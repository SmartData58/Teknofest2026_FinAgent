# -*- coding: utf-8 -*-
"""TEKNOFEST tanitim videosu — sahne kliplerini siteden kaydeder.

KAYNAK: "video cekim-render .md" dosyasindaki sahne sahne cekim talimatlari.
Dosya adlari o dokumandaki isimlendirmeyle BIREBIR ayni (sahne_02_... gibi) —
kurguda eslesme icin.

CIKTI: 1920x1080 / 30 fps h264 mp4 (dokumanin istedigi sekans ayari).

CERCEVEYE SIGDIRMA
------------------
Dokuman "sayfalar kaydirilmadan tek karede butun olarak" istiyor. Olculdu:
/campaigns icerigi kanit paneli acikken 1624 px ve bu deger genislikten
BAGIMSIZ (icerik sutunu max-width ile sinirli, genisletince sadece yanlarda
beyaz bosluk artiyor). Bu yuzden goruntu alani sahne basina ayri seciliyor ve
kayit 1920x1080'e olceklenerek yaziliyor:
2880x1620 denendi: icerik tek karede siginca sutun kadrajin ancak %53'unu
dolduruyor ve 1080p'ye inince metin okunmaz oluyor. Secilen denge 2304x1296
(%69 dolgu, 0.83 kucultme); artan 300-400 px kubik egriyle kaydiriliyor.
Sigmayan sayfalarda (dashboard 2336 px, finansman 6926 px, index 11292 px)
kubik egriyle YUMUSAK KAYDIRMA kullaniliyor — dokuman zaten PDF ciktisi ve
kapanis icin kaydirma istiyor.

ANIMASYONLAR
------------
Chromium varsayilan olarak arka plan sekmelerinde rAF'i kisiyor; kisma
kapatilmazsa arayuzun giris animasyonlari kayda DUSMUYOR. Asagidaki bayraklar
ve `reduced_motion="no-preference"` bunun icin var.
"""

import os
import sys
import time

from playwright.sync_api import sync_playwright

TABAN = os.getenv("SUNUM_TABAN", "http://frontend:3000")
CIKIS = "/tmp/sahne"

# KALITE: goruntu alani = kayit boyutu. Playwright, ikisi farkli oldugunda
# kareyi olcekliyor ve metin yumusuyordu (2304 -> 1920 = 0.83 kucultme).
# Olceksiz kayit gozle gorulur derecede daha keskin.
#
# Daha buyuk kadraj (2560/2880) DENENDI ve birakildi: icerik sutunu `max-width`
# ile sinirli oldugu icin genisletmek metni buyutmuyor, yalnizca yanlarda beyaz
# bosluk aciyor. Metnin piksel boyutu her iki durumda da ayni.
KAYIT = {"width": 1920, "height": 1080}
GENIS = KAYIT
NORMAL = KAYIT

BAYRAKLAR = [
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--force-device-scale-factor=1",
    "--force-prefers-reduced-motion=no-preference",
]


# ----------------------------------------------------------------- yardimcilar

def kubik(t: float) -> float:
    """ease-in-out cubic. Dogrusal kaydirma makine gibi gorunuyor."""
    return 4 * t * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 3) / 2


# Kaydirma animasyonu SAYFANIN ICINDE calisiyor, disaridan adim adim degil.
#
# NEDEN: Onceki surum her karede bir `page.evaluate` yapiyordu. Ana sayfa gibi
# surekli animasyonlu (parcacik/starfield) sayfalarda ana is parcacigi mesgul
# oldugu icin her gidis-donus saniyelere ciktı ve kayit 18 dakika surup asili
# kaldi. rAF ile sayfa kendi icinde kaydiginda hem kilitlenme olmuyor hem de
# hareket ekran tazeleme hiziyla senkron, yani daha akici.
KAYDIRMA_JS = """([hedef, sureMs]) => new Promise((bitti) => {
  const kap = document.getElementById('main-scroller');
  const oku = () => kap ? kap.scrollTop : window.scrollY;
  const yaz = (y) => { if (kap) kap.scrollTop = y; else window.scrollTo(0, y); };
  const bas = oku();
  const fark = hedef - bas;
  if (Math.abs(fark) < 2 || sureMs <= 0) { yaz(hedef); return bitti(oku()); }
  const t0 = performance.now();
  const kubik = (t) => t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t + 2, 3) / 2;
  let kapandi = false;
  const kapat = () => { if (!kapandi) { kapandi = true; bitti(oku()); } };
  // BEKCI: Lenis gibi bir yumusak-kaydirma motoru sayfayi devraldiginda
  // rAF zinciri kopabiliyor ve promise hic cozulmuyordu — sahne 9 kaydi bu
  // yuzden 8 dakikaya cikti. Sure asilirsa her halukarda cikiyoruz.
  setTimeout(kapat, sureMs + 1500);
  const adim = (simdi) => {
    if (kapandi) return;
    const t = Math.min(1, (simdi - t0) / sureMs);
    yaz(bas + fark * kubik(t));
    if (t < 1) requestAnimationFrame(adim); else kapat();
  };
  requestAnimationFrame(adim);
})"""


