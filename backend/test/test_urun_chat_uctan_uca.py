# test_urun_chat_uctan_uca.py — /api/chat uç noktasına gerçek istek atan testler.
#
# Neden ayrı bir istemci yazıldı: bu uç nokta multipart FORM verisi bekliyor
# (JSON değil) ve Türkçe karakterler UTF-8 olarak gitmek ZORUNDA. Windows
# kabuğundan `curl --form-string` ile gönderildiğinde metin sistem kod
# sayfasından geçip bozuluyor ('ı'->'ý', 'ğ'->'ð', 'ş'->'þ'); sunucu
# "diðer katýlým bankalarý" görüyor, banka adını ve kıyas niyetini tanıyamıyor
# ve test, uygulamada olmayan bir hatayı varmış gibi gösteriyor.
#
# Çalıştırma:  python test/test_urun_chat_uctan_uca.py [taban_url]

import io
import json
import re
import sys
import urllib.request
import uuid

TABAN = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8003"


def _multipart(alanlar: dict) -> tuple:
    """UTF-8 multipart gövdesi kurar (stdlib ile, bağımlılık eklemeden)."""
    sinir = f"----FinAgentTest{uuid.uuid4().hex}"
    parcalar = []
    for ad, deger in alanlar.items():
        parcalar.append(f"--{sinir}\r\n"
                        f'Content-Disposition: form-data; name="{ad}"\r\n\r\n'
                        f"{deger}\r\n")
    parcalar.append(f"--{sinir}--\r\n")
    govde = "".join(parcalar).encode("utf-8")
    return govde, f"multipart/form-data; boundary={sinir}"


def sor(mesaj: str, view_mode: str = "bankaci", dil: str = "tr",
        zaman_asimi: int = 240) -> str:
    govde, ctype = _multipart({
        "prompt": mesaj, "view_mode": view_mode,
        "language": dil, "history": "[]", "thinking": "auto",
    })
    istek = urllib.request.Request(
        f"{TABAN}/api/chat", data=govde,
        headers={"Content-Type": ctype}, method="POST")
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as y:
        return y.read().decode("utf-8", errors="replace")


def tablo_al(ham: str):
    m = re.search(r"\[CHART\](.*?)\[/CHART\]", ham, re.S)
    return json.loads(m.group(1)) if m else None


def anlatim(ham: str) -> str:
    return re.sub(r"\[(CHART|SOURCES|SUGGESTIONS|STATUS)\].*?\[/\1\]",
                  "", ham, flags=re.S).strip()


# --------------------------------------------------------------------------

KATILIM_SORUSU = (
    "Vakıf Katılım'ın 100.000 TL tutarındaki 32 gün / 1 Ay vadeli katılım hesabı "
    "kâr payı getirisini (%25.99 net kâr oranı, 2,207.01 TL net getiri) diğer "
    "katılım bankalarıyla ve sektör ortalamasıyla karşılaştırarak analiz et."
)
FINANSMAN_SORUSU = (
    "Dünya Katılım'ın 1.000.000 TL tutarındaki 84 ay vadeli konut finansmanını "
    "(%2,89 kâr oranı, aylık 32.648,38 TL taksit) diğer katılım bankalarının aynı "
    "koşuldaki teklifleriyle karşılaştırarak değerlendir."
)

# Mevduatta ASLA görülmemesi gereken kredi dili.
KREDI_DILI = ("aylık taksit", "geri ödeme", "geri ödenecek", "taksit hesaplanıyor")


