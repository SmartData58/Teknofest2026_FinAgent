import os
import json
import hashlib
import asyncio
import httpx
import re
import traceback
from typing import List, Optional
from loguru import logger
from fastapi.responses import StreamingResponse

from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from pymongo import MongoClient

from chatbot.intent import niyet_bul, Mesaj, Niyet, RAG_CEVAP_PROMPTU, gecmis_metni_olustur, banka_bul
from chatbot.agents import (
    suggestion_chain,
    derin_dusunme_gerekli_mi,
    hyde_belgesi_uret,
    step_back_sorgu_uret,
    coklu_sorgu_uret,
    yapisal_analiz_parametreleri_uret,
    TIMEOUT_ONERI,
)
from chatbot.redis_cache import get_cached_full_response, set_cached_full_response
from chatbot.tools import gercek_finansman_hesapla
from embedding_client import embed_batch

TEMP_DIR = "./temp"
os.makedirs(TEMP_DIR, exist_ok=True)

QDRANT_URL = os.getenv("QDRANT_HOST", "http://qdrant:6333")
EMBEDDING_API_URL = os.getenv("EMBEDDING_URL", "http://embedding:8001/api/embed")
RERANKER_API_URL = os.getenv("RERANKER_URL", "http://reranker:8002/api/rerank")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434/api/chat")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@mongodb:27017/?authSource=admin")

# Derin RAG akışında (HyDE + Step-Back + Multi-Query) üretilecek toplam
# alternatif sorgu sayısını ve arama başına getirilecek belge sayısını sınırlar.
MAKS_ALT_SORGU = 5
SORGU_BASINA_K = 4
NIHAI_BAGLAM_BELGE_SAYISI = 4

# Redis tam-yanıt önbelleğinin geçerlilik süresi. Kampanya verisi (Mongo/Qdrant
# yeniden kurulumu) sık değişebildiği için 24 saat yerine daha temkinli 6 saat.
CACHE_TTL_SANIYE = 6 * 60 * 60


class OzelQwenEmbedder(Embeddings):
    """LangChain Embeddings arayüzü — gerçek HTTP çağrısı artık chatbot/ ve rag/
    paketleri arasında PAYLAŞILAN embedding_client.embed_batch() üzerinden yapılıyor
    (tek gerçek kaynak; bkz. embedding_client.py). Bu sayede önceden burada hiç
    olmayan otomatik yeniden deneme (transient hatalarda 1 kez, 5sn sonra tekrar)
    de bedavaya geldi. `api_url` parametresi yalnızca geriye dönük uyumluluk için
    tutuluyor; gerçek istek embedding_client'ın kendi EMBEDDING_URL çözümlemesini
    kullanır (aynı ortam değişkeni: EMBEDDING_URL)."""

    def __init__(self, api_url: str = None):
        self.api_url = api_url

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        try:
            # normalize=False: bu adaptörün önceki davranışını (ham/normalize
            # edilmemiş vektörler) korur. Qdrant'ın COSINE mesafesi normalize
            # farkını zaten otomatik ele aldığı için sonuç değişmez.
            matris = embed_batch(texts, normalize=False, url=self.api_url)
            return matris.tolist()
        except Exception as e:
            logger.error(f"Embedding servisi (embed_documents) hatası: {e}")
            return []

    def embed_query(self, text: str) -> List[float]:
        r = self.embed_documents([text])
        return r[0] if r else []


embeddings = OzelQwenEmbedder(api_url=EMBEDDING_API_URL)
_vector_store = None


def get_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = QdrantVectorStore(
            client=QdrantClient(url=QDRANT_URL),
            collection_name="banka_kampanyalari",
            embedding=embeddings,
            content_payload_key="belge",
        )
    return _vector_store


async def rerank_documents(query: str, docs: List, top_n: int = NIHAI_BAGLAM_BELGE_SAYISI) -> List:
    if not docs:
        return []
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                RERANKER_API_URL,
                json={"query": query, "texts": [d.page_content for d in docs]},
                timeout=15.0,
            )
            res.raise_for_status()
            data = res.json()
            idx = [i["index"] for i in data] if isinstance(data, list) else data.get("indices", list(range(len(docs))))
            return [docs[i] for i in idx if i < len(docs)][:top_n]
    except Exception as e:
        logger.warning(f"Reranker servisi başarısız, sırasız ilk {top_n} belge kullanılıyor: {e}")
        return docs[:top_n]


def parse_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val)
    s = re.sub(r'[^\d,\.]', '', s)
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s) if s else 0.0
    except Exception:
        return 0.0


def extract_campaign_data(doc):
    genel = doc.get("genel_bilgi") or {}
    fin = doc.get("finansman_detay") or {}
    pro = doc.get("promosyon_detay") or {}
    mgm = doc.get("mgm_detay") or {}

    banka = genel.get("banka_id") or doc.get("banka_adi") or doc.get("banka") or "Bilinmiyor"
    kampanya_adi = genel.get("kampanya_adi") or doc.get("kampanya_adi") or doc.get("baslik") or "Kampanya"
    kat = genel.get("kampanya_turu") or doc.get("kategori") or doc.get("kampanya_kategorisi") or genel.get("alt_kategori") or "Genel"
    url = genel.get("kaynak_url") or doc.get("url") or doc.get("kampanya_url") or "-"

    kitle_raw = genel.get("hedef_kitle") or doc.get("hedef_kitle") or "-"
    kitle = ", ".join(kitle_raw) if isinstance(kitle_raw, list) else str(kitle_raw)

    bitis = genel.get("bitis_tarihi") or genel.get("cekilis_tarihi") or doc.get("bitis_tarihi") or "-"
    if not bitis:
        bitis = "-"

    metin = genel.get("metin") or doc.get("ham_metin") or doc.get("kosullar") or ""
    if not metin or len(str(metin)) < 5:
        clean_doc = {k: v for k, v in doc.items() if k not in ["_id", "embedding", "vektorler"]}
        metin = json.dumps(clean_doc, indent=2, ensure_ascii=False)

    kar_payi = parse_float(fin.get("kar_paylasim_orani") or doc.get("kar_payi_orani") or doc.get("kar_payi") or 0.0)
    vade = parse_float(fin.get("vade_ay") or fin.get("taksit") or fin.get("sure_gun") or doc.get("vade_ay") or doc.get("vade") or 0.0)

    odul = parse_float(pro.get("odul_tutari_tl") or pro.get("odul_miktari") or pro.get("puan_kazanc") or doc.get("odul_miktari") or doc.get("odul_tl") or 0.0)
    if odul == 0:
        odul = parse_float(mgm.get("kisi_basi_kazanc") or mgm.get("mgm_limit_tl") or 0.0)

    return {
        "banka": str(banka).replace("_", " ").title(),
        "kampanya_adi": str(kampanya_adi),
        "kat": str(kat).replace("_", " ").title(),
        "url": str(url),
        "kitle": str(kitle).replace("_", " ").title(),
        "bitis": str(bitis),
        "metin": str(metin),
        "kar_payi": kar_payi,
        "vade": vade,
        "odul": odul,
    }


