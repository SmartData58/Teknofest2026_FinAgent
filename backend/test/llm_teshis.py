# -*- coding: utf-8 -*-
"""
llm_teshis.py — "LLM neden cevap üretmiyor?" sorusunu KANITLA cevaplar.

DURUM
-----
Ekranda 77 satırlık tablo var, altında ya "elimdeki verilerde bilgi bulamadım"
ya da "yapay zekâ yorumu eklenemedi" yazıyor. İkisi de bizim yedek metnimiz;
yani model ya HİÇ İÇERİK ÜRETMEDİ ya da çağrı HATA VERDİ. Backend logu tek
başına hangisi olduğunu söylemiyordu.

Bu script sohbet yığınını hiç çalıştırmadan doğrudan yarışma API'sine gider ve
sorunu dört kademede daraltır:

    1. Bağlantı + anahtar        -> /models
    2. KISA prompt, akışlı        -> temel çalışıyor mu
    3. KISA prompt, akışsız       -> yedek yol çalışıyor mu
    4. GERÇEK BOYUTLU prompt      -> asıl şüpheli: uzun bağlam
       (77 kampanyalık db_context'i taklit eder)

Her adımda süre, üretilen karakter, finish_reason ve varsa muhakeme
(reasoning) uzunluğu raporlanır.

KULLANIM
    python llm_teshis.py
    python llm_teshis.py --kampanya 150      # daha da uzun bağlam dene
    python llm_teshis.py --max-tokens 8192
"""
import argparse
import asyncio
import json
import os
import sys
import time


def _paketi_bul():
    burasi = os.path.dirname(os.path.abspath(__file__))
    for aday in (burasi, os.getcwd(), os.path.dirname(burasi)):
        if os.path.isfile(os.path.join(aday, "evren_client.py")) or \
           os.path.isfile(os.path.join(aday, "chatbot", "evren_client.py")):
            if aday not in sys.path:
                sys.path.insert(0, aday)
            return
    raise SystemExit("evren_client.py bulunamadı — bu dosyayı onun yanına koy.")


_paketi_bul()
try:
    import evren_client as ev
except ModuleNotFoundError:
    from chatbot import evren_client as ev

import httpx


def sahte_baglam(adet: int) -> str:
    """generate_response'un ürettiği db_context'e benzer bir metin kurar.

    Amaç uzunluğu taklit etmek: gerçek bağlamda her kampanya banka adı,
    kampanya adı, oran, vade ve ödül içeriyor.
    """
    bankalar = ["Kuveyt Türk", "Türkiye Finans", "Albaraka Türk",
                "Hayat Finans", "TOM Katılım", "Emlak Katılım"]
    satirlar = [f"(Kapsam: sistemdeki 346 kampanyanın {adet} tanesinde 'Ödül' verisi kayıtlı.)"]
    for i in range(adet):
        b = bankalar[i % len(bankalar)]
        satirlar.append(
            f"{i+1}. Banka: {b} | Kampanya: Örnek Kampanya {i+1} — "
            f"Müşterilere Özel Avantajlı Paket ve Ek Ödül Fırsatı | "
            f"Kâr Payı: %{(i % 30) / 10:.2f} | Vade: {6 + (i % 30)} ay | "
            f"Ödül: {1000 + i * 137} TL"
        )
    return "\n".join(satirlar)


