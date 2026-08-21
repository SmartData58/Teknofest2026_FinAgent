# =============================================================================
# llm_extractor.py — Lokal LLM ile Bilgi Çıkarımı (hibritin 2. katmanı)
# =============================================================================
#
# NEDEN LLM? Kurallar "%1,89 kâr payı" gibi AÇIK kalıpları yakalar ama
# "avantajlı oranlarla", "kâr paysız", "masraf ödemeden" gibi DOLAYLI
# ifadeleri anlayamaz. Dil modeli bu boşluğu doldurur (şartname 5.2: model
# farklı ifade biçimlerini yorumlayabilmeli).
#
# NEDEN LOKAL (OLLAMA + QWEN2.5 3B)?
# - Şartname 5.9: on-premise şart — OpenAI/Claude gibi dış API'ler YASAK.
# - Ollama [MIT]: modeli tek komutla indirip yerel REST API olarak sunar.
# - Qwen2.5 3B [Apache 2.0]: küçük sınıfta Türkçesi en iyilerden; 4-bit
#   quantize hâli ~2 GB — GPU'SUZ sunucuda çalışır (test: AMD EPYC 4 çekirdek,
#   AVX-512, ~15 token/sn). "Herhangi bir kurum sunucusunda GPU'suz çalışır"
#   cümlesi on-prem kriterinde (%20) güçlü bir artı.
# - CPU yavaşlığı sorun değil: hibrit tasarımda LLM yalnızca kuralların BOŞ
#   bıraktığı alanları doldurur ve pipeline offline/batch çalışır.
#
# HALÜSİNASYON KALKANI (bu dosyanın en önemli güvenlik önlemi)
# ------------------------------------------------------------
# LLM'ler olmayan bilgiyi "uydurabilir". Önlemler:
# 1. temperature=0 → yaratıcılık kapalı, deterministike yakın çıktı
# 2. format="json" → Ollama çıktıyı geçerli JSON'a ZORLAR
# 3. Prompt: "SADECE metinde açıkça yazanı doldur, yoksa null" + alan
#    tanımları ve NEGATİF örnekler (neyin o alan OLMADIĞI)
# 4. SAYISAL DOĞRULAMA (sayı sınırlı): modelin verdiği her sayı, metinde
#    BAĞIMSIZ BİR SAYI olarak geçiyor mu diye kontrol edilir. Düz alt-dize
#    araması YETMEZ — 15. adım ölçümünde "1.25", metindeki "1.250 TL"nin
#    içinde eşleşip kalkanı deldi. Regex lookaround ile eşleşmenin bitişiğinde
#    rakam/binlik ayracı varsa eşleşme SAYILMAZ.
# 5. BAĞLAM DOĞRULAMASI: değer metinde var olsa bile YANLIŞ ALANA atanmış
#    olabilir ("%5 mil kazanımı" kâr payı değildir — 15. adımda 12 vaka).
#    Kural katmanındaki bağlam penceresi ilkesi LLM bulgularına da uygulanır:
#    değerin geçtiği yerin çevresinde alanın pozitif ipucu ARANIR, negatif
#    ipucu (mil/puan/komisyon...) varsa bulgu REDDEDİLİR.
# 6. Güven skoru 0.7 (kurallar 1.0): dashboard'da LLM bulgusu olduğu görünür.
# =============================================================================

import json
import os
import re

import requests

from backend.nlp.extraction.rule_based import AlanBulgusu

OLLAMA_URL = os.environ.get("FINAGENT_OLLAMA_URL", "http://llm:11434")
MODEL = os.environ.get("FINAGENT_LLM_MODEL", "qwen3.5:4b")
LLM_GUVEN = 0.7          # LLM bulgularının güven skoru (kural=1.0'dan düşük)
ZAMAN_ASIMI = 180        # CPU'da tek istek için üst sınır (saniye)