def kaydir(s, hedef, sure=1.8, adim=None):
    """Kubik egriyle yumusak kaydirma (adim parametresi artik kullanilmiyor)."""
    s.evaluate(KAYDIRMA_JS, [hedef, int(sure * 1000)])
    time.sleep(0.15)


def kaydir_guvenli(s, hedef, sure=1.8):
    """Ana sayfa icin: Lenis varsa onunla, yoksa normal yolla kaydirir.

    Ana sayfa (index) Lenis + ScrollTrigger kullaniyor. Disaridan `scrollTop`
    yazmak Lenis'in kendi dongusuyle carpisiyor. Lenis'in kendi API'siyle
    kaydirmak hem catismayi bitiriyor hem de sitenin gercek his verdigi
    hareketi kaydediyor.
    """
    # Sayfada `window.lenis` GORUNUYOR ama uzerinde `scrollTo` yok (surumu
    # farkli bir nesne aciyor). O yola guvenmek yerine normal kaydirma
    # kullaniliyor; asili kalma riskini KAYDIRMA_JS'teki bekci kapatiyor.
    kaydir(s, hedef, sure=sure)


def imlec(s, x0, y0, x1, y1, sure=0.8, adim=30):
    for i in range(adim + 1):
        t = kubik(i / adim)
        s.mouse.move(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
        time.sleep(sure / adim)


def dibe_in(s, sure=2.6, bekle=1.5):
    """Sayfayi en alta kadar kubik egriyle indirir ve orada bekler.

    Kadraja sigmayan sayfalarda (dashboard, finansman, index) icerigin tamami
    ancak boyle goruntuye giriyor.
    """
    dip = s.evaluate("""() => { const e = document.getElementById('main-scroller');
        return e ? e.scrollHeight - e.clientHeight
                 : document.body.scrollHeight - window.innerHeight; }""")
    if dip and dip > 40:
        kaydir(s, dip, sure=sure)
        time.sleep(bekle)
    return dip


def mod(s, ad):
    """'Musteri' / 'Banka Calisani' gorunumu — gecis animasyonu kayda girsin."""
    try:
        s.get_by_text(ad, exact=False).first.click(timeout=5000)
        time.sleep(0.5)
        # Dugmenin ustunde kalan imlec, siyah aciklama balonunu kadrajda tutuyor.
        s.mouse.move(120, 1150)
        time.sleep(1.0)
        return True
    except Exception as e:
        print(f"    ! mod '{ad}': {str(e)[:70]}")
        return False


def tur_sec(s, secenek):
    """/campaigns TUR filtresinden bir tur secer.

    TUZAK: filtre girdilerinde `type` ozniteligi yok (input[type=text] onlari
    bulamaz) ve `.click()` acilir listeyi ACMIYOR — disari-tiklama isleyicisi
    hemen kapatiyor. Yalnizca `.focus()` ise yariyor.
    """
    alan = s.locator("input:not([type])").nth(1)   # 0=banka 1=tur 2=hedef kitle
    k = alan.bounding_box()
    if k:
        imlec(s, k["x"] - 420, k["y"] + 260, k["x"] + 60, k["y"] + 18, sure=0.9)
    alan.focus()
    time.sleep(1.1)                                 # liste acilma animasyonu
    sec = s.locator("label:has(input[type=checkbox])", has_text=secenek).first
    ks = sec.bounding_box()
    if ks:
        imlec(s, k["x"] + 60, k["y"] + 18, ks["x"] + 70, ks["y"] + 14, sure=0.8)
    sec.click()
    time.sleep(1.5)                                 # tablo daralma animasyonu


def pdf_goster(s, pdf_yolu, baslik="FinAgent Raporu"):
    """Indirilen PDF'i AYNI kayitta ekranda gosterir ve bastan asagi kaydirir.

    NEDEN DOGRUDAN ACMIYORUZ: headless Chromium `file://...pdf` adresini
    goruntulemiyor, indirmeye basliyor ("Page.goto: Download is starting").
    Bu yuzden sayfalar PyMuPDF ile yuksek cozunurlukte PNG'ye cevrilip
    tek bir HTML'de alt alta diziliyor — ekranda gorunen, sistemin urettigi
    GERCEK PDF'in kendisi.
    """
    import base64
    import fitz

    belge = fitz.open(pdf_yolu)
    gorseller = []
    for sayfa in belge:
        pix = sayfa.get_pixmap(dpi=150)
        gorseller.append(base64.b64encode(pix.tobytes("png")).decode())
    belge.close()

    kutular = "".join(
        f'<img src="data:image/png;base64,{g}" alt="sayfa {i+1}">'
        for i, g in enumerate(gorseller))
    html = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<title>{baslik}</title><style>
  html,body{{margin:0;background:#f1f5f9;font-family:'Segoe UI',system-ui,sans-serif}}
  .cerceve{{max-width:1080px;margin:0 auto;padding:40px 0 80px}}
  .ust{{position:sticky;top:0;background:#ffffffee;backdrop-filter:blur(8px);
       border-bottom:1px solid #e2e8f0;padding:14px 24px;font-size:15px;
       font-weight:600;color:#0f172a;z-index:5}}
  .ust span{{color:#2563eb}}
  img{{display:block;width:100%;margin:0 auto 26px;border-radius:10px;
      box-shadow:0 10px 30px rgba(15,23,42,.14);background:#fff}}
</style></head><body>
<div class="ust">{baslik} — <span>sistemin urettigi PDF ciktisi</span> ·
 {len(gorseller)} sayfa</div>
<div class="cerceve">{kutular}</div></body></html>"""

    yol = "/tmp/rapor_onizleme.html"
    with open(yol, "w", encoding="utf-8") as f:
        f.write(html)
    s.goto("file://" + yol, wait_until="load", timeout=30000)
    time.sleep(1.8)
    dibe_in(s, sure=4.2, bekle=1.8)      # raporu bastan asagi gez
    print(f"    PDF ekranda gosterildi ({len(gorseller)} sayfa)")


def yaz(s, kutu, metin, gecikme=38):
    kutu.click()
    for ch in metin:
        kutu.type(ch, delay=gecikme)


def klip(tarayici, ad, islem, alan=GENIS):
    kok = os.path.join(CIKIS, ad)
    os.makedirs(kok, exist_ok=True)
    c = tarayici.new_context(
        viewport=alan,
        record_video_dir=kok,
        record_video_size=KAYIT,
        locale="tr-TR",
        reduced_motion="no-preference",
        accept_downloads=True,
    )
    # On yuz API'yi host adresiyle (localhost:8003) cagiriyor; konteyner
    # icindeki tarayicida bu adres yok. Yonlendirmeden once tablolar bos cikiyor.
    c.route("**localhost:8003/**", lambda r, i: r.continue_(
        url=i.url.replace("http://localhost:8003", "http://backend:8000")))

    s = c.new_page()
    t0 = time.time()
    try:
        islem(s)
    except Exception as e:
        print(f"    ! {ad}: {type(e).__name__}: {str(e)[:110]}")
    time.sleep(0.7)
    s.close()
    c.close()

    dosyalar = [f for f in os.listdir(kok) if f.endswith(".webm")]
    if dosyalar:
        os.replace(os.path.join(kok, dosyalar[0]),
                   os.path.join(CIKIS, f"{ad}.webm"))
        print(f"  {ad}.webm  ({time.time() - t0:.1f} sn)")
    else:
        print(f"  ! {ad}: video olusmadi")


# --------------------------------------------------------------------- sahneler

def sahne_02_cikarim_kanit(s):
    """00:08-00:20 — VIDEONUN KALBI. /campaigns -> kanit paneli."""
    s.goto(f"{TABAN}/campaigns", wait_until="networkidle", timeout=60000)
    time.sleep(2.0)
    mod(s, "Banka Çalışanı")

    # TUR filtresinden "Ihtiyac": serbest arama yerine bilincli olarak filtre
    # kullaniliyor — 599 -> 3 daralmasi ekranda net gorunuyor.
    tur_sec(s, "İhtiyaç")

    s.wait_for_selector("tbody tr", timeout=20000)
    # Ilk satir degil, KAR PAYI ORANI DOLU olan satir seciliyor: kanit tablosu
    # boylece "%1,99 -> 1.99  REGEX  0.99" gibi guclu bir ornek gosteriyor.
    # (Ilk satirda oran "%0" ve guven 0.35 cikiyordu.)
    satir = s.locator("tbody tr", has_text="1,99").first
    if satir.count() == 0:
        satir = s.locator("tbody tr").first
    kutu = satir.bounding_box()
    if kutu:
        imlec(s, GENIS["width"] * 0.62, 420, kutu["x"] + 300, kutu["y"] + 20)
    satir.click()
    time.sleep(2.2)                     # kanit paneli acilma animasyonu
    kaydir(s, 430, sure=1.6)            # kanit tablosu kadraja otursun

    # "Kampanyanin islenmis metni" akordeonunu ac
    try:
        s.get_by_text("işlenmiş metni", exact=False).first.click(timeout=4000)
        time.sleep(2.0)
    except Exception:
        pass
    time.sleep(1.6)
    dibe_in(s, sure=2.8, bekle=2.2)     # islenmis metnin tamami gorunsun


def sahne_03_dashboard_pdf(s):
    """00:20-00:30 — dashboard, mod degisimi, PDF ciktisi."""
    s.goto(f"{TABAN}/dashboard", wait_until="networkidle", timeout=60000)
    time.sleep(2.6)                     # kart giris animasyonlari
    mod(s, "Banka Çalışanı")
    time.sleep(1.4)

    # Tier 1 filtresi (dokumanin istedigi adim)
    try:
        s.locator("button", has_text="Tier 1").first.click(timeout=5000)
        time.sleep(1.6)
    except Exception as e:
        print(f"    ! Tier 1: {str(e)[:60]}")

    # Karsilastirma alani ancak BANKA KARTINA tiklaninca aciliyor; PDF/Excel
    # dugmeleri o alanin ust barinda. Kartlar buton degil, tiklanabilir div.
    try:
        kartlar = s.locator("div.cursor-pointer.rounded-2xl")
        kartlar.first.wait_for(timeout=8000)
        for i in (0, 1):                # iki banka -> "Rekabet Analizi"
            k = kartlar.nth(i).bounding_box()
            if k:
                imlec(s, k["x"] - 200, k["y"] + 220,
                      k["x"] + k["width"] / 2, k["y"] + 60, sure=0.7)
            kartlar.nth(i).click()
            time.sleep(1.4)
    except Exception as e:
        print(f"    ! banka karti: {str(e)[:70]}")

    dibe_in(s, sure=3.6, bekle=1.6)     # rekabet analizinin tamami
    time.sleep(0.8)

    try:
        with s.expect_download(timeout=45000) as bekleyen:
            s.locator("button[title*='PDF']").first.click(timeout=10000)
        indirilen = bekleyen.value
        pdf = "/tmp/sahne/dashboard-raporu.pdf"
        indirilen.save_as(pdf)
        print(f"    PDF indirildi: {indirilen.suggested_filename}")
        time.sleep(2.2)                 # "hazirlaniyor" bildirimi ekranda kalsin
        pdf_goster(s, pdf, "Rekabet Analizi Raporu")
    except Exception as e:
        print(f"    ! PDF: {type(e).__name__}: {str(e)[:80]}")
        time.sleep(2.0)


def sahne_05_finansman(s):
    """00:36-00:44 — finansman, musteri -> calisan, ortalama oklari."""
    s.goto(f"{TABAN}/finansman", wait_until="networkidle", timeout=60000)
    time.sleep(2.2)
    mod(s, "Banka Çalışanı")            # oklar yalnizca bu modda cikiyor
    time.sleep(1.6)

    # Okun uzerinde bekle: native `title` ipucu videoya DUSMEZ (tarayici
    # cizer), ama okun kendi vurgu durumu gorunur. Ipucu metni kurguda
    # cagri kutusu olarak eklenmeli.
    try:
        ok = s.locator(".ortalama-ok").first
        ok.wait_for(timeout=8000)
        k = ok.bounding_box()
        if k:
            imlec(s, k["x"] - 340, k["y"] + 140, k["x"] + 7, k["y"] + 7, sure=1.0)
            time.sleep(2.4)
    except Exception as e:
        print(f"    ! ok: {str(e)[:70]}")
    kaydir(s, 560, sure=1.6)
    time.sleep(1.2)
    dibe_in(s, sure=5.0, bekle=1.8)     # 48 finansman urununun tamami


def sahne_06_katilim_chat(s):
    """00:44-00:54 — katilim hesabi -> FinAgent logosu -> chat."""
    s.goto(f"{TABAN}/katilim-hesap", wait_until="networkidle", timeout=60000)
    time.sleep(2.2)
    mod(s, "Banka Çalışanı")
    time.sleep(1.6)

    try:
        dugme = s.locator("img[alt='FinAgent']").first
        dugme.wait_for(timeout=8000)
        k = dugme.bounding_box()
        if k:
            imlec(s, k["x"] - 380, k["y"] + 180, k["x"] + 9, k["y"] + 9, sure=1.0)
        time.sleep(0.7)
        dugme.click()
    except Exception as e:
        print(f"    ! FinAgent logosu: {str(e)[:70]}")
    time.sleep(18.0)                    # otomatik analiz aksin
    kaydir(s, 420, sure=1.5)
    time.sleep(1.2)
    dibe_in(s, sure=2.6, bekle=1.8)     # cevabin sonu + kaynak satirlari


def sahne_07_chatbot_excel(s):
    """00:54-01:06 — iki soru; ikincisinde Excel ciktisi."""
    s.goto(f"{TABAN}/chat", wait_until="networkidle", timeout=60000)
    time.sleep(1.8)
    mod(s, "Banka Çalışanı")

    kutu = s.locator("input[type=text]").last
    yaz(s, kutu, "Albaraka mı daha avantajlı, Dünya Katılım mı?", 34)
    time.sleep(0.4)
    kutu.press("Enter")
    time.sleep(12.0)
    dibe_in(s, sure=2.4, bekle=1.8)     # 1. cevabin tamami

    # 2. soru — musteri modu + Excel
    s.goto(f"{TABAN}/chat", wait_until="networkidle", timeout=60000)
    time.sleep(1.6)
    mod(s, "Müşteri")
    kutu = s.locator("input[type=text]").last
    yaz(s, kutu, "kuveyttürk'ün konut finansmanı oranı nedir?", 34)
    kutu.press("Enter")
    time.sleep(12.0)
    dibe_in(s, sure=2.4, bekle=1.5)     # 2. cevabin tamami

    try:
        with s.expect_download(timeout=40000):
            s.get_by_text("Excel İndir", exact=False).first.click(timeout=10000)
        print("    Excel indirildi")
    except Exception as e:
        print(f"    ! Excel: {str(e)[:70]}")
    time.sleep(2.4)


def sahne_09_kapanis(s):
    """01:14-01:20 — karanlik tema ana sayfa."""
    s.add_init_script(
        "try { localStorage.setItem('nuxt-color-mode', 'dark'); } catch (e) {}")
    s.goto(f"{TABAN}/", wait_until="networkidle", timeout=60000)
    time.sleep(1.2)
    # color-mode ilk yuklemede cerezden okunmadiysa elle zorla
    s.evaluate("() => { document.documentElement.classList.add('dark');"
               " document.documentElement.style.colorScheme = 'dark'; }")
    time.sleep(2.6)                     # kahraman bolumu animasyonlari

    # Sayfanin gercek yuksekligini oku ve duraklari ORANLA yerlestir; sabit
    # piksel hedefleri icerik degisince anlamsizlasiyordu.
    dip = s.evaluate("""() => { const e = document.getElementById('main-scroller');
        return e ? e.scrollHeight - e.clientHeight
                 : document.body.scrollHeight - window.innerHeight; }""")
    print(f"    ana sayfa kaydirma payi: {dip} px")
    for oran in (0.12, 0.28, 0.46, 0.64, 0.82, 1.0):
        kaydir_guvenli(s, int(dip * oran), sure=1.4)
        time.sleep(0.85)
    time.sleep(2.0)
    # NOT: Basa donus denendi ve BIRAKILDI. Ana sayfada ScrollTrigger ana is
    # parcacigini tikaniyor; bu durumda KAYDIRMA_JS'teki setTimeout bekcisi de
    # gecikiyor ve tek bir cagri dakikalara yayilabiliyor (klip 36 sn yerine
    # 132 sn cikti). Sahne dipte bitiyor; kapanis karesini kurguda secmek
    # daha guvenli.


SAHNELER = [
    ("sahne_02_cikarim_kanit", sahne_02_cikarim_kanit, GENIS),
    ("sahne_03_dashboard_pdf", sahne_03_dashboard_pdf, GENIS),
    ("sahne_05_finansman",     sahne_05_finansman,     GENIS),
    ("sahne_06_katilim_chat",  sahne_06_katilim_chat,  GENIS),
    ("sahne_07_chatbot_excel", sahne_07_chatbot_excel, NORMAL),
    ("sahne_09_kapanis_index_dark", sahne_09_kapanis,  NORMAL),
]


if __name__ == "__main__":
    secili = sys.argv[1:] or None
    os.makedirs(CIKIS, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(args=BAYRAKLAR)
        for ad, islem, alan in SAHNELER:
            if secili and not any(x in ad for x in secili):
                continue
            print(f"[{ad}]")
            klip(b, ad, islem, alan)
        b.close()
    print("bitti")
