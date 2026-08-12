# =============================================================================
# prompts.py — LLM Cevap Şablonları ve Deterministik Metinler
# =============================================================================

RAG_CEVAP_PROMPTU = """Sen FinAgent'sın: Türkiye'deki katılım bankalarının \
kampanyalarını bilen bir asistansın.

KURALLAR:
- SADECE aşağıdaki kampanya bilgilerine dayanarak cevap ver.
- Bilgi kampanya metinlerinde yoksa açıkça "elimdeki kampanya verilerinde bu \
bilgi yok" de. ASLA tahmin etme, sayı uydurma.
- Hangi bankanın hangi kampanyasından bahsettiğini belirt.
- Kısa ve doğal Türkçe ile cevapla (2-5 cümle).
- Sorular yatırım tavsiyesi isterse: kampanya bilgisi verdiğini, tavsiye \
veremeyeceğini söyle.

KAMPANYA BİLGİLERİ:
{baglam}

{gecmis}SORU: {soru}

CEVAP:"""

URUN_KURALLARI = """- Bağlamdaki bazı kayıtlar KAMPANYA değil, bankanın \
SÜREKLİ ÜRÜNÜdür ("Kayıt türü" satırına bak). Ürünlerden bahsederken \
"kampanya" ASLA deme, "ürün" de.
- Ürünün bitiş tarihi, ödülü ya da ilan edilmiş kâr payı oranı YOKTUR; \
bunları uydurma. Ürün için yalnız "Doğrulanmış bilgiler" satırındaki \
değerleri kullan.
"""

SELAMLAMA_CEVABI = (
    "Merhaba! Ben FinAgent — katılım bankalarının güncel kampanyalarını "
    "takip eden asistan. Bana örneğin şunları sorabilirsiniz:\n"
    "- *Kâr payı oranı en düşük kampanya hangisi?*\n"
    "- *Kuveyt Türk'ün kampanyaları neler?*\n"
    "- *Emekliler için kampanya var mı?*"
)

VERI_YOK_CEVABI = (
    "Bu soruya elimdeki kampanya verileriyle cevap veremiyorum — sorunuz "
    "izlediğim katılım bankası kampanyalarıyla eşleşmedi. Banka adı veya "
    "kampanya konusu (finansman, taksit, ödül...) belirterek tekrar "
    "deneyebilirsiniz."
)

TAVSIYE_CEVABI = (
    "Yatırım tavsiyesi veremem — ben yalnızca bankaların **ilan ettiği "
    "kampanya bilgilerini** aktarabilirim; hangi bankayı seçeceğiniz sizin "
    "kararınızdır.\n\nYine de karar verirken işinize yarayabilecek "
    "karşılaştırmaları sorabilirsiniz:\n"
    "- *En düşük kâr payı oranı hangi bankada?*\n"
    "- *En yüksek ödül hangi kampanyada?*\n"
    "- *En düşük tahsis ücreti hangi kampanyada?*"
)

TUR_ADLARI = {
    "ihtiyac_finansmani": "ihtiyaç finansmanı",
    "konut_finansmani": "konut finansmanı",
    "tasit_finansmani": "taşıt finansmanı",
}

def rag_promptu(soru: str, belgeler: list[str], gecmis=None, urun_var: bool = False) -> str:
    baglam = "\n\n".join(
        f"[{i}] {belge[:1400]}" for i, belge in enumerate(belgeler, start=1)
    )
    gecmis_blok = ""
    if gecmis:
        satirlar = [
            f"{'Kullanıcı' if m.rol == 'user' else 'Asistan'}: {m.icerik[:300]}"
            for m in list(gecmis)[-4:]
        ]
        gecmis_blok = (
            "ÖNCEKİ KONUŞMA (SORU bu konuşmanın devamıdır; \"peki\", \"onun\" "
            "gibi göndermeleri buna göre yorumla):\n" + "\n".join(satirlar) + "\n\n"
        )
    sablon = RAG_CEVAP_PROMPTU
    if urun_var:
        sablon = sablon.replace(
            "\nKAMPANYA BİLGİLERİ:",
            f"{URUN_KURALLARI}\nKAMPANYA VE ÜRÜN BİLGİLERİ:"
        )
    return sablon.format(baglam=baglam, soru=soru, gecmis=gecmis_blok)

def tur_yok_cevabi(tur: str, banka_adi: str | None = None, olan_bankalar: list[str] | None = None) -> str:
    ad = TUR_ADLARI.get(tur, tur)
    if banka_adi and olan_bankalar:
        return (
            f"{banka_adi} için kayıtlı bir {ad} kampanyası ya da ürünü bulunmuyor. "
            f"Ancak şu bankalarda var: {', '.join(olan_bankalar)}. İsterseniz onları sorabilirsiniz."
        )
    kapsam = f"{banka_adi} sayfalarında" if banka_adi else "İzlediğim katılım bankalarının kampanya ve ürün sayfalarında"
    return (
        f"{kapsam} bir {ad} kaydı bulamadım — olmayan bir kampanya ya da ürün hakkında "
        f"tahmin yürütmüyorum. **Kampanyalar** sayfasından tüm güncel kampanyalara bakabilirsiniz."
    )

def urun_kapsam_notu(tur: str) -> str:
    ad = TUR_ADLARI.get(tur, tur)
    return (
        f"*Şu anda yürürlükte bir {ad} **kampanyası** yok; aşağıdaki bilgi bankanın "
        f"sürekli **ürün** sayfasından geliyor (süreli bir fırsat değil, oranlar başvuruda belirlenir).*"
    )