def _kampanya_kayitlarini_getir() -> list:
    """MongoDB'den ham kampanya kayıtlarını okur.

    🛠️ HATA DÜZELTMESİ: Bu fonksiyon önceden SADECE `smartdata.*` koleksiyonlarına
    bakıyordu. Ama chatbot.py'deki Qdrant indexleyici (auto_init_qdrant), smartdata
    boşsa `finagent.kampanyalar`'a DÜŞEREK devam ediyordu. Sonuç: gerçek veri
    finagent'ta tutulduğunda Qdrant/vektör arama sorunsuz çalışıyor (LLM oradan
    metin buluyor) ama Mongo tabanlı grafik/karşılaştırma sorgusu HİÇBİR ZAMAN veri
    bulamıyor, dolayısıyla grafik/tablo hiç render edilmiyor ve "en düşük kâr payı
    hangi banka" gibi kesin sıralama gerektiren sorular LLM'in Qdrant'tan gelen
    birkaç alakalı-ama-sıralanmamış belgeyi yorumlamaya çalışmasıyla (net bir cevap
    veremeden) sonuçlanıyordu. Artık iki kod yolu da AYNI iki-aşamalı fallback'i
    kullanıyor: önce smartdata.*, boşsa finagent.kampanyalar."""
    client = MongoClient(MONGO_URI)
    try:
        db = client["smartdata"]
        koleksiyonlar = ["extracted_fields", "structured_campaigns", "processed_campaigns", "kampanyalar"]
        for kol in koleksiyonlar:
            try:
                veri = list(db[kol].find({}).limit(500))
                if veri:
                    return veri
            except Exception as e:
                logger.warning(f"MongoDB 'smartdata.{kol}' okunamadı: {e}")

        try:
            veri = list(client["finagent"]["kampanyalar"].find({}).limit(500))
            if veri:
                return veri
        except Exception as e:
            logger.warning(f"MongoDB 'finagent.kampanyalar' okunamadı: {e}")

        return []
    finally:
        client.close()


# Karşılaştırma niyetindeki "alan" (intent.py) ile Mongo sütun adları arasındaki eşleme.
# Bu sayede intent routing sonucu, regex ile yeniden tahmin etmeden doğrudan kullanılır.
_ALAN_TO_HEDEF = {
    "kar_payi_orani": "kar_payi",
    "tahsis_ucreti": "kar_payi",
    "odul_miktari": "odul",
    "vade_ay": "vade",
    "taksit_sayisi": "vade",
}