def test_katilim_hesabi_mevduat_olarak_ele_alinir():
    ham = sor(KATILIM_SORUSU)
    t = tablo_al(ham)
    assert t is not None, "katılım tablosu üretilmedi"
    assert "Katılım Hesap" in t["title"], t["title"]

    # Regresyon: bu soru krediye düşüp "Aylık Taksit: 125.990,00 TL" yazıyordu.
    #
    # Denetim ÜRETİLEN TABLO YÜKÜNDE yapılıyor, serbest metinde değil: model
    # "'geri ödeme' veya 'taksit' gibi kredi kavramları bu analizde geçerli
    # değildir" diye yazabiliyor ve bu DOĞRU davranış. Yasak olan, ürünü kredi
    # gibi SUNMAK — o da tabloya ve hesaplayıcının izlerine bakarak anlaşılır.
    tablo_metni = json.dumps(t, ensure_ascii=False).lower()
    for kotu in KREDI_DILI:
        assert kotu not in tablo_metni, f"mevduat tablosunda kredi dili: {kotu!r}"
    assert "taksit hesaplanıyor" not in ham.lower(), "eski hesaplayıcı tetiklendi"
    assert "125.990" not in ham and "125,990" not in ham

    # Kıyas istendi: en az iki banka olmalı ve sorulan banka listede olmalı.
    bankalar = set(t["labels"])
    assert len(bankalar) >= 2, f"kıyas için tek banka kaldı: {bankalar}"
    assert any("Vakıf" in b for b in bankalar), f"sorulan banka yok: {bankalar}"

    # Değerler veritabanındaki gerçek getiriler olmalı (türetilmiş değil).
    assert 2207.01 in t["values"], t["values"]
    print(f"     bankalar={sorted(bankalar)} degerler={t['values']}")


def test_konut_finansmani_veriden_cevaplanir():
    ham = sor(FINANSMAN_SORUSU)
    t = tablo_al(ham)
    assert t is not None, "finansman tablosu üretilmedi"

    # Regresyon: "elimdeki veritabanı sadece kredi kartı taksit kampanyalarını
    # içermektedir" cevabı veriliyordu.
    for kotu in ("veritabanı sadece kredi kartı", "bilgi bulunmamaktadır"):
        assert kotu not in anlatim(ham).lower(), f"veri yok cevabı döndü: {kotu!r}"

    bankalar = set(t["labels"])
    assert len(bankalar) >= 2, f"kıyas istendi ama tek banka: {bankalar}"
    assert any("Dünya" in b for b in bankalar), f"sorulan banka yok: {bankalar}"

    # Taksit tutarı veritabanındaki gerçek değer olmalı.
    assert 32648.38 in t["values"], t["values"]
    print(f"     bankalar={sorted(bankalar)} satir={len(t['labels'])}")


def test_kampanya_akisi_bozulmadi():
    """Ürün dalları kampanya sorularını çalmamalı."""
    ham = sor("Albaraka Türk'ün kampanyalarını listele")
    t = tablo_al(ham)
    assert t is not None, "kampanya tablosu üretilmedi"
    assert "Katılım Hesap" not in t.get("title", "")
    assert "Finansman Ürünleri" not in t.get("title", "")
    print(f"     baslik={t.get('title')!r} satir={len(t.get('labels', []))}")


def test_tablo_altyazisinda_model_talimati_sizmaz():
    """Regresyon: 'Bunları hâlen geçerli teklifmiş gibi sunma' gibi MODELE
    yazılmış emirler kullanıcıya gösterilen alt başlıkta görünüyordu."""
    ham = sor("Süresi dolmuş kampanyaları da dahil ederek tüm bankaları karşılaştır")
    t = tablo_al(ham)
    if not t:
        print("     (tablo üretilmedi, atlandı)")
        return
    altyazi = t.get("subtitle", "")
    for emir in ("sunma", "SUNMA", "kullanma", "Do not present", "do NOT"):
        assert emir not in altyazi, f"alt başlıkta model talimatı: {altyazi!r}"
    print(f"     altyazi={altyazi[:110]!r}")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    import traceback
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    basarisiz = 0
    for t in testler:
        print(f"  ... {t.__name__}")
        try:
            t()
            print(f"  OK   {t.__name__}")
        except Exception:
            basarisiz += 1
            print(f"  HATA {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(testler) - basarisiz}/{len(testler)} gecti")
    sys.exit(1 if basarisiz else 0)
