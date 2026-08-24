# -*- coding: utf-8 -*-
"""grafigi_hazirla_mongo_dinamik() uçtan uca testi (sahte Mongo verisiyle).

Ağır bağımlılıklar (langchain, qdrant, pymongo, httpx...) sahte modüllerle
değiştiriliyor; amaç yalnızca karar mantığını (grafik mi tablo mu, kaç satır,
hangi metrik, hangi dil) doğrulamak.
"""
import sys, os

# 🛠️ `chatbot` paketini nerede olursa olsun bul: bu dosyanın klasörü, üst
# klasörleri ve her birinin altındaki "backend" klasörü denenir. Böylece test
# dosyası proje kökünde de, backend\ altında da, backend\chatbot\ altında da
# çalışır — hangi klasörden çağrıldığından bağımsız olarak.
def _paketi_bul():
    burasi = os.path.dirname(os.path.abspath(__file__))
    adaylar = []
    for ust in range(4):
        kok = burasi
        for _ in range(ust):
            kok = os.path.dirname(kok)
        adaylar.append(kok)
        adaylar.append(os.path.join(kok, "backend"))
    for aday in adaylar:
        if os.path.isfile(os.path.join(aday, "chatbot", "intent.py")):
            return aday
    return None

_KOK = _paketi_bul()
if _KOK and _KOK not in sys.path:
    sys.path.insert(0, _KOK)
elif not _KOK:
    raise SystemExit(
        "HATA: 'chatbot' paketi bulunamadi. Bu dosyayi projenin backend klasorune "
        "(ya da backend\\chatbot icine) koyup tekrar calistir."
    )
import types, json


def sahte_modul(ad, **icerik):
    m = types.ModuleType(ad)
    for k, v in icerik.items():
        setattr(m, k, v)
    sys.modules[ad] = m
    return m


class _Any:
    def __init__(self, *a, **k): pass
    def __call__(self, *a, **k): return self
    def __getattr__(self, n): return _Any()


class _Logger:
    def __getattr__(self, n):
        return lambda *a, **k: None


sahte_modul("loguru", logger=_Logger())
sahte_modul("httpx", AsyncClient=_Any)
sahte_modul("fastapi", responses=None)
sahte_modul("fastapi.responses", StreamingResponse=_Any)
sahte_modul("langchain_core")
sahte_modul("langchain_core.embeddings", Embeddings=object)
sahte_modul("langchain_qdrant", QdrantVectorStore=_Any)
sahte_modul("qdrant_client", QdrantClient=_Any)
sahte_modul("qdrant_client.models", Filter=_Any, FieldCondition=_Any, MatchValue=_Any)
sahte_modul("pymongo", MongoClient=_Any)
sahte_modul("embedding_client", embed_batch=lambda *a, **k: [])
sahte_modul("chatbot.agents", suggestion_chain=_Any(), derin_dusunme_gerekli_mi=_Any(),
            hyde_belgesi_uret=_Any(), step_back_sorgu_uret=_Any(), coklu_sorgu_uret=_Any(),
            yapisal_analiz_parametreleri_uret=_Any(), supervisor_denetle=_Any(),
            gorsel_niyeti_sor=_Any(),
            persona_belirle=lambda *a, **k: "", TIMEOUT_ONERI=10)
sahte_modul("chatbot.redis_cache", get_cached_full_response=_Any(), set_cached_full_response=_Any())
sahte_modul("chatbot.tools", gercek_finansman_hesapla=lambda *a, **k: "")

from chatbot import generate_response as gr  # noqa: E402

# --- Sahte kampanya havuzu (islenmis_kampanyalar şemasına benzer) -------------
SAHTE = []
for i in range(12):
    SAHTE.append({
        "_id": f"id{i}",
        "banka_kodu": "kuveytturk" if i % 2 == 0 else "albaraka",
        "genel_bilgi": {"kampanya_adi": f"Kampanya {i}", "metin": "Detay metni", "kampanya_turu": "kart"},
        "finansman_detay": {"kar_payi_orani": 2.0 + i * 0.1, "vade_ay": 6 + i},
        "promosyon_detay": {"odul_tutari": 500 * (i + 1)},
    })

gr._kampanya_kayitlarini_getir = lambda: SAHTE


def calistir(soru, view_mode, dil="tr", gecmis=()):
    from chatbot.intent import niyet_bul, gorsel_limiti
    n = niyet_bul(soru, gecmis, dil=dil)
    chart_str, db_context, labels = gr.grafigi_hazirla_mongo_dinamik(
        soru, view_mode,
        zorla_hedef=None, zorla_baslik=None,
        banka_kodu=None if n.kiyas_genis else n.banka_kodu,
        banka_kodlari=None if n.kiyas_genis else n.banka_kodlari,
        zorla_tip=n.gorsel,
        zorla_limit=gorsel_limiti(soru, n.gorsel, view_mode),
        dil=dil,
    )
    veri = json.loads(chart_str.split("[CHART]")[1].split("[/CHART]")[0]) if chart_str else None
    return n, veri, db_context, labels


