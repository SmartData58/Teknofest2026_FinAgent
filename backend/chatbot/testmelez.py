# -*- coding: utf-8 -*-
"""Melez (regex + LLM) görsel-niyet katmanı testleri.

İki şeyi doğrular:
  1. KAPI: hangi sorularda LLM'e soruluyor, hangilerinde boşuna sorulmuyor.
  2. AYRIŞTIRMA: ajan farklı/bozuk çıktı biçimlerinde ne döndürüyor, hata ve
     timeout durumunda regex kararı korunuyor mu.
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
import types, asyncio, json

from chatbot.intent import niyet_bul, llm_gorsel_sorulmali, gorsel_limiti, Mesaj

# ----------------------------------------------------------------------------
# 1. KAPI TESTLERİ — LLM'e sorulmalı mı?
# ----------------------------------------------------------------------------
KAPI = [
    # (soru, dil, beklenen_regex_gorsel, LLM'e_sorulmali_mi, not)
    # NOT: "döküm" ve "hepsini" zaten TABLO_ISTEGI kalıbında — onlarda LLM'e
    # sorulmaz (regex hâlâ hızlı yol). Buradakiler gerçekten kalıp DIŞI ifadeler.
    ("bunları yan yana koyabilir misin", "tr", None, True, "kalıp dışı liste isteği -> LLM'e sor"),
    ("bir arada görmek istiyorum", "tr", None, True, "kalıp dışı -> LLM'e sor"),
    ("bunların dökümünü çıkarabilir misin", "tr", "tablo", False, "'döküm' kalıpta var -> regex hallediyor"),
    ("can you break these down for me", "en", None, True, "EN kalıp dışı -> LLM'e sor"),
    ("kampanyaları listele", "tr", "tablo", False, "regex zaten karar verdi -> sorma"),
    ("grafik çizer misin", "tr", "grafik", False, "regex zaten karar verdi -> sorma"),
    ("Bu kampanyaya kimler başvurabilir?", "tr", None, False, "yorum sorusu -> sorma"),
    ("Neden bu oran bu kadar düşük?", "tr", None, False, "yorum sorusu -> sorma"),
    ("pythonda bu hesabı nasıl yazarım", "tr", None, False, "kod sorusu -> sorma"),
    ("merhaba", "tr", None, False, "statik -> sorma"),
    ("100.000 TL 12 ay taksit hesapla", "tr", None, False, "hesaplama -> sorma"),
]

hata = 0
print("=== KAPI: LLM'e sorulmalı mı? ===")
for soru, dil, bek_gorsel, bek_sor, aciklama in KAPI:
    n = niyet_bul(soru, (), dil=dil)
    sor = llm_gorsel_sorulmali(n)
    ok = (n.gorsel == bek_gorsel) and (sor == bek_sor)
    hata += 0 if ok else 1
    print(f"{'✅' if ok else '❌'} {soru[:52]!r}")
    print(f"      regex={n.gorsel} (beklenen {bek_gorsel}) | LLM'e sor={sor} (beklenen {bek_sor}) | niyet={n.tur}")
    print(f"      → {aciklama}")

# ----------------------------------------------------------------------------
# 2. AJAN TESTLERİ — sahte LLM çıktılarıyla
# ----------------------------------------------------------------------------
# agents.py'yi gerçek Ollama olmadan yükleyebilmek için ChatOllama'yı sahteliyoruz.
class _SahteLLM:
    def __init__(self, *a, **k): pass
    def __or__(self, other): return self


def sahte_modul(ad, **icerik):
    m = types.ModuleType(ad)
    for k, v in icerik.items():
        setattr(m, k, v)
    sys.modules[ad] = m
    return m


class _Logger:
    def __getattr__(self, n): return lambda *a, **k: None


sahte_modul("loguru", logger=_Logger())
# 🚀 Yarışma API'sine geçişten sonra agents.py ChatOllama yerine ChatOpenAI
# kullanıyor; testin gerçek pakete ihtiyacı yok, sahtesi yeterli.
sahte_modul("langchain_ollama", ChatOllama=_SahteLLM)
sahte_modul("langchain_openai", ChatOpenAI=_SahteLLM)


class _SahtePrompt:
    def __init__(self, *a, **k): pass
    def __or__(self, other): return self


sahte_modul("langchain_core")
sahte_modul("langchain_core.prompts", PromptTemplate=_SahtePrompt)
sahte_modul("langchain_core.output_parsers", StrOutputParser=_SahtePrompt)

from chatbot import agents  # noqa: E402


class _SahteZincir:
    """ainvoke() çağrıldığında önceden verilen ham metni (ya da hatayı) döner."""
    def __init__(self, cikti): self.cikti = cikti

    async def ainvoke(self, _):
        if isinstance(self.cikti, Exception):
            raise self.cikti
        if self.cikti == "__yavas__":
            await asyncio.sleep(5)
            return '{"gorsel": "tablo"}'
        return self.cikti


AJAN = [
    ('{"gorsel": "tablo"}', "tablo", "temiz JSON"),
    ('```json\n{"gorsel": "grafik"}\n```', "grafik", "markdown çitli JSON"),
    # 🛠️ Artık "yok" (bilinçli karar) ile None (cevap alınamadı) AYRI dönüyor:
    # çağıran taraf ikisine farklı davranıyor — "yok" -> hiçbir şey çizme,
    # None -> temkinli varsayılan (3 satırlık özet tablo).
    ('{"gorsel": "yok"}', "yok", "'yok' -> bilinçli karar, görsel yok"),
    ('Karar: tablo olmalı', "tablo", "bozuk JSON, düz metinden kurtarma"),
    ('{"gorsel": "table"}', "tablo", "İngilizce değer"),
    ('kjhsdf', None, "anlamsız çıktı -> None (karar yok, varsayılana düşülür)"),
    (RuntimeError("Ollama kapalı"), None, "ajan patladı -> regex kararı korunur"),
    ("__yavas__", None, "timeout -> regex kararı korunur"),
]

print("\n=== AJAN: çıktı ayrıştırma ve hata dayanıklılığı ===")


async def ajan_testleri():
    global hata
    for cikti, beklenen, aciklama in AJAN:
        agents.gorsel_niyet_chain = _SahteZincir(cikti)
        timeout = 0.2 if cikti == "__yavas__" else 10
        sonuc = await agents.gorsel_niyeti_sor("bunların dökümünü çıkar", timeout=timeout)
        ok = sonuc == beklenen
        hata += 0 if ok else 1
        etiket = cikti if isinstance(cikti, str) else repr(cikti)
        print(f"{'✅' if ok else '❌'} {etiket[:42]!r} -> {sonuc} (beklenen {beklenen})  # {aciklama}")

    # Anahtar kapalıyken hiç çağrı yapılmamalı
    agents.GORSEL_LLM_FALLBACK_AKTIF = False
    agents.gorsel_niyet_chain = _SahteZincir('{"gorsel": "grafik"}')
    sonuc = await agents.gorsel_niyeti_sor("dökümünü çıkar")
    ok = sonuc is None
    hata += 0 if ok else 1
    print(f"{'✅' if ok else '❌'} GORSEL_LLM_FALLBACK=false -> {sonuc} (beklenen None)  # anahtar kapalı, çağrı yok")
    agents.GORSEL_LLM_FALLBACK_AKTIF = True


asyncio.run(ajan_testleri())

# ----------------------------------------------------------------------------
# 3. LİMİT — melez karar geldiğinde 3 satıra kırpılmamalı
# ----------------------------------------------------------------------------
print("\n=== LİMİT: melez karar açık istek sayılır ===")
soru = "bunları yan yana koyabilir misin"
regex_limit = gorsel_limiti(soru, "tablo", "analist", acik_istek_zorla=False)
melez_limit = gorsel_limiti(soru, "tablo", "analist", acik_istek_zorla=True)
ok = regex_limit == 3 and melez_limit == 50
hata += 0 if ok else 1
print(f"{'✅' if ok else '❌'} regex bayrağı olmadan={regex_limit} (3), melez bayrağıyla={melez_limit} (50)")

print("\n" + ("TÜM MELEZ TESTLERİ GEÇTİ ✅" if hata == 0 else f"{hata} TEST BAŞARISIZ ❌"))
sys.exit(1 if hata else 0)