def olc_ham(mesajlar, max_tokens, akis: bool, timeout: float, dusunme: bool = True):
    """httpx ile DOĞRUDAN çağrı — evren_client'ın ayrıştırmasını atlar.

    Neden ham: evren_client'ın kendi çıkarıcısı bir alanı kaçırıyorsa, onun
    üstünden ölçmek aynı körlüğü tekrarlar. Burada sunucunun DÖNDÜĞÜ HER ŞEYİ
    görüyoruz.
    """
    govde = {
        "model": ev.MODEL_ANA,
        "messages": mesajlar,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "stream": akis,
    }
    if not dusunme:
        # Qwen/vLLM'in muhakemeyi kapatma alanı. Standart OpenAI alanı DEĞİL;
        # sunucu desteklemezse 400 döner ve bunu raporda görürüz.
        govde["chat_template_kwargs"] = {"enable_thinking": False}
    basliklar = {"Authorization": f"Bearer {ev.API_KEY}",
                 "Content-Type": "application/json"}
    ulasim = httpx.HTTPTransport(local_address="0.0.0.0") if ev.IPV4_ZORLA else None

    icerik, muhakeme, bitis = "", "", None
    ilk_token = None
    bas = time.perf_counter()

    with httpx.Client(timeout=timeout, transport=ulasim) as c:
        if not akis:
            r = c.post(f"{ev.BASE_URL}/chat/completions", json=govde, headers=basliklar)
            sure = time.perf_counter() - bas
            if r.status_code >= 400:
                return {"hata": f"HTTP {r.status_code}: {r.text[:400]}", "sure": sure}
            veri = r.json()
            secim = (veri.get("choices") or [{}])[0]
            mesaj = secim.get("message") or {}
            icerik = mesaj.get("content")
            if isinstance(icerik, list):
                icerik = "".join(p.get("text", "") for p in icerik if isinstance(p, dict))
            icerik = icerik or ""
            muhakeme = mesaj.get("reasoning_content") or ""
            bitis = secim.get("finish_reason")
            return {"icerik": icerik, "muhakeme": muhakeme, "bitis": bitis,
                    "sure": sure, "ilk_token": sure,
                    "kullanim": veri.get("usage"), "ham_anahtarlar": sorted(mesaj.keys())}

        with c.stream("POST", f"{ev.BASE_URL}/chat/completions",
                      json=govde, headers=basliklar) as cevap:
            if cevap.status_code >= 400:
                ham = cevap.read()
                return {"hata": f"HTTP {cevap.status_code}: {ham[:400].decode('utf-8','replace')}",
                        "sure": time.perf_counter() - bas}
            gorulen_alanlar = set()
            for satir in cevap.iter_lines():
                if not satir:
                    continue
                if satir.startswith("data:"):
                    satir = satir[5:].strip()
                if satir == "[DONE]":
                    break
                try:
                    p = json.loads(satir)
                except json.JSONDecodeError:
                    continue
                for s in p.get("choices") or []:
                    d = s.get("delta") or {}
                    gorulen_alanlar |= set(d.keys())
                    parca = d.get("content")
                    if isinstance(parca, list):
                        parca = "".join(x.get("text", "") for x in parca if isinstance(x, dict))
                    if parca:
                        if ilk_token is None:
                            ilk_token = time.perf_counter() - bas
                        icerik += parca
                    if d.get("reasoning_content"):
                        muhakeme += d["reasoning_content"]
                    if s.get("finish_reason"):
                        bitis = s["finish_reason"]
    return {"icerik": icerik, "muhakeme": muhakeme, "bitis": bitis,
            "sure": time.perf_counter() - bas, "ilk_token": ilk_token,
            "delta_alanlari": sorted(gorulen_alanlar)}


def raporla(baslik, s):
    print(f"\n  ── {baslik}")
    if s.get("hata"):
        print(f"     ❌ {s['hata']}")
        print(f"     süre {s['sure']:.1f}sn")
        return False
    icerik = s.get("icerik") or ""
    muhakeme = s.get("muhakeme") or ""
    print(f"     süre          : {s['sure']:.1f}sn"
          + (f"   (ilk token {s['ilk_token']:.1f}sn)" if s.get("ilk_token") else ""))
    print(f"     içerik        : {len(icerik):,} karakter")
    if muhakeme:
        print(f"     muhakeme      : {len(muhakeme):,} karakter  ⚠️ (kullanıcıya gitmez)")
    print(f"     finish_reason : {s.get('bitis')!r}")
    if s.get("delta_alanlari"):
        print(f"     delta alanları: {s['delta_alanlari']}")
    if s.get("ham_anahtarlar"):
        print(f"     message alanları: {s['ham_anahtarlar']}")
    if s.get("kullanim"):
        print(f"     usage         : {s['kullanim']}")
    if icerik:
        print(f"     ilk 120 krktr : {icerik[:120]!r}")
        return True

    print("     🚨 İÇERİK BOŞ — kullanıcının gördüğü yedek mesajın sebebi bu.")
    if s.get("bitis") == "length":
        print("        ➜ TEŞHİS: token bütçesi CEVAP YAZILMADAN doldu.")
        print("          Muhakeme yapan modellerde düşünme adımları da bütçeden düşer.")
        print("          ÇÖZÜM: .env -> EVREN_MAX_TOKENS değerini yükselt.")
    elif muhakeme:
        print("        ➜ TEŞHİS: model sadece 'düşündü', görünür cevap yazmadı.")
        print("          ÇÖZÜM: max_tokens yükselt ya da prompt'u kısalt.")
    else:
        print("        ➜ Sebep belirsiz; yukarıdaki delta/message alanlarına bak:")
        print("          içerik beklenmedik bir alandaysa evren_client'ın")
        print("          _metni_cikar fonksiyonuna o alan eklenmeli.")
    return False


