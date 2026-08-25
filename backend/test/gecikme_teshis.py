# -*- coding: utf-8 -*-
"""
gecikme_teshis.py — "Neden her istek 12 saniye?" sorusunun cevabı.

Ölçümde llm-large, llm-fast ve 2 kelimelik embedding'in HEPSİ ~12-14 saniye
sürdü. Farklı ağırlıktaki işlerin aynı süreyi alması, sürenin MODEL HESABINDAN
değil, her isteğin başındaki SABİT BİR BEDELDEN geldiğini gösterir.

Bu script o bedeli parçalara ayırır:
    1. DNS çözümlemesi          (yavaşsa: IPv6/AAAA zaman aşımı olabilir)
    2. TCP bağlantısı           (yavaşsa: ağ mesafesi/güvenlik duvarı)
    3. TLS el sıkışması         (yavaşsa: sertifika doğrulama/proxy)
    4. Yeni bağlantıyla istek   (her seferinde 1+2+3 yeniden ödenir)
    5. AYNI bağlantıyla istek   (keep-alive: 1+2+3 bir kez ödenir)

4 ile 5 arasındaki fark, bağlantı havuzu kullanarak kazanacağımız süredir.

    python gecikme_teshis.py
"""
import os
import socket
import ssl
import statistics
import sys
import time
from urllib.parse import urlparse

try:
    import httpx
except ImportError:
    raise SystemExit("httpx kurulu değil:  pip install httpx")

# .env'i evren_client'ın yükleyicisiyle oku
try:
    import backend.chatbot.evren_client as ev
except ModuleNotFoundError:
    try:
        from chatbot import evren_client as ev
    except ModuleNotFoundError:
        raise SystemExit("evren_client.py bulunamadı — bu dosyayı onun yanına koy.")


def olc(fn, tekrar=3):
    sureler = []
    for _ in range(tekrar):
        bas = time.perf_counter()
        try:
            fn()
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"
        sureler.append(time.perf_counter() - bas)
    return sureler, None


def yazdir(baslik, sureler, hata=None, esik=1.0):
    if hata:
        print(f"  {baslik:<34} ❌ {hata}")
        return
    ort = statistics.mean(sureler)
    isaret = "🐢" if ort > esik else "✅"
    tekil = "  ".join(f"{s:.2f}" for s in sureler)
    print(f"  {baslik:<34} {isaret} ort {ort:6.2f}sn   ({tekil})")