TESTLER = [
    # (soru, view_mode, dil, beklenen_tip, beklenen_satir, beklenen_db_etiketi)
    ("bana para ödülü olan tüm kampanyaları listeler misin", "analist", "tr", "table", 12, "Ödül"),
    ("bana para ödülü olan tüm kampanyaları grafik olarak verir misin", "analist", "tr", "doughnut", 12, "Ödül"),
    ("can you list me interest rate of the banks", "analist", "en", "table", 12, "Profit Rate"),
    ("Kuveyt Türk ve diğer rakiplerle kıyaslandığında hangi segmentlerde daha yüksek getiri sağlıyor?",
     "analist", "tr", None, 3, None),
    ("Kuveyt Türk'ün kâr payı oranları ne durumda?", "analist", "tr", "table", 3, "Kâr Payı Oranı"),
    ("en yüksek ödülü olan 5 kampanyayı göster", "musteri", "tr", "table", 5, "Ödül"),
]

# --- ÇOK BANKALI KIYASLAMA (analist senaryosu) -------------------------------
BANKA_TESTLERI = [
    # (soru, beklenen_bankalar_kümesi, not)
    ("Kuveyt Türk kampanyalarını listele", {"Kuveyt Türk"}, "tek banka -> filtre uygulanır"),
    ("Kuveyt Türk ile Albaraka'yı ödül bazında kıyasla, listele",
     {"Kuveyt Türk", "Albaraka Türk"}, "İKİ banka -> ikisi de olmalı"),
    ("Ben Kuveyt Türk'te çalışıyorum, rakiplerimizin ödüllerini bizimkiyle kıyasla ve listele",
     {"Kuveyt Türk", "Albaraka Türk"}, "rakip kıyaslaması -> filtre KAPALI, tüm bankalar"),
]

hata = 0
for soru, vm, dil, bek_tip, bek_satir, bek_etiket in TESTLER:
    n, veri, db_context, labels = calistir(soru, vm, dil)
    tip = veri["type"] if veri else None
    satir = len(labels)
    ok = (tip == bek_tip) and (satir == bek_satir)
    if bek_etiket:
        ok = ok and (bek_etiket in db_context)
    if not ok:
        hata += 1
    print(f"{'✅' if ok else '❌'} [{dil}/{vm}] {soru[:58]!r}")
    print(f"      tip={tip} (beklenen {bek_tip}) satır={satir} (beklenen {bek_satir}) "
          f"başlık={veri['title'] if veri else '-'}")
    if db_context:
        print(f"      db_context ilk satır: {db_context.splitlines()[0][:110]}")



# 🛠️ GERÇEK VERİ TUZAĞI: kâr payı SADECE tek bankada dolu. Metrik yanlış
# seçilirse (eskiden genel karşılaştırma hep "kar_payi" diyordu) iki bankalı
# kıyaslama sessizce tek bankaya çöküyordu — canlı testte 6/6 koşuda oldu.
for _k in SAHTE:
    if _k["banka_kodu"] != "kuveytturk":
        _k["finansman_detay"]["kar_payi_orani"] = None   # sadece KT'de oran var

print("\n=== METRİK SEÇİMİ (kâr payı sadece tek bankada dolu) ===")
for soru, beklenen, aciklama in [
    ("Kuveyt Türk ile Albaraka'nın ödüllerini kıyasla ve listele",
     {"Kuveyt Türk", "Albaraka Türk"}, "ödül istendi -> ödül metriği, iki banka da gelmeli"),
    ("Kuveyt Türk ile Albaraka'nın kâr payı oranlarını kıyasla ve listele",
     {"Kuveyt Türk"}, "kâr payı istendi -> sadece verisi olan banka (doğru davranış)"),
]:
    n, veri, db_context, labels = calistir(soru, "analist", "tr")
    gorulen = set(labels)
    ok = gorulen == beklenen
    if not ok: hata += 1
    print(f"{'✅' if ok else '❌'} {soru[:52]!r}")
    print(f"      bankalar={sorted(gorulen)} (beklenen {sorted(beklenen)}) | alan={n.alan} "
          f"| birim={veri['prefix'] if veri else '-'}{veri['suffix'] if veri else ''}")
    print(f"      → {aciklama}")
print("\n=== ÇOK BANKALI FİLTRE ===")
for soru, beklenen, aciklama in BANKA_TESTLERI:
    n, veri, db_context, labels = calistir(soru, "analist", "tr")
    gorulen = set(labels)
    ok = gorulen == beklenen
    if not ok:
        hata += 1
    print(f"{'✅' if ok else '❌'} {soru[:52]!r}")
    print(f"      bankalar={sorted(gorulen)} (beklenen {sorted(beklenen)}) | kodlar={n.banka_kodlari} genis={n.kiyas_genis}")
    print(f"      → {aciklama}")

print("\n" + ("TÜM GRAFİK TESTLERİ GEÇTİ ✅" if hata == 0 else f"{hata} TEST BAŞARISIZ ❌"))
sys.exit(1 if hata else 0)