# LLM'e sorulabilecek alanlar ve JSON şemasındaki tip açıklamaları.
# Tarihler bilinçli YOK: kural katmanı tarihlerde zaten 46/46 — LLM'e sormak
# maliyet + halüsinasyon riski, kazanç sıfır.
# Alan tanımları negatif örnek İÇERİR (15. adım ölçüm dersi): model alan
# adından ne kastettiğimizi bilemez — neyin o alan OLMADIĞINI söylemek,
# ne olduğunu söylemek kadar önemli çıktı.
ALAN_SEMASI = {
    "kar_payi_orani": (
        '"kar_payi_orani": sayı|null  '
        "(finansman kâr payı veya katılma hesabı kâr paylaşım oranı, örn 1.89. "
        "DİKKAT: mil/puan kazanım oranı, indirim oranı ve komisyon oranı "
        "kâr payı DEĞİLDİR — bunlar için null yaz)"
    ),
    # NOT: örnek sayı YAZMA — model prompttaki örneği cevap sanıp kopyalıyor
    # (ölçümde "120" onlarca kampanyada uydurma cevap olarak döndü).
    "vade_ay": '"vade_ay": tamsayı|null  (AY cinsinden vade; yıl verilmişse 12 ile çarp)',
    "taksit_sayisi": (
        '"taksit_sayisi": tamsayı|null  '
        "(yalnızca metinde \"taksit\" kelimesiyle geçen sayı)"
    ),
    "finansman_tutari": (
        '"finansman_tutari": sayı|null  '
        "(TL, kredi/finansman üst limiti. DİKKAT: minimum hesap açılış tutarı, "
        "ATM para yatırma/çekme limiti ve ödül tutarı finansman DEĞİLDİR)"
    ),
    "odul_tutari_tl": (
        '"odul_tutari_tl": sayı|null  '
        "(TL cinsinden hediye/çek/bonus/puan ödülü. DİKKAT: finansman veya "
        "taksit desteği ödül DEĞİLDİR)"
    ),
    # hedef_kitle burada YER ALMAZ: sınıflandırma ayrı prompt ile yapılır
    # (aşağıdaki _siniflandirma_promptu ve dosya sonundaki gerekçe notu).
}


def llm_hazir() -> bool:
    """Ollama ayakta ve istenen model yüklü mü?"""
    try:
        url = f"{OLLAMA_URL}/api/tags"
        cevap = requests.get(url, timeout=5)
        
        if cevap.status_code != 200:
            print(f" ⚠️ Ollama yanıt verdi ancak durum kodu hatalı: {cevap.status_code}")
            return False

        models = cevap.json().get("models", [])
        
        # Yüklü modellerin isimlerini topla (hem 'name' hem 'model' alanını kontrol et)
        yuklu_modeller = []
        for m in models:
            if "name" in m:
                yuklu_modeller.append(m["name"])
            if "model" in m:
                yuklu_modeller.append(m["model"])

        aranan_kok = MODEL.split(":")[0]  # örn: "qwen2.5"
        
        # Tam eşleşme veya kök isim eşleşmesi kontrolü
        model_bulundu = any(
            m == MODEL or m.startswith(f"{aranan_kok}:") or m == aranan_kok
            for m in yuklu_modeller
        )

        if not model_bulundu:
            print(f" ⚠️ Aranan model ('{MODEL}') Docker içindeki Ollama'da bulunamadı!")
            print(f" 📋 Docker'da Mevcut Modeller: {list(set(yuklu_modeller))}")
            print(f" 💡 Çözüm için terminalde şu komutu çalıştırın: docker exec -it <konteynir_adi> ollama pull {MODEL}")
            return False

        return True

    except Exception as e:
        print(f" ❌ Ollama Bağlantı Hatası ({OLLAMA_URL}): {e}")
        return False