def grafigi_hazirla_mongo_dinamik(
    user_query: str,
    view_mode: str,
    zorla_hedef: Optional[str] = None,
    zorla_baslik: Optional[str] = None,
    banka_kodu: Optional[str] = None,
):
    query_lower = user_query.lower()

    chart_type = "table" if re.search(r'\b(tablo|liste|sırala|ver|detaylandır)\b', query_lower) else "doughnut"
    if view_mode == "musteri" and not re.search(r'\b(grafik|pasta|şekil|çiz)\b', query_lower):
        chart_type = "table"

    is_specific = True
    if zorla_hedef == "kar_payi":
        hedef, prefix, suffix = "kar_payi", "%", ""
    elif zorla_hedef == "odul":
        hedef, prefix, suffix = "odul", "", " TL"
    elif zorla_hedef == "vade":
        hedef, prefix, suffix = "vade", "", " Ay"
    elif re.search(r'\b(kar|kâr|faiz|oran|payı)\b', query_lower):
        hedef, prefix, suffix = "kar_payi", "%", ""
    elif re.search(r'\b(ödül|para|tl|hediye|bonus|nakit|iade)\b', query_lower):
        hedef, prefix, suffix = "odul", "", " TL"
    elif re.search(r'\b(vade|ay|taksit|süre)\b', query_lower):
        hedef, prefix, suffix = "vade", "", " Ay"
    else:
        is_specific = False
        hedef, prefix, suffix = "odul", "", ""

    tum_sonuclar = _kampanya_kayitlarini_getir()
    islenmis = [extract_campaign_data(d) for d in tum_sonuclar]

    # 🛠️ HATA DÜZELTMESİ: Banka filtresi önceden SADECE is_specific=False dalında
    # (yani "kâr/oran/ödül/vade" gibi belirli bir metrik istenmediğinde) ve yalnızca
    # 4 bankaya özel sabit kodlanmış substring kontrolleriyle uygulanıyordu. Bu yüzden
    # "Tom Katılım kampanyalarını detaylandır" gibi bir soru intent routing'den
    # (niyet.banka_kodu) veya text-to-mongo ajanından bir zorla_hedef ürettiğinde
    # (is_specific=True olduğunda) banka filtresi TAMAMEN atlanıyor, sonuç olarak
    # istenen bankanın kampanyaları yerine TÜM bankalardan en yüksek/düşük değerli
    # kampanyalar dönüyordu (ör. Tom Katılım yerine Ziraat/Vakıf Katılım listeleniyordu).
    # Artık banka filtresi is_specific'ten TAMAMEN BAĞIMSIZ ve intent.py'nin zaten
    # tespit ettiği banka_kodu üzerinden (tüm bankaları kapsayan banka_bul ile)
    # uygulanıyor; eski 4 bankalık sabit substring listesi kaldırıldı.
    temel_havuz = islenmis
    if banka_kodu:
        bankaya_ozel = [d for d in islenmis if banka_bul(d["banka"]) == banka_kodu]
        if bankaya_ozel:
            temel_havuz = bankaya_ozel
        else:
            logger.warning(f"Banka filtresi ('{banka_kodu}') hiçbir kayıtla eşleşmedi, filtresiz devam ediliyor.")

    if is_specific:
        gecerli = [d for d in temel_havuz if d[hedef] > 0]
    else:
        gecerli = temel_havuz

    is_lowest = re.search(r'\b(düşük|az|minimum|küçük)\b', query_lower)

    if is_specific:
        if hedef == "kar_payi":
            reverse_sort = False if is_lowest else (False if not re.search(r'\b(yüksek|çok|büyük|maksimum)\b', query_lower) else True)
        else:
            reverse_sort = False if is_lowest else True
        gecerli.sort(key=lambda x: x[hedef], reverse=reverse_sort)

    limit = 10
    sayi_match = re.search(r'\b(\d+)\b', query_lower)
    if sayi_match:
        limit = min(int(sayi_match.group(1)), 50)
    elif re.search(r'\b(en|hangisi|kimde|nedir)\b', query_lower):
        limit = 3
    elif re.search(r'\b(bütün|tüm|hepsini|detaylandır)\b', query_lower):
        limit = 50

    gecerli = gecerli[:limit]

    labels, sub_labels, values, source_indices, full_texts, categories = [], [], [], [], [], []
    db_context = ""

    for idx, c in enumerate(gecerli):
        labels.append(c["banka"])
        sub_labels.append(c["kampanya_adi"])
        gosterilen_deger = c[hedef] if is_specific else (c["odul"] if c["odul"] > 0 else (c["kar_payi"] if c["kar_payi"] > 0 else 0))
        g_prefix = prefix if is_specific else ("" if c["odul"] > 0 else "%")
        g_suffix = suffix if is_specific else (" TL" if c["odul"] > 0 else "")

        values.append(gosterilen_deger)
        source_indices.append(idx + 1)
        categories.append(c["kat"])

        tam_metin = f"📌 KAMPANYA VERİTABANI KAYDI\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🏦 Banka/Kurum: {c['banka']}\n🏷️ Kampanya Adı: {c['kampanya_adi']}\n📦 Kategori: {c['kat']}\n⚖️ Değer: {g_prefix}{gosterilen_deger}{g_suffix}\n🎯 Hedef Kitle: {c['kitle']}\n⏳ Bitiş Tarihi: {c['bitis']}\n🔗 URL: {c['url']}\n\n📝 KAMPANYA DETAYLARI / KOŞULLAR:\n{c['metin']}\n"
        full_texts.append(tam_metin)

        db_context += f"- Banka: {c['banka']} | Kampanya: {c['kampanya_adi']} | Değer: {g_prefix}{gosterilen_deger}{g_suffix} | Kategori: {c['kat']}\n"

    chart_str = ""
    if labels:
        tablo_baslik = zorla_baslik or (f"En İyi {len(labels)} Sonuç" if "en" in query_lower else "Kampanya Verileri")
        chart_data = {
            "type": chart_type, "title": tablo_baslik, "subtitle": f"Sistemdeki kriterlere uyan {len(labels)} sonuç listelendi.",
            "prefix": prefix if is_specific else "", "suffix": suffix if is_specific else "",
            "labels": labels, "sub_labels": sub_labels, "values": values,
            "source_indices": source_indices, "full_texts": full_texts, "categories": categories,
            "stats": {"avg": round(sum(values) / len(values), 2), "min": min(values), "max": max(values)},
        }
        chart_str = f'\n\n[CHART]{json.dumps(chart_data)}[/CHART]\n\n'

    return chart_str, db_context, labels


def _oneriyi_temizle(ham: str) -> str:
    """Tek bir öneri metnindeki etiket/işaret artıklarını temizler."""
    s = (ham or "").strip()
    # Metne yapışmış tam veya YARIM etiketler ([SUGGESTION], [/SUGGESTION,
    # SUGGESTION] gibi) — LLM etiketi bozuk ürettiğinde bunlar sızıyor.
    s = re.sub(r"\[?/?\s*SUGGESTIONS?\s*\]?", "", s, flags=re.IGNORECASE)
    # Baştaki numaralandırma / madde işareti ("1. ", "2) ", "- ", "• ")
    s = re.sub(r"^\s*(?:\d+\s*[\.\)\-]|[\-\*•])\s*", "", s)
    # Markdown kalın/italik ve tırnak sarmalayıcıları
    s = s.strip().strip("*_").strip()
    if len(s) > 1 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    # 🛠️ ASIL HATA: Uçlarda kalan başıboş köşeli parantezler.
    # Ekran görüntüsündeki "Bu teklif kaç gün boyunca geçerli oluyor?[" tam
    # olarak buydu: LLM kapanış etiketinden önce fazladan bir "[" üretmiş,
    # non-greedy regex de onu sadakatle yakalamıştı.
    s = s.strip("[]/ \t")
    return s.strip()


