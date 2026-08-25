# =============================================================================
# kullanim_raporu.py — TAKIMIN KÜMÜLATİF KULLANIMI (/key/info)
#
# NEDEN AYRI BİR ARAÇ:
#   /health içindeki "kullanim" bloğu YALNIZCA çalışan backend sürecinin
#   ölçümüdür — konteyner yeniden başlayınca sıfırlanır. Yarışma boyunca
#   harcanan GERÇEK TOPLAM sunucu tarafında tutulur ve GET /key/info ile
#   okunur. Bu script onu sorgular.
#
# KULLANIM:
#   python kullanim_raporu.py              # tablo görünümü
#   python kullanim_raporu.py --ham        # sunucunun döndürdüğü ham JSON
#   python kullanim_raporu.py --yerel      # backend /health sayacını da ekle
#
# Docker içinden (anahtar zaten /app/.env'de):
#   docker compose ... exec backend python kullanim_raporu.py
# =============================================================================
import argparse
import asyncio
import json
import sys

try:
    import evren_client as ec
except ModuleNotFoundError:
    try:
        from chatbot import evren_client as ec   # type: ignore
    except ModuleNotFoundError:
        sys.exit(
            "evren_client bulunamadı.\n"
            "Bu scripti evren_client.py ile AYNI klasörden (ya da backend "
            "konteynerinin içinden) çalıştırın."
        )


# --- Sunucu yanıtındaki alan adları kesin bilinmediği için esnek okuma -------
# Dokümantasyon "istek sayısı, token kullanımı ve harcama verileri" diyor ama
# tam şemayı vermiyor. Bu yüzden bilinen adları arıyoruz; bulunamayan alanlar
# ham JSON'da zaten görünür (--ham). Uydurma yapmıyoruz: bulamazsak "-" yazıp
# ham çıktıya yönlendiriyoruz.
_ADAYLAR = {
    "istek": ("request_count", "requests", "total_requests", "istek_sayisi", "n_requests"),
    "girdi_token": ("prompt_tokens", "input_tokens", "total_prompt_tokens"),
    "cikti_token": ("completion_tokens", "output_tokens", "total_completion_tokens"),
    "toplam_token": ("total_tokens", "tokens", "token_count", "toplam_token"),
    "harcama": ("spend", "cost", "total_cost", "usage_cost", "harcama"),
    "limit": ("max_budget", "budget", "limit", "quota", "hard_limit"),
    "kalan": ("remaining", "remaining_budget", "kalan"),
    "anahtar_adi": ("key_alias", "alias", "name", "key_name", "team", "team_name"),
}


def _derin_ara(veri, adlar):
    """Sözlükte (iç içe olsa da) verilen adlardan ilkini bulur."""
    if isinstance(veri, dict):
        for ad in adlar:
            if ad in veri and veri[ad] is not None:
                return veri[ad]
        for v in veri.values():
            if isinstance(v, (dict, list)):
                bulunan = _derin_ara(v, adlar)
                if bulunan is not None:
                    return bulunan
    elif isinstance(veri, list):
        for v in veri:
            bulunan = _derin_ara(v, adlar)
            if bulunan is not None:
                return bulunan
    return None


def _sayi(x):
    if x is None:
        return "-"
    if isinstance(x, float):
        return f"{x:,.4f}".rstrip("0").rstrip(".")
    if isinstance(x, int):
        return f"{x:,}".replace(",", ".")
    return str(x)


def _satir(etiket, deger):
    print(f"  {etiket:<28} {_sayi(deger)}")


async def main():
    ap = argparse.ArgumentParser(description="Takımın kümülatif Evren API kullanımı")
    ap.add_argument("--ham", action="store_true", help="ham JSON yanıtı yazdır")
    ap.add_argument("--yerel", action="store_true",
                    help="bu süreçteki yerel sayacı da göster (yalnızca backend içinde anlamlı)")
    a = ap.parse_args()

    print("=" * 62)
    print("  EVREN API — TAKIM KULLANIM RAPORU (/key/info)")
    print("=" * 62)

    if not ec.hazir_mi():
        sys.exit(
            "\n❌ EVREN_API_KEY okunamadı.\n"
            f"   Aranan .env: {getattr(ec, 'ENV_DOSYASI', 'bilinmiyor')}\n"
            "   Bu scripti .env'in bulunduğu klasörden çalıştırın."
        )

    try:
        veri = await ec.anahtar_bilgisi()
    except Exception as e:
        sys.exit(f"\n❌ /key/info okunamadı: {e}")
    finally:
        await ec.kapat()

    if a.ham:
        print(json.dumps(veri, indent=2, ensure_ascii=False))
        return

    okunan = {k: _derin_ara(veri, adlar) for k, adlar in _ADAYLAR.items()}

    ad = okunan["anahtar_adi"]
    if ad:
        print(f"\n  Anahtar: {ad}")

    print("\n  KÜMÜLATİF (yarışma başından beri, sunucu kaydı)")
    print("  " + "-" * 58)
    _satir("Toplam istek", okunan["istek"])
    _satir("Girdi (prompt) token", okunan["girdi_token"])
    _satir("Çıktı (completion) token", okunan["cikti_token"])
    _satir("TOPLAM token", okunan["toplam_token"])
    if okunan["harcama"] is not None:
        _satir("Harcama", okunan["harcama"])
    if okunan["limit"] is not None:
        _satir("Limit / bütçe", okunan["limit"])
    if okunan["kalan"] is not None:
        _satir("Kalan", okunan["kalan"])

    bulunamayan = [k for k, v in okunan.items() if v is None and k != "anahtar_adi"]
    if bulunamayan:
        print(
            f"\n  ℹ️  Şu alanlar sunucu yanıtında bu adlarla bulunamadı: "
            f"{', '.join(bulunamayan)}\n"
            "     Alan adları farklı olabilir — tam yanıt için: "
            "python kullanim_raporu.py --ham"
        )

    if a.yerel:
        print("\n  BU SÜREÇTEKİ ÖLÇÜM (backend restart'ında sıfırlanır)")
        print("  " + "-" * 58)
        y = ec.kullanim_ozeti()
        g = y["genel"]
        _satir("Çağrı", g["cagri"])
        _satir("Hata", g["hata"])
        _satir("Toplam token", g["toplam_token"])
        _satir("Toplam süre (sn)", g["sure_toplam_sn"])
        for tur, s in y["tur_bazinda"].items():
            print(f"\n    [{tur}] {s['cagri']} çağrı | {_sayi(s['toplam_token'])} token "
                  f"| ort {s['sure_ortalama_sn']}sn | p90 {s['sure_p90_sn']}sn")
            if s["ilk_token_p50_sn"] is not None:
                print(f"       ilk token (p50): {s['ilk_token_p50_sn']}sn")

    print()


if __name__ == "__main__":
    asyncio.run(main())