def _prompt_kur(metin: str, istenen_alanlar: list[str]) -> str:
    """Yalnızca EKSİK sayısal alanları soran dar kapsamlı prompt üretir.

    Neden dar kapsam? (1) Kısa çıktı = CPU'da hız, (2) modelin işi ne kadar
    dar tanımlanırsa doğruluk o kadar yüksek, (3) kuralın bulduğu alanı
    LLM'e tekrar sormak gereksiz risk.
    """
    sema = ",\n  ".join(ALAN_SEMASI[a] for a in istenen_alanlar)
    return (
        "Türkçe katılım bankası kampanya metninden bilgi çıkarıyorsun.\n"
        "KURALLAR:\n"
        "- SADECE metinde açıkça yazan bilgileri doldur.\n"
        "- Metinde olmayan bilgiye null yaz. ASLA tahmin etme.\n"
        "- Sayıları Türkçe biçimden çevir: %1,89 → 1.89 | 50.000 TL → 50000\n"
        f"Şu JSON şemasıyla cevap ver:\n{{\n  {sema}\n}}\n\n"
        f"METİN: {metin}\n\nJSON:"
    )


# NEDEN AYRI PROMPT? Sınıflandırma (hedef_kitle) ile sayısal çıkarım aynı
# prompt'tayken, sayısal alan tanımlarına eklenen "DİKKAT: ... DEĞİLDİR"
# blokları sınıflandırmayı BOZDU: 3. koşu ölçümünde model "Kuveyt Türk
# Müşterilerine Özel" kampanyasına bile yeni_musteri dedi (1. koşuda, sade
# prompt'la doğruydu; hedef_kitle doğruluğu %90 → ~%71 düştü). Küçük model
# tek prompt'ta iki farklı görev + yoğun negatif talimat kaldıramıyor.
# İki dar görev > bir geniş görev. Ek maliyet: kampanya başına 1 kısa çağrı.
def _siniflandirma_promptu(metin: str) -> str:
    return (
        "Türkçe katılım bankası kampanya metnini sınıflandır.\n"
        "Soru: Kampanya KİMLERE yönelik?\n"
        '- "yeni_musteri": bankaya yeni müşteri olacaklara özel\n'
        '- "mevcut_musteri": bankanın mevcut kart/hesap sahiplerine yönelik\n'
        '- "maas_musterisi": maaşını bankaya taşıyanlara özel\n'
        '- "segment": belirli bir gruba özel (esnaf, KOBİ, işletme, emekli, öğrenci)\n'
        "- null: metinden anlaşılmıyor\n"
        'Şu JSON ile cevap ver: {"hedef_kitle": ...}\n\n'
        f"METİN: {metin}\n\nJSON:"
    )


# Sayı sınırı (lookaround): eşleşmenin HEMEN öncesinde rakam ya da
# rakama yapışık ayraç (./,) olamaz; hemen sonrasında rakam ya da
# "ayraç+rakam" olamaz. Böylece:
#   "1.25"  artık "1.250 TL" içinde eşleşemez (sonrası '0')
#   "5"     artık "5.000 TL" içinde eşleşemez (sonrası '.0')
#   "12"    artık "31.12.2026" içinde eşleşemez (öncesi '.')
_SINIR_ON = r"(?<![\d.,])"
_SINIR_SON = r"(?!\d)(?![.,]\d)"


def _varyantlar(deger: float) -> set[str]:
    """Bir sayının metinde geçebilecek Türkçe/İngilizce yazımları.

      1.89   → "1.89" | "1,89"
      50000  → "50000" | "50.000" | "50 bin"
    """
    varyantlar = set()
    if deger == int(deger):
        tam = int(deger)
        varyantlar.add(str(tam))                                  # 50000
        varyantlar.add(f"{tam:,}".replace(",", "."))              # 50.000
        if tam >= 1000 and tam % 1000 == 0:
            varyantlar.add(f"{tam // 1000} bin")                  # 50 bin
    ondalik = f"{deger:g}"                                        # 1.89
    varyantlar.add(ondalik)
    varyantlar.add(ondalik.replace(".", ","))                     # 1,89
    return varyantlar