def main():
    parca = urlparse(ev.BASE_URL)
    host = parca.hostname
    port = parca.port or (443 if parca.scheme == "https" else 80)
    print("=" * 78)
    print(f"HEDEF: {host}:{port}   ({ev.BASE_URL})")
    print("=" * 78)

    # --- 1. DNS ---
    print("\n[1] DNS ÇÖZÜMLEMESİ")
    dns_varsayilan, hata = olc(lambda: socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP))
    yazdir("getaddrinfo (varsayılan)", dns_varsayilan, hata, esik=0.5)
    dns_ipv4, hata = olc(lambda: socket.getaddrinfo(host, port, family=socket.AF_INET,
                                                    proto=socket.IPPROTO_TCP))
    yazdir("getaddrinfo (sadece IPv4)", dns_ipv4, hata, esik=0.5)
    try:
        adresler = {a[4][0] for a in socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)}
        print(f"  {'çözümlenen adresler':<34} {sorted(adresler)}")
    except Exception as e:
        print(f"  çözümleme hatası: {e}")

    # --- 2. TCP ---
    print("\n[2] TCP BAĞLANTISI")
    def tcp():
        s = socket.create_connection((host, port), timeout=30)
        s.close()
    sureler, hata = olc(tcp)
    yazdir("connect", sureler, hata, esik=0.5)

    # --- 3. TLS ---
    print("\n[3] TLS EL SIKIŞMASI")
    ctx = ssl.create_default_context()
    def tls():
        with socket.create_connection((host, port), timeout=30) as ham:
            with ctx.wrap_socket(ham, server_hostname=host):
                pass
    sureler, hata = olc(tls)
    yazdir("connect + handshake", sureler, hata, esik=1.0)
    if hata and "CERTIFICATE_VERIFY_FAILED" in str(hata):
        print("       ℹ️  Bu adım Python'un ssl modülünün kök sertifika deposunu kullanır;")
        print("           httpx `certifi` kullandığı için UYGULAMA ETKİLENMEZ ([4]/[5]'e bak).")
        print("           Yani bu satırdaki hata bir engel değil, ölçüm aracının sınırı.")

    if not ev.hazir_mi():
        print("\n⚠️ EVREN_API_KEY yok — HTTP ölçümleri atlanıyor.")
        return 1

    basliklar = {"Authorization": f"Bearer {ev.API_KEY}"}

    # --- 4. HER İSTEKTE YENİ BAĞLANTI (mevcut davranış) ---
    print("\n[4] HTTP — HER İSTEKTE YENİ BAĞLANTI  (evren_client'ın şu anki hâli)")
    def yeni_baglanti():
        with httpx.Client(timeout=60) as c:
            r = c.get(f"{ev.BASE_URL}/models", headers=basliklar)
            r.raise_for_status()
    sureler_yeni, hata = olc(yeni_baglanti)
    yazdir("GET /models", sureler_yeni, hata, esik=2.0)

    # --- 5. AYNI BAĞLANTIYI YENİDEN KULLAN (keep-alive) ---
    print("\n[5] HTTP — TEK BAĞLANTI, YENİDEN KULLANIM  (bağlantı havuzu)")
    sureler_ayni = []
    hata2 = None
    try:
        with httpx.Client(timeout=60, limits=httpx.Limits(max_keepalive_connections=5)) as c:
            for i in range(4):
                bas = time.perf_counter()
                r = c.get(f"{ev.BASE_URL}/models", headers=basliklar)
                r.raise_for_status()
                sureler_ayni.append(time.perf_counter() - bas)
        print(f"  {'1. istek (bağlantı kuruluyor)':<34} {sureler_ayni[0]:.2f}sn")
        yazdir("2-4. istekler (hazır bağlantı)", sureler_ayni[1:], None, esik=1.0)
    except Exception as e:
        hata2 = f"{type(e).__name__}: {e}"
        print(f"  ❌ {hata2}")

    # --- 6. GERÇEK İŞ: aynı bağlantıda embedding ---
    print("\n[6] GERÇEK İŞ — tek bağlantıda 3 embedding çağrısı")
    try:
        with httpx.Client(timeout=120, limits=httpx.Limits(max_keepalive_connections=5)) as c:
            emb_sureler = []
            for i in range(3):
                bas = time.perf_counter()
                r = c.post(f"{ev.BASE_URL}/embeddings",
                           headers={**basliklar, "Content-Type": "application/json"},
                           json={"model": ev.EMBED_MODEL, "input": [f"deneme metni {i}"]})
                r.raise_for_status()
                emb_sureler.append(time.perf_counter() - bas)
        print(f"  {'1. çağrı':<34} {emb_sureler[0]:.2f}sn")
        yazdir("2-3. çağrı (hazır bağlantı)", emb_sureler[1:], None, esik=2.0)
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")

    # --- YORUM ---
    print("\n" + "=" * 78)
    print("YORUM")

    # 🛠️ ÖNEMLİ: Bu bölüm önce yalnızca [4] ile [5]'i kıyaslıyordu ve DNS'i hiç
    # hesaba katmıyordu. Oysa [1]-[3] adımları DNS önbelleğini ISITIYOR; sonraki
    # HTTP ölçümleri bu yüzden hızlı çıkıyor ve "bağlantı kurulumu suçlu değil"
    # gibi YANLIŞ bir sonuca varılıyordu. Artık DNS farkı ilk sırada değerlendiriliyor.
    if dns_varsayilan and dns_ipv4:
        v, i4 = statistics.mean(dns_varsayilan), statistics.mean(dns_ipv4)
        print(f"  DNS varsayılan : {v:.2f}sn   |   sadece IPv4: {i4:.2f}sn")
        if v - i4 > 1.0:
            print(f"  ➜ 🚨 ASIL SUÇLU BU: IPv6 (AAAA) sorgusu ~{v - i4:.0f} saniye zaman aşımına")
            print("       düşüyor, sonra IPv4'e geçiliyor. Her YENİ bağlantı bu bedeli öder.")
            print("       ÇÖZÜM (kodda uygulandı): evren_client soketi IPv4'e zorluyor")
            print("       (EVREN_IPV4=true -> local_address='0.0.0.0').")
            print("       Kalıcı sistem çözümü: DNS sunucusunu değiştirmek ya da")
            print("       hosts dosyasına IPv4 kaydı eklemek.")
        else:
            print("  ➜ DNS sorun değil.")

    if sureler_yeni and sureler_ayni and len(sureler_ayni) > 1:
        yeni_ort = statistics.mean(sureler_yeni)
        ayni_ort = statistics.mean(sureler_ayni[1:])
        kazanc = yeni_ort - ayni_ort
        print(f"\n  Yeni bağlantı  : {yeni_ort:.2f}sn/istek   (DNS önbelleği ISINMIŞ hâlde)")
        print(f"  Hazır bağlantı : {ayni_ort:.2f}sn/istek")
        if kazanc > 0.2:
            print(f"  ➜ Bağlantı havuzu istek başına ~{kazanc:.2f}sn kazandırır "
                  f"(evren_client'ta uygulandı).")
        print("\n  ⚠️ NOT: Bu iki ölçüm DNS önbelleği dolduktan SONRA yapıldı, yani")
        print("     gerçek 'ilk istek' maliyetini göstermez. Asıl fark yukarıdaki")
        print("     DNS satırındadır.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())