def _onerileri_ayikla(sug_raw: str, adet: int = 3) -> list:
    """LLM'in öneri çıktısını dayanıklı biçimde ayrıştırır.

    🛠️ Eski kod iki dalda da hatalıydı:
      • Regex dalı ham eşleşmeyi olduğu gibi alıyordu -> fazladan "[" gibi
        artıklar öneri metnine sızıyordu (ekran görüntüsündeki hata).
      • Yedek (fallback) dalı satırları bölüyordu ama numaralandırmayı
        TEMİZLEMİYORDU -> öneriler "1. Faiz oranları ne kadar?" diye çıkıyordu.
        Ayrıca "[SUGGESTION]..." ve "/SUGGESTION]" gibi çöp satırlar geçiyordu.
    Ayrıca kapanış etiketi eksik olduğunda eski regex o öneriyi tamamen
    kaybediyordu; artık kapanış etiketi opsiyonel.
    """
    if not sug_raw:
        return []

    # Kapanış etiketi opsiyonel: eksikse satır sonuna kadar al.
    bulunan = re.findall(
        r"\[\s*SUGGESTION\s*\]\s*(.*?)\s*(?:\[\s*/\s*SUGGESTION\s*\]?|$)",
        sug_raw,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not bulunan:
        bulunan = sug_raw.split("\n")

    sonuc, gorulen = [], set()
    for parca in bulunan:
        temiz = _oneriyi_temizle(parca)
        # Çok kısa (çöp) veya aşırı uzun (cevabın kendisi kaçmış) olanları ele.
        if not (6 <= len(temiz) <= 160):
            continue
        anahtar = temiz.lower()
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        sonuc.append(temiz)
        if len(sonuc) >= adet:
            break
    return sonuc


def _temsili_oran_bul(banka_kodu: Optional[str]) -> Optional[float]:
    """Taksit hesaplama isteyen kullanıcı bir kâr payı oranı BELİRTMEDİYSE,
    MongoDB'deki güncel kampanyalardan (varsa ilgili bankaya özel, yoksa genel
    ortalama) temsili bir oran türetir. Senkron pymongo çağrısıdır; çağıran
    taraf asyncio.to_thread ile sarmalamalı."""
    try:
        tum_sonuclar = _kampanya_kayitlarini_getir()
        islenmis = [extract_campaign_data(d) for d in tum_sonuclar]
        adaylar = [d["kar_payi"] for d in islenmis if d["kar_payi"] > 0]

        if banka_kodu:
            bankaya_ozel = [d["kar_payi"] for d in islenmis if d["kar_payi"] > 0 and banka_bul(d["banka"]) == banka_kodu]
            if bankaya_ozel:
                adaylar = bankaya_ozel

        if not adaylar:
            return None
        return round(sum(adaylar) / len(adaylar), 2)
    except Exception as e:
        logger.warning(f"Temsili oran bulma hatası: {e}")
        return None


def _banka_filtresi(banka_kodu: Optional[str]) -> Optional[Filter]:
    if not banka_kodu:
        return None
    return Filter(must=[FieldCondition(key="banka_kodu", match=MatchValue(value=banka_kodu))])


async def _tek_vektor_arama(vs, sorgu: str, banka_filtre: Optional[Filter], k: int = SORGU_BASINA_K):
    try:
        if banka_filtre is not None:
            return await asyncio.wait_for(
                asyncio.to_thread(vs.similarity_search, sorgu, k=k, filter=banka_filtre), timeout=10.0
            )
        return await asyncio.wait_for(asyncio.to_thread(vs.similarity_search, sorgu, k=k), timeout=10.0)
    except Exception as e:
        logger.warning(f"Vektör arama başarısız ('{sorgu[:50]}...'): {e}")
        return []


async def gelismis_belge_getir(
    soru: str,
    niyet: Niyet,
    derin_arama: bool,
    status_callback=None,
) -> List:
    """RAG retrieval çekirdeği. `derin_arama` True ise HyDE + Step-Back + Multi-Query
    ile birden fazla alternatif sorgu üretip sonuçları birleştirir; False ise
    yalnızca doğrudan (ve varsa bağlamsal) sorguyla hızlı bir arama yapar."""

    async def durum(msg: str):
        if status_callback:
            await status_callback(msg)

    aday_sorgular = [soru]
    if niyet.baglam_soru:
        aday_sorgular.append(f"{niyet.baglam_soru} {soru}".strip())

    if derin_arama:
        await durum("HyDE: varsayımsal belge üretiliyor...")
        await durum("Step-Back: genel/kapsayıcı soru çıkarılıyor...")
        await durum("Multi-Query: alternatif sorgular üretiliyor...")
        hyde_metni, step_back_sorusu, coklu_sorgular = await asyncio.gather(
            hyde_belgesi_uret(soru),
            step_back_sorgu_uret(soru),
            coklu_sorgu_uret(soru),
        )
        if hyde_metni:
            aday_sorgular.append(hyde_metni)
        if step_back_sorusu:
            aday_sorgular.append(step_back_sorusu)
        aday_sorgular.extend(coklu_sorgular)

    # Tekilleştir, boşları at, maliyeti sınırla.
    gorulmus, temiz_sorgular = set(), []
    for s in aday_sorgular:
        s_norm = (s or "").strip()
        anahtar = s_norm.lower()
        if s_norm and anahtar not in gorulmus:
            gorulmus.add(anahtar)
            temiz_sorgular.append(s_norm)
    temiz_sorgular = temiz_sorgular[:MAKS_ALT_SORGU]

    vs = get_vector_store()
    banka_filtre = _banka_filtresi(niyet.banka_kodu)

    await durum("Vektör DB taranıyor...")
    sonuc_listeleri = await asyncio.gather(*(_tek_vektor_arama(vs, s, banka_filtre) for s in temiz_sorgular))

    gorulen_icerik, birlesik = set(), []
    for liste in sonuc_listeleri:
        for d in liste:
            anahtar = d.page_content[:150]
            if anahtar not in gorulen_icerik:
                gorulen_icerik.add(anahtar)
                birlesik.append(d)

    # Banka filtresi sonuç bulamadıysa (isim uyuşmazlığı, eksik metadata vb.)
    # filtresiz bir son çare araması yap — kullanıcıyı boş bağlamda bırakma.
    if not birlesik and banka_filtre is not None:
        yedek = await _tek_vektor_arama(vs, soru, None)
        birlesik.extend(yedek)

    return birlesik


async def get_chatbot_response(
    user_message: str,
    model: str = "qwen3.5:4b",
    thinking: str = "auto",
    history: list = None,
    file_context: str = "",
    files: List = None,
    view_mode: str = "musteri",
    language: str = "tr",
):
    history = history or []
    gecmis_mesajlari = [Mesaj(rol=m.get("role", "user"), icerik=m.get("content", "")) for m in history]
    niyet = niyet_bul(user_message, gecmis_mesajlari)

    # 🛠️ HATA DÜZELTMESİ — cevaplara İngilizce ve DOLAR sızması:
    # Model "%2.99'dur; yani iki dolar yedi de altı (two dollars and seventy-nine
    # cents)" gibi cümleler kuruyordu. İki sebebi vardı: (1) prompt'taki
    # "rakamları telaffuz ederek" talimatı (aşağıda kaldırıldı), (2) dil kuralının
    # sadece "Türkçe ver" demesi — İngilizce parantez/çeviri eklemeyi yasaklamaması.
    # Küçük bir 4B model, sayıyı heceleyince eğitim verisindeki en yaygın kalıba
    # ("$2.99") kayıp para birimini dolara çeviriyordu.
    if language == "tr":
        dil = (
            "Yanıtlarını KESİNLİKLE ve YALNIZCA Türkçe yaz. Tek bir İngilizce kelime, "
            "parantez içinde İngilizce çeviri veya başka dilde açıklama EKLEME."
        )
    else:
        dil = "Write your answer ONLY in English."
    mod = "Karşında MÜŞTERİ var. Gizli terim KULLANMA, nazik ol." if view_mode == "musteri" else "Karşında ANALİST var. Teknik ve detaylı ol."

    if niyet.tur in ("statik", "tavsiye") and niyet.statik_cevap:
        async def static_stream():
            yield f"[STATUS]Yanıt iletiliyor...[/STATUS]\n\n"
            yield niyet.statik_cevap
        return StreamingResponse(static_stream(), media_type="text/plain")

    # 🧮 Taksit hesaplama: tools.py'deki gercek_finansman_hesapla artık gerçekten
    # tetikleniyor. LLM'e sayısal hesap yaptırmak yerine (uydurma riski) deterministik
    # bir hesap yapılır; LLM turuna hiç girilmediği için de çok hızlıdır.
    if niyet.tur == "hesaplama":
        async def hesaplama_stream():
            yield "[STATUS]Taksit hesaplanıyor...[/STATUS]\n\n"
            oran = niyet.oran
            oran_kaynagi = "belirttiğiniz"
            if not oran:
                oran = await asyncio.to_thread(_temsili_oran_bul, niyet.banka_kodu)
                oran_kaynagi = "sistemdeki güncel ortalama"
            if not oran:
                yield (
                    "Hesaplama yapabilmem için kâr payı/faiz oranını da belirtmeniz gerekiyor "
                    "(örn: \"100.000 TL, 12 ay, %2.99 oranla taksit hesabı\"). "
                    "Şu an bu işlem için elimde referans alınabilecek bir oran bulamadım."
                )
                return
            tablo = gercek_finansman_hesapla(niyet.tutar, niyet.vade, oran)
            if not tablo:
                yield (
                    f"%0 kâr payı oranıyla ek bir maliyet oluşmaz; "
                    f"{niyet.tutar:,.2f} TL / {niyet.vade} ay için taksit tutarı doğrudan "
                    f"{(niyet.tutar / niyet.vade):,.2f} TL/ay olur."
                )
                return
            banka_notu = f" ({niyet.banka_kodu})" if niyet.banka_kodu else ""
            yield (
                f"Belirttiğiniz {niyet.tutar:,.2f} TL / {niyet.vade} ay için{banka_notu} hesaplama:\n\n"
                f"{tablo}\n\n"
                f"*Not: Bu hesaplama {oran_kaynagi} %{oran} oranı üzerinden yapılmıştır; "
                f"kesin koşullar banka onayına tabidir ve bu bir yatırım/finansal tavsiye değildir.*"
            )
        return StreamingResponse(hesaplama_stream(), media_type="text/plain")

    async def stream_generator():
        q = asyncio.Queue()

        async def background_process():
            try:
                final_res = ""
                await q.put({"type": "status", "content": "Sorgu analiz ediliyor..."})

                # 🛠️ DÜRÜST STATUS: Frontend eskiden "Sohbet geçmişi taranıyor"
                # etiketini istek GÖNDERİLMEDEN ÖNCE, sadece "geçmiş boş mu değil mi"
                # diye bakıp basıyordu — hiçbir iş yapılmadığı için hep 0.0s
                # görünüyordu. O etiket kaldırıldı; artık geçmiş GERÇEKTEN
                # kullanıldığında burada, backend'den bildiriliyor.
                if gecmis_mesajlari:
                    if niyet.baglam_soru:
                        # Takip sorusu: geçmişten bağlam (ve varsa banka) çözüldü.
                        detay = f"takip sorusu, bağlam çözüldü"
                        if niyet.banka_kodu:
                            detay += f" → {niyet.banka_kodu}"
                        await q.put({
                            "type": "status",
                            "content": f"Sohbet geçmişi kullanıldı ({len(gecmis_mesajlari)} mesaj, {detay})",
                        })
                    else:
                        await q.put({
                            "type": "status",
                            "content": f"Sohbet geçmişi bağlama eklendi ({len(gecmis_mesajlari)} mesaj)",
                        })

                # ⚡ Redis tam-yanıt önbelleği: yalnızca bağlama bağlı olmayan (takip
                # sorusu olmayan) kampanya/karşılaştırma/liste sorularında kullanılır —
                # "peki en düşüğü hangisi" gibi bağlamsal sorularda yanlış/eski bir
                # cevabı olduğu gibi geri vermemek için devre dışı bırakılır.
                # 🛠️ file_context varsa önbellek DEVRE DIŞI: önbellek anahtarı yalnızca
                # (dil, mod, banka, soru metni) üzerinden üretiliyor, yüklenen dosyayı
                # içermiyor. Aksi halde farklı PDF'ler yükleyip aynı soruyu ("özetler
                # misin") soran iki kullanıcı aynı anahtara düşer ve ikincisi
                # BİRİNCİNİN DOSYASINA ait cevabı görürdü.
                cache_uygun = (
                    (not niyet.baglam_soru)
                    and not file_context
                    and niyet.tur in ("kampanya_soru", "karsilastirma", "banka_listesi")
                )
                # 🛠️ HATA DÜZELTMESİ — "sohbet geçmişini gerçekten taramıyor":
                # Önbellek anahtarı SOHBET GEÇMİŞİNİ HİÇ İÇERMİYORDU. `cache_uygun`
                # yalnızca niyet.baglam_soru'ya bakıyor, o da sadece _DEVAM regex'i
                # ("peki", "onun", "bir de"...) eşleşirse dolduruluyor. Dolayısıyla
                # "grafik olarak verir misin" gibi bağlama BAĞIMLI ama regex'e
                # UYMAYAN bir takip sorusu önbelleğe uygun sayılıyor ve geçmişten
                # bağımsız olarak anahtarlanıyordu. Sonuç: aynı soru ikinci kez
                # sorulduğunda BAŞKA bir sohbetin cevabı aynen geri veriliyor,
                # geçmiş hiç okunmuyordu. Anahtar artık geçmişin parmak izini
                # (son mesajların hash'i) içeriyor: aynı soru + aynı geçmiş = isabet,
                # farklı geçmiş = yeni cevap.
                gecmis_parmak_izi = hashlib.md5(
                    "|".join(f"{m.rol}:{m.icerik}" for m in gecmis_mesajlari[-6:]).encode("utf-8")
                ).hexdigest()[:12] if gecmis_mesajlari else "yok"

                cache_anahtari = (
                    f"{language}|{view_mode}|{niyet.banka_kodu or '-'}|"
                    f"{gecmis_parmak_izi}|{user_message.strip().lower()}"
                )

                if cache_uygun:
                    await q.put({"type": "status", "content": "Önbellek kontrol ediliyor..."})
                    try:
                        onbellek = await get_cached_full_response(cache_anahtari)
                    except Exception as e:
                        logger.warning(f"Redis önbellek okuma hatası: {e}")
                        onbellek = None
                    if onbellek:
                        await q.put({"type": "status", "content": "⚡ Anında yanıt (önbellek)"})
                        await q.put({"type": "token", "content": onbellek})
                        return

                # 🧭 Intent routing: niyet.tur zaten karsilastirma/banka_listesi/kampanya_soru
                # arasında ayrım yapıyor. Bunu regex ile yeniden tahmin etmek yerine
                # doğrudan kullanıyoruz; ek anahtar kelime taraması sadece geniş
                # "kampanya_soru" durumunda analiz gerekip gerekmediğini belirlemek için.
                is_analyst = niyet.tur in ("karsilastirma", "banka_listesi") or re.search(
                    r'\b(grafik|tablo|oran|ödül|tl|faiz|kampanya|liste|vade|kar|kâr|detaylandır)\b',
                    user_message.lower(),
                )
                zorla_hedef = _ALAN_TO_HEDEF.get(niyet.alan) if niyet.alan else None
                zorla_baslik = None

                db_context = ""
                labels_found = []

                if is_analyst:
                    # 🤖 Text-to-Mongo ajanı (agents.sql_agent_chain): intent regex'i hedef
                    # sütunu zaten belirlediyse (zorla_hedef) LLM'e gerek yok — hızlı yol.
                    # "banka_listesi" niyetinde (ör. "X Bankası kampanyalarını detaylandır")
                    # ajana HİÇ danışılmıyor: ajanın şeması banka farkında değil, tek bir
                    # metriğe (kar_payi/vade/odul_tl) zorlayınca kullanıcının istediği
                    # "bu bankanın TÜM kampanyaları" listesi yerine tüm bankalardan
                    # sıralanmış tek metrikli bir sonuç dönüyordu — banka filtresi bu
                    # durumda anlamsızlaşıyordu.
                    if not zorla_hedef and niyet.tur != "banka_listesi":
                        await q.put({"type": "status", "content": "Text-to-Mongo ajanı sorgu parametrelerini çıkarıyor..."})
                        db_params = await yapisal_analiz_parametreleri_uret(user_message)
                        if db_params:
                            eslenen = {"kar_payi": "kar_payi", "vade": "vade", "odul_tl": "odul"}.get(db_params.get("hedef_sutun"))
                            if eslenen:
                                zorla_hedef = eslenen
                            if db_params.get("title"):
                                zorla_baslik = str(db_params["title"])[:120]

                    await q.put({"type": "status", "content": "MongoDB Ajanı Sorgulanıyor..."})
                    grafik_kodu, db_context, labels_found = grafigi_hazirla_mongo_dinamik(
                        user_message, view_mode, zorla_hedef=zorla_hedef, zorla_baslik=zorla_baslik,
                        banka_kodu=niyet.banka_kodu,
                    )
                    if grafik_kodu:
                        final_res += grafik_kodu
                        await q.put({"type": "token", "content": grafik_kodu})

                # 🧠 Thinking-decider: kullanıcı zorunlu tutmadıysa (thinking="true"/"false"),
                # sorunun derin RAG (HyDE + Step-Back + Multi-Query) gerektirip
                # gerektirmediğine karar verilir. karsilastirma/banka_listesi niyetleri
                # zaten intent routing ile net olduğundan LLM'e sorulmadan doğrudan derin
                # moda alınır (daha hızlı + daha güvenilir); yalnızca belirsiz
                # "kampanya_soru" durumunda thinking-decider ajanına danışılır.
                if thinking == "true":
                    derin_arama = True
                elif thinking == "false":
                    derin_arama = False
                elif niyet.tur in ("karsilastirma", "banka_listesi"):
                    derin_arama = True
                else:
                    await q.put({"type": "status", "content": "Sorgu karmaşıklığı değerlendiriliyor..."})
                    derin_arama = await derin_dusunme_gerekli_mi(user_message)

                context_text = ""
                kaynaklar_listesi = []
                try:
                    async def durum_bildir(msg: str):
                        await q.put({"type": "status", "content": msg})

                    docs = await gelismis_belge_getir(user_message, niyet, derin_arama, status_callback=durum_bildir)
                    if docs:
                        await q.put({"type": "status", "content": "Belgeler yeniden sıralanıyor (rerank)..."})
                        docs = await rerank_documents(user_message, docs)
                        for i, doc in enumerate(docs):
                            context_text += f"[{i + 1}] {doc.page_content}\n"
                            kaynaklar_listesi.append({
                                "index": i + 1,
                                "kampanya_id": doc.metadata.get("kampanya_id", "Qdrant"),
                                "icerik": doc.page_content,
                            })
                except Exception as e:
                    logger.error(f"Belge getirme (retrieval) hatası: {e}\n{traceback.format_exc()}")

                await q.put({"type": "status", "content": "Yapay zeka yanıtı hazırlıyor..."})

                tam_baglam = ""
                # 🛠️ HATA DÜZELTMESİ: file_context bu fonksiyonun parametresiydi ama
                # gövdede HİÇ KULLANILMIYORDU. main.py kullanıcının yüklediği dosyaları
                # diske yazıp parse_document() ile (pahalı bir işlem) metnini çıkarıyor,
                # buraya gönderiyor ve metin sessizce çöpe gidiyordu — yani kullanıcı bir
                # PDF yükleyip "bu dosyada ne yazıyor?" dediğinde model dosyayı hiç
                # görmüyordu. Dosya içeriği artık bağlamın EN BAŞINA konuyor (kullanıcının
                # az önce yüklediği belge, veritabanı kayıtlarından daha önceliklidir).
                if file_context:
                    tam_baglam += f"📎 KULLANICININ YÜKLEDİĞİ DOSYALAR:\n{file_context}\n"
                if db_context:
                    tam_baglam += f"📌 MONGODB KESİN VERİLERİ (BUNLARI ANALİZ ET VE YORUMLA):\n{db_context}\n"
                if context_text:
                    tam_baglam += f"\n📌 İNTERNET/METİN VERİLERİ:\n{context_text}"

                safe_baglam = tam_baglam.replace("{", "{{").replace("}", "}}")

                # 🛠️ HATA DÜZELTMESİ: Kullanıcı "grafik olarak verir misin" dediğinde
                # arayüz grafiği ZATEN çiziyor (doughnut + bar + tablo), ama prompt
                # modele yalnızca "tablo çizildi" diyordu. Model de grafik isteğini
                # karşılayamadığını sanıp "size grafik oluşturamıyorum, teknik
                # yeteneklerim yok" diye özür diliyordu — kullanıcı ekranda grafiği
                # görürken. Prompt artık grafiğin de çizildiğini açıkça söylüyor ve
                # modelden özür dilememesini istiyor.
                kural_ext = (
                    "\nÖNEMLİ KURAL — GÖRSELLEŞTİRME: Kullanıcının istediği TABLO VE GRAFİK "
                    "(pasta/çubuk grafik dahil) ARAYÜZ TARAFINDAN ZATEN ÇİZİLDİ ve bu mesajın "
                    "hemen üstünde kullanıcıya gösteriliyor. Bu yüzden:\n"
                    "- Markdown tablosu veya ASCII grafik ÇİZME, buna gerek yok.\n"
                    "- 'Grafik oluşturamam', 'görselleştirme yapamam', 'teknik yeteneklerim yok' "
                    "GİBİ ŞEYLER ASLA SÖYLEME ve ÖZÜR DİLEME. Grafik zaten hazır ve ekranda.\n"
                    "- Bunun yerine ekrandaki grafiği/tabloyu SÖZLÜ OLARAK YORUMLA: neyi "
                    "gösterdiğini, öne çıkan kampanyaları ve dikkat çeken farkları anlat.\n"
                    "Sen uzman bir Finansal Analistsin! Yukarıdaki 'MONGODB KESİN VERİLERİ' "
                    "kısmını detaylıca incele, en iyi kampanyaları kıyasla, uzun ve "
                    "profesyonel bir analiz metni yaz."
                )

                # 🛠️ HATA DÜZELTMESİ — sayı/para birimi kayması:
                # Eski prompt'ta "rakamları TELAFFUZ EDEREK ... yaz" talimatı vardı
                # (yukarıdan kaldırıldı). Model sayıları heceleyince şunlar oluyordu:
                #   "%2.99'dur; yani iki dolar yedi de altı (two dollars and
                #    seventy-nine cents) yüzdesidir"   <- para birimi DOLAR'a kaydı
                #   "1000,00 Türk Lirası ... bir bin TL (one thousand Turkish Lira)"
                #   "yüzbin (1000)"                    <- 1000'i "yüzbin" diye okudu
                # Yani talimat hem yanlış para birimi hem de yanlış sayı okumaları
                # üretiyordu. Artık rakamların olduğu gibi yazılması isteniyor.
                sayi_kurali = (
                    "\nÖNEMLİ KURAL — SAYILAR VE PARA BİRİMİ:\n"
                    "- Sayıları RAKAMLA yaz (örn: %2.99, 1.000 TL, 6 ay). Sayıları harflerle "
                    "heceleme, telaffuz etme, okunuşunu yazma.\n"
                    "- Para birimi her zaman TÜRK LİRASI'dır (TL). Dolar, cent, euro veya "
                    "başka bir para birimine ASLA çevirme; bu kelimeleri hiç kullanma.\n"
                    "- Verideki rakamı AYNEN aktar; yuvarlama, dönüştürme veya yeniden "
                    "yorumlama yapma."
                )
                kural_ext += sayi_kurali

                # 🗣️ Konuşma geçmişi artık gerçekten prompt'a giriyor (önceden hep "" idi).
                gecmis_metni = gecmis_metni_olustur(gecmis_mesajlari)

                prompt = RAG_CEVAP_PROMPTU.format(
                    dil_kurali=dil,
                    mod_kurali=mod,
                    baglam=safe_baglam + kural_ext,
                    gecmis=gecmis_metni,
                    soru=user_message,
                )

                # 🛠️ HATA DÜZELTMESİ: Bazı Ollama sürümleri/modelleri (özellikle "thinking"
                # destekli varyantlar) akış satırlarında asıl cevabı message.content yerine
                # message.thinking (muhakeme/CoT) alanına yazabiliyor; bu durumda content hep
                # boş kalıyor ve kullanıcı kaynaklar dışında TAMAMEN BOŞ bir yanıt görüyordu
                # (istek hata vermeden, sessizce). Elden geldiğince "think": false ile bunu
                # kaynağında engelliyoruz (desteklemeyen sürümlerde zararsızca yok sayılır/
                # zaten mevcut except bloğu yakalar); ayrıca akış tamamen boş dönerse aşağıda
                # kullanıcıya net bir mesaj gösterilir — asla sessiz bir boşluk kalmaz.
                cevap_uretildi = False
                dusunme_goruldu = False
                try:
                    async with httpx.AsyncClient(timeout=600.0) as client:
                        async with client.stream(
                            "POST", OLLAMA_URL,
                            json={"model": model, "think": False, "messages": [{"role": "user", "content": prompt}]},
                        ) as res:
                            res.raise_for_status()
                            async for line in res.aiter_lines():
                                if line:
                                    mesaj = json.loads(line).get("message", {})
                                    tk = mesaj.get("content", "")
                                    if tk:
                                        cevap_uretildi = True
                                        final_res += tk
                                        await q.put({"type": "token", "content": tk})
                                    elif mesaj.get("thinking"):
                                        dusunme_goruldu = True

                    if not cevap_uretildi:
                        if dusunme_goruldu:
                            logger.warning(
                                "LLM yalnızca 'thinking' (muhakeme) alanına yazdı, message.content boş kaldı — "
                                "kullanıcıya bunun yerine bir uyarı gösteriliyor."
                            )
                        else:
                            logger.warning("LLM akışı hatasız tamamlandı ama hiç içerik üretmedi (boş yanıt).")
                        bos_yanit_msg = (
                            "Bu soru için elimdeki kampanya verilerinde doğrudan bir bilgi bulamadım. "
                            "Size sadece güncel banka kampanyaları hakkında bilgi verebilirim; "
                            "genel yatırım tavsiyesi konusunda yardımcı olamam."
                        )
                        final_res += bos_yanit_msg
                        await q.put({"type": "token", "content": bos_yanit_msg})
                except Exception as llm_err:
                    logger.error(f"LLM (Ollama) akış hatası: {llm_err}")
                    err_msg = "\n\n*(Sistem yoğunluğundan dolayı yapay zeka detaylı yorumu eklenemedi, tablodaki sonuçları inceleyebilirsiniz.)*"
                    final_res += err_msg
                    await q.put({"type": "token", "content": err_msg})

                if kaynaklar_listesi and not db_context:
                    src_str = f"\n\n[SOURCES]{json.dumps(kaynaklar_listesi)}[/SOURCES]\n\n"
                    final_res += src_str
                    await q.put({"type": "token", "content": src_str})

                await q.put({"type": "status", "content": "Öneriler düşünülüyor..."})
                sugs = []
                try:
                    sug_raw = await asyncio.wait_for(
                        suggestion_chain.ainvoke({"question": user_message, "answer": final_res[:300], "language": "Türkçe"}),
                        # 🛠️ Sabit 45sn yerine ortam değişkeninden ayarlanabilir
                        # (AGENT_TIMEOUT_ONERI=0 => zaman aşımı yok).
                        timeout=TIMEOUT_ONERI,
                    )
                    sugs = _onerileri_ayikla(sug_raw)
                except Exception as e:
                    logger.warning(f"Öneri motoru başarısız: {e}")
                    if labels_found:
                        sugs = [f"{labels_found[0]} kampanyalarını detaylandır", "En düşük kâr payı oranları neler?", "Grafik çizer misin?"]
                    else:
                        sugs = ["Başka hangi kampanyalar var?", "En düşük kâr payı oranları neler?", "Taksit oranlarını göster"]

                if sugs:
                    sug_str = f"\n\n[SUGGESTIONS]{json.dumps(sugs[:3])}[/SUGGESTIONS]\n\n"
                    final_res += sug_str
                    await q.put({"type": "token", "content": sug_str})

                # ⚡ Üretilen tam yanıtı (chart + kaynaklar + LLM metni + öneriler dahil)
                # önbelleğe yaz — aynı (dil, mod, banka, soru) kombinasyonu tekrar
                # geldiğinde Mongo/Qdrant/LLM turuna hiç girmeden anında dönülür.
                if cache_uygun and final_res.strip():
                    try:
                        await set_cached_full_response(cache_anahtari, final_res, ttl=CACHE_TTL_SANIYE)
                    except Exception as e:
                        logger.warning(f"Redis önbellek yazma hatası: {e}")

            except Exception as e:
                err_msg = str(e)
                if not err_msg:
                    err_msg = "Sistem Hatası (Bilinmeyen Hata)"
                logger.error(f"Hata: {err_msg}\n{traceback.format_exc()}")
                await q.put({"type": "error", "content": "İşlem sırasında bir gecikme yaşandı."})
            finally:
                await q.put({"type": "done"})

        asyncio.create_task(background_process())

        while True:
            item = await q.get()
            if item["type"] == "done":
                break
            elif item["type"] == "status":
                yield f"[STATUS]{item['content']}[/STATUS]\n\n"
            elif item["type"] == "token":
                yield item["content"]
            elif item["type"] == "error":
                yield f"\n[Hata: {item['content']}]"

    return StreamingResponse(stream_generator(), media_type="text/plain")