def sayi_konumlari(deger: float, metin: str) -> list[tuple[int, int]]:
    """Halüsinasyon kalkanı 1. basamak: değerin metindeki SINIR-DOĞRU
    eşleşme konumlarını döndürür. Boş liste = değer metinde bağımsız bir
    sayı olarak YOK → uydurma kabul edilir.

    Konumlar döndürülür (bool değil) çünkü 2. basamak (bağlam doğrulaması)
    aynı konumların çevresine bakacak — iki kez arama yapılmaz.
    """
    if deger != deger:  # NaN koruması
        return []
    konumlar = []
    for v in _varyantlar(deger):
        desen = re.compile(_SINIR_ON + re.escape(v) + _SINIR_SON)
        konumlar.extend((e.start(), e.end()) for e in desen.finditer(metin))
    return konumlar


# Halüsinasyon kalkanı 2. basamak: alan başına bağlam kuralları.
# Değerin geçtiği konumların ±60 karakterlik penceresinde:
#   - POZİTİF ipuçlarından en az biri OLMALI (alanın kanıtı)
#   - NEGATİF ipuçlarından hiçbiri OLMAMALI (başka alanın kanıtı)
# En az bir konum bu iki şartı sağlarsa bulgu kabul edilir.
# Listeler 15. adım ölçümündeki 19 gerçek hatadan türetildi:
#   "%5 ekstra mil"        → kâr payı sanılmıştı  → "mil" negatif
#   "650 TL BES bonusu"    → kâr payı sanılmıştı  → "bonus" negatif
#   "hesap açılış tutarı"  → finansman sanılmıştı → "açıl" negatif
#   "para yatırma limiti"  → finansman sanılmıştı → "para yatırma" negatif
_BAGLAM_KURALLARI: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "kar_payi_orani": (
        ("kâr pay", "kar pay", "paylaşım", "oran"),
        ("mil", "puan", "indirim", "iskonto", "bonus", "komisyon",
         "hediye", "çekiliş", "iade", "ödül"),
    ),
    # finansman pozitifleri DARALTILDI (2026-07-17 Emlak denetimi): eski
    # listedeki "taksit/harcama/ödeme", ödül basamaklarını ("15.000-49.999 TL
    # arasındaki ilk HARCAMAYA 750 TL ParafPara") ve sepet eşiklerini
    # ("2.000 TL ve üzeri siparişlerde 3 TAKSİT") finansman diye geçirdi —
    # 7 bulgunun 7'si de yanlıştı. Bu kelimeler finansman KANITI değil,
    # tam tersine başka alanların dilidir. "kredi kart" negatifi: kart
    # kampanyalarındaki "Kredi Kartı" finansman ürünü kanıtı sayılmasın.
    "finansman_tutari": (
        ("finansman", "kredi", "limit", "destek"),
        ("açıl", "para yatırma", "para çekme", "mil", "puan", "hediye",
         "bonus", "iade", "parafpara", "kredi kart"),
    ),
    "odul_tip": (
        ("hediye", "ödül", "odul", "bonus", "puan", "mil", "çek", "kazan"),
        ("finansman", "kredi"),
    ),
    # "vade farksız 3 taksit"teki "vade" kelimesi vade SÜRESİ kanıtı değildir
    # (3. koşu ölçümünde 6 kampanyaya vade_ay=taksit sayısı yazılmıştı);
    # "3 ay öteleme/erteleme" ve "ilk taksit için 3 aya varan ödemesiz dönem"
    # (4. koşu, k39) de ne taksit sayısı ne vadedir.
    "taksit_sayisi": (("taksit",), ("ötele", "ertele", "ödemesiz")),
    "vade_ay": (("vade",), ("vade fark", "ötele", "ertele", "ödemesiz")),
}

_PENCERE_GENISLIGI = 60