def main():
    ap = argparse.ArgumentParser(description="LLM boş cevap teşhisi")
    ap.add_argument("--kampanya", type=int, default=77,
                    help="sahte bağlamdaki kampanya sayısı (ekranda 77 vardı)")
    ap.add_argument("--max-tokens", type=int, default=0,
                    help="0 = .env'deki EVREN_MAX_TOKENS")
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()

    mt = args.max_tokens or ev.MAX_TOKENS

    print("=" * 78)
    print("LLM TEŞHİS")
    print("=" * 78)
    print(f"  BASE_URL     : {ev.BASE_URL}")
    print(f"  model        : {ev.MODEL_ANA}")
    print(f"  max_tokens   : {mt}")
    print(f"  IPv4 zorlama : {ev.IPV4_ZORLA}")
    print(f"  .env         : {ev.ENV_DOSYASI}")
    # 🛠️ Eskiden burada sadece "EVREN_API_KEY yok" yazıyordu ve HANGİ .env'e
    # bakıldığı belli olmuyordu. Gerçek kurulumda iki .env vardı (repo kökü ve
    # backend/) ve script yanlış olanı yüklüyordu. Artık hepsi listeleniyor.
    adaylar = getattr(ev, "ENV_ADAYLARI", [])
    if len(adaylar) > 1 or not ev.hazir_mi():
        print("\n  bulunan .env dosyaları:")
        for yol, anahtar_var in adaylar:
            isaret = "🔑 anahtar VAR" if anahtar_var else "⚠️ anahtar YOK"
            secili = "  ← YÜKLENEN" if yol == ev.ENV_DOSYASI else ""
            print(f"    {isaret}  {yol}{secili}")
        if not adaylar:
            print("    (hiç .env bulunamadı)")

    if not ev.hazir_mi():
        print("\n❌ EVREN_API_KEY okunamadı.")
        print("   Olası sebepler:")
        print("     • Anahtar BAŞKA bir .env dosyasında (yukarıdaki listeye bak)")
        print("     • Satır bozuk: 'EVREN_API_KEY=sk-...' biçiminde, '=' etrafında")
        print("       boşluk olmadan ve tırnak içinde OLMADAN yazılmalı")
        print("     • Değer boş bırakılmış")
        print("   İki .env varsa gereksiz olanı sil ya da anahtarı doğru olana taşı;")
        print("   evren_client artık içinde anahtar OLAN dosyayı tercih eder ama")
        print("   diğer ayarlar (EVREN_MAX_TOKENS vb.) da o dosyadan okunur.")
        return 1

    # --- 1 ---
    print("\n[1] BAĞLANTI VE ANAHTAR")
    try:
        ulasim = httpx.HTTPTransport(local_address="0.0.0.0") if ev.IPV4_ZORLA else None
        with httpx.Client(timeout=30, transport=ulasim) as c:
            r = c.get(f"{ev.BASE_URL}/models",
                      headers={"Authorization": f"Bearer {ev.API_KEY}"})
        print(f"  HTTP {r.status_code}")
        if r.status_code >= 400:
            print(f"  ❌ {r.text[:300]}")
            return 1
        adlar = [m.get("id") for m in (r.json().get("data") or [])]
        print(f"  modeller: {adlar}")
        if ev.MODEL_ANA not in adlar:
            print(f"  ⚠️ '{ev.MODEL_ANA}' listede YOK — EVREN_MODEL yanlış olabilir.")
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return 1

    kisa = [{"role": "user", "content": "Merhaba, tek cümleyle kendini tanıt."}]

    # --- 2 & 3 ---
    print("\n[2] KISA PROMPT")
    a = raporla("akışlı (stream=True)", olc_ham(kisa, mt, True, args.timeout))
    b = raporla("akışsız (stream=False)", olc_ham(kisa, mt, False, args.timeout))

    if not (a or b):
        print("\n🛑 KISA promptta bile içerik yok. Sorun bağlam uzunluğu DEĞİL;")
        print("   model/parametre düzeyinde. Yukarıdaki finish_reason'a bak.")
        return 1

    # --- 4 ---
    print(f"\n[3] GERÇEK BOYUTLU PROMPT ({args.kampanya} kampanya)")
    baglam = sahte_baglam(args.kampanya)
    uzun = [{"role": "user", "content":
             "Aşağıdaki kampanya verilerini analiz et ve en dikkat çekici 3 kampanyayı "
             "Türkçe olarak yorumla.\n\n<<<VERİ>>>\n" + baglam + "\n<<<VERİ_SONU>>>"}]
    print(f"  prompt uzunluğu: {len(uzun[0]['content']):,} karakter "
          f"(~{len(uzun[0]['content']) // 3:,} token tahmini)")
    c_ok = raporla("akışlı (stream=True)", olc_ham(uzun, mt, True, args.timeout))

    # --- 5: muhakemeyi kapatma denemesi ---
    print("\n[4] MUHAKEMEYİ KAPATMA DENEMESİ (chat_template_kwargs)")
    print("    Ölçümde muhakeme, bütçenin ~%85'ini ve gecikmenin çoğunu yiyor.")
    print("    Kapatılabiliyorsa hem ilk token süresi hem token kullanımı düşer.")
    kapali = olc_ham(uzun, mt, True, args.timeout, dusunme=False)
    d_ok = raporla("akışlı + düşünme KAPALI", kapali)
    if kapali.get("hata"):
        print("     ➜ Sunucu bu alanı desteklemiyor. Sorun değil: evren_client")
        print("       400 alınca alanı atıp isteği tekrarlar, sistem bozulmaz.")
        print("       .env'de EVREN_DUSUNME=acik bırak.")
    elif d_ok:
        print("\n     KARŞILAŞTIRMA (uzun prompt):")
        print(f"       muhakeme  : {len(kapali.get('muhakeme') or ''):,} karakter "
              f"(0'a yakınsa kapatma İŞE YARADI)")
        print(f"       ilk token : {kapali.get('ilk_token')}sn")
        print("     ➜ Belirgin kazanç varsa .env'de EVREN_DUSUNME=kapali yap.")
        print("       ⚠️ Ama önce cevap KALİTESİNİ kontrol et: muhakeme, çok")
        print("       bankalı kıyaslama gibi sorularda gerçekten yardımcı olabilir.")
        print("       Ölçmek için: test_buyuk.py'yi iki ayarla da çalıştır.")

    if (a or b) and not c_ok:
        print("\n🎯 TEŞHİS NETLEŞTİ: kısa prompt çalışıyor, UZUN prompt çalışmıyor.")
        print("   Sebep neredeyse kesin olarak token bütçesi ya da zaman aşımı.")
        print("   Sırayla dene:")
        print(f"     python llm_teshis.py --max-tokens {mt * 2}")
        print("   Düzelirse .env'de EVREN_MAX_TOKENS'ı o değere çek.")
        print("   Düzelmezse bağlamı kısalt: LLM'e giden kampanya sayısını sınırla")
        print("   (tablo yine 77 satır gösterebilir; modele hepsini vermek şart değil).")

    print("\n" + "=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())