def baglam_uygun_mu(alan: str, konumlar: list[tuple[int, int]], metin: str) -> bool:
    """Konumlardan en az biri alanın bağlam kurallarını sağlıyor mu?"""
    pozitifler, negatifler = _BAGLAM_KURALLARI.get(alan, ((), ()))
    if not pozitifler:  # bağlam kuralı tanımsız alan → yalnız 1. basamak yeter
        return True
    kucuk = metin.lower()
    for bas, bit in konumlar:
        pencere = kucuk[max(0, bas - _PENCERE_GENISLIGI): bit + _PENCERE_GENISLIGI]
        if (any(p in pencere for p in pozitifler)
                and not any(n in pencere for n in negatifler)):
            return True
    return False


_GECERLI_KITLELER = {"yeni_musteri", "mevcut_musteri", "maas_musterisi", "segment"}

# "segment" cevabı için METİN KANITI şartı (2026-07-17 denetimi): model,
# Emlak'ın sıradan kart kampanyalarının 13'üne (giyim/kozmetik/POS taksiti...)
# "segment" dedi — oysa segment demografik/mesleki bir gruptur. Kapalı liste
# doğrulaması etiketin GEÇERLİ olduğunu garanti eder ama DOĞRU olduğunu etmez;
# metinde segment kelimesi hiç geçmiyorsa bulgu düşürülür (null > yanlış).
_SEGMENT_KANITI = re.compile(
    r"esnaf|çiftçi|kobi|şah[ıi]s\s+firma|işletme\s+sahi|işletmelere|işletmeniz"
    r"|emekli|öğrenci|maaş|genç\w*\s+özel|kadın\w*\s+özel", re.IGNORECASE)

# hybrid.py'nin "hangi alanlar LLM'e sorulabilir?" sorusunun cevabı:
# sayısal şema alanları + ayrı prompt'la sorulan hedef_kitle.
SORULABILIR_ALANLAR = list(ALAN_SEMASI) + ["hedef_kitle"]


def _ollama_json(prompt: str) -> dict | None:
    """Ollama'ya tek istek atar, JSON cevabı döndürür (hata → None)."""
    try:
        cevap = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",  # geçerli JSON zorunlu
                "options": {
                    "temperature": 0,  # uydurma kapalı
                    "num_ctx": 4096,  # bağlam penceresi
                },
                "keep_alive": "30m",  # batch boyunca modeli RAM'de tut
            },
            timeout=ZAMAN_ASIMI,
        )

        # 1. Ollama yanıtından ham metni al
        raw_response = cevap.json().get("response", "").strip()

        if not raw_response:
            return None

        # 2. Doğrudan parse etmeyi dene (En hızlı yol)
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            pass

        # 3. Hata aldıysa Temizlik Yap:
        # a) Qwen 3.5 düşünce bloklarını (<think>...</think>) temizle
        temiz_metin = re.sub(
            r"<think>[\s\S]*?</think>", "", raw_response
        ).strip()

        # b) ```json ... ``` markdown bloklarını temizle
        temiz_metin = re.sub(
            r"```(?:json)?\s*([\s\S]*?)\s*```", r"\1", temiz_metin
        ).strip()

        # c) Metin içinde kalan ilk '{' ve son '}' karakterleri arasını çek
        json_match = re.search(r"\{[\s\S]*\}", temiz_metin)
        if json_match:
            return json.loads(json_match.group(0))

        # Temizliğe rağmen JSON ayrıştırılamadıysa
        raise json.JSONDecodeError(
            "Geçerli bir JSON objesi bulunamadı", raw_response, 0
        )

    except (requests.RequestException, json.JSONDecodeError, KeyError) as hata:
        print(
            f"    LLM atlandı ({hata.__class__.__name__}) — kural bulgularıyla devam"
        )
        return None


def llm_ile_cikar(metin: str, istenen_alanlar: list[str]) -> dict[str, AlanBulgusu]:
    """Eksik alanları lokal LLM'e sorar; doğrulamadan geçenleri döndürür.

    İki ayrı görev, iki ayrı istek (gerekçe: _siniflandirma_promptu notu):
      1. sayısal ÇIKARIM (ALAN_SEMASI alanları) → iki basamaklı kalkan
      2. hedef_kitle SINIFLANDIRMASI → kapalı liste doğrulaması

    Ollama'ya ulaşılamazsa/parse hatasında BOŞ sözlük döner — pipeline
    kural bulgularıyla yoluna devam eder (zarif geri düşüş / graceful
    degradation: LLM bir zenginleştirme katmanı, tek hata noktası değil).
    """
    if not metin:
        return {}
    bulgular: dict[str, AlanBulgusu] = {}

    # --- 1. istek: sayısal çıkarım ----------------------------------------
    sayisal_alanlar = [a for a in istenen_alanlar if a in ALAN_SEMASI]
    if sayisal_alanlar:
        ham_json = _ollama_json(_prompt_kur(metin, sayisal_alanlar)) or {}
        for alan in sayisal_alanlar:
            deger = ham_json.get(alan)
            if deger is None:
                continue  # model "metinde yok" dedi — doğru davranış, alan boş kalır
            # Tip zorlama + iki basamaklı halüsinasyon kalkanı
            try:
                sayi = float(deger)
            except (TypeError, ValueError):
                continue
            konumlar = sayi_konumlari(sayi, metin)
            if not konumlar:
                print(f"    LLM RED (sayı sınırı): {alan}={sayi} metinde bağımsız sayı olarak yok")
                continue
            if alan in ("vade_ay", "taksit_sayisi"):
                # PARA değeri adet/süre olamaz (k36 denetim bulgusu, 2026-07-17):
                # "toplam 2.000 TL bonus ... taksitli harcamalar dahildir"
                # cümlesinde pencereye giren "taksit" kelimesi kalkanı delmiş,
                # taksit_sayisi=2000 yazılmıştı. Eşleşmenin hemen ardında
                # TL/₺ varsa o konum tutar demektir, aday listeden düşer.
                konumlar = [(b, s) for b, s in konumlar
                            if not re.match(r"\s*(tl\b|₺)", metin[s:s + 4],
                                            re.IGNORECASE)]
                if not konumlar:
                    print(f"    LLM RED (para değeri): {alan}={sayi} yalnız TL tutarı olarak geçiyor")
                    continue
                # Makullük sınırı (ikinci kemer): taksit/vade alanları için
                # alan bilgisi — 60 taksit / 360 ay üstü değer gerçek dünyada
                # kampanya değil, çıkarım hatasıdır.
                ust = 60 if alan == "taksit_sayisi" else 360
                if not 1 <= sayi <= ust:
                    print(f"    LLM RED (makullük): {alan}={sayi} olası aralık dışı (1-{ust})")
                    continue
            if not baglam_uygun_mu(alan, konumlar, metin):
                print(f"    LLM RED (bağlam): {alan}={sayi} çevresinde alan kanıtı yok")
                continue
            if alan in ("vade_ay", "taksit_sayisi"):
                sayi = int(sayi)
            bulgular[alan] = AlanBulgusu(sayi, f"LLM cikarimi (metinde dogrulandi): {deger}",
                                         f"llm:{MODEL}")

    # --- 2. istek: hedef kitle sınıflandırması -----------------------------
    if "hedef_kitle" in istenen_alanlar:
        ham_json = _ollama_json(_siniflandirma_promptu(metin)) or {}
        deger = ham_json.get("hedef_kitle")
        # Kapalı liste doğrulaması: 4 etiket dışındaki her şey çöp
        if deger in _GECERLI_KITLELER:
            if deger == "segment" and not _SEGMENT_KANITI.search(metin):
                print("    LLM RED (segment kanıtı): metinde segment kelimesi yok")
            else:
                bulgular["hedef_kitle"] = AlanBulgusu(
                    deger, f"LLM siniflandirmasi: {deger}", f"llm:{MODEL}")

    return bulgular
