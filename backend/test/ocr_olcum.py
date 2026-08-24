# -*- coding: utf-8 -*-
"""
ocr_olcum.py — "OCR'ı CPU'ya düşürsek ne kaybederiz?" sorusunun ölçülmüş cevabı.

NEDEN VAR
---------
torch'un CUDA'lı wheel'i ~2,5 GB ve build'i patlatan 526 MB'lık indirme onun.
CPU-only wheel ~200 MB. Ama OCR GPU kullanıyorsa CPU'ya düşmek onu yavaşlatır.
"Ne kadar yavaşlatır?" sorusunun cevabı tahminle verilemez: modele, sayfa
sayısına ve CPU'ya göre 2 kat da olabilir 30 kat da.

Bu script backend KONTEYNERİNİN İÇİNDE çalışır ve şunları söyler:
  1. CUDA gerçekten görünüyor mu (görünmüyorsa zaten CPU'dasın, tartışma biter)
  2. Aynı belge GPU'da ve CPU'da kaç saniye sürüyor
  3. Kullanıcı bekleme süresi açısından kabul edilebilir mi

KULLANIM (konteyner içinde)
    docker compose exec backend python ocr_olcum.py --dosya /app/temp/ornek.pdf
    docker compose exec backend python ocr_olcum.py --dosya /app/temp/ornek.pdf --sadece-durum
"""
import argparse
import asyncio
import os
import sys
import time


def durum_yazdir():
    print("=" * 78)
    print("TORCH / CUDA DURUMU")
    print("=" * 78)
    try:
        import torch
    except ImportError:
        print("  ❌ torch kurulu değil. OCR yığını çalışmıyor demektir.")
        return None

    print(f"  torch sürümü      : {torch.__version__}")
    # '+cpu' soneki CPU-only wheel'in işaretidir; '+cu121' gibi bir sonek
    # CUDA'lı wheel demektir. Sonek yoksa varsayılan (CUDA'lı) wheel'dir.
    if "+cpu" in torch.__version__:
        print("  wheel türü        : CPU-only (~200 MB)")
    elif "+cu" in torch.__version__:
        print(f"  wheel türü        : CUDA'lı (~2,5 GB)")
    else:
        print("  wheel türü        : varsayılan (büyük olasılıkla CUDA'lı)")

    var = torch.cuda.is_available()
    print(f"  cuda.is_available : {var}")
    if var:
        try:
            print(f"  GPU               : {torch.cuda.get_device_name(0)}")
            top = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"  VRAM              : {top:.1f} GB")
        except Exception as e:
            print(f"  GPU bilgisi okunamadı: {e}")
    else:
        print("\n  ⚠️ CUDA GÖRÜNMÜYOR. İki anlama gelebilir:")
        print("     a) CPU-only torch kurulu  -> zaten CPU'dasın")
        print("     b) CUDA'lı torch kurulu ama konteynere GPU verilmemiş")
        print("        -> 2,5 GB'lık paketi taşıyıp hiç kullanmıyorsun.")
        print("        Düzeltme:  -f docker-compose.nvidia.yml ekle")
        print("        (bu durum SESSİZDİR: OCR hata vermez, sadece yavaşlar)")
    return var


async def _ayristir(yol):
    """Uygulamanın kendi ayrıştırıcısını çağırır — gerçek yolu ölçmek için."""
    from document_processor.parser import parse_document
    import inspect
    if "progress_callback" in inspect.signature(parse_document).parameters:
        async def _cb(m):
            return None
        return await parse_document(yol, progress_callback=_cb)
    return await parse_document(yol)


def olc(yol, etiket):
    bas = time.perf_counter()
    try:
        metin = asyncio.run(_ayristir(yol))
    except Exception as e:
        print(f"  {etiket:<22} ❌ {type(e).__name__}: {e}")
        return None
    sure = time.perf_counter() - bas
    print(f"  {etiket:<22} {sure:7.2f}sn   ({len(metin or ''):,} karakter)")
    return sure


def main():
    ap = argparse.ArgumentParser(description="OCR GPU/CPU karşılaştırması")
    ap.add_argument("--dosya", default="", help="ölçülecek PDF/görsel")
    ap.add_argument("--sadece-durum", action="store_true")
    args = ap.parse_args()

    cuda_var = durum_yazdir()
    if args.sadece_durum:
        return 0

    if not args.dosya:
        print("\n⚠️ --dosya verilmedi, ölçüm yapılmadı.")
        print("   Örnek:  docker compose exec backend python ocr_olcum.py --dosya /app/temp/ornek.pdf")
        return 0
    if not os.path.isfile(args.dosya):
        print(f"\n❌ Dosya yok: {args.dosya}")
        return 1

    boyut = os.path.getsize(args.dosya) / 1024
    print("\n" + "=" * 78)
    print(f"ÖLÇÜM: {args.dosya}  ({boyut:.0f} KB)")
    print("=" * 78)

    gpu_sure = cpu_sure = None

    if cuda_var:
        print("\n[1] GPU (mevcut ayar)")
        olc(args.dosya, "ısınma (sayılmaz)")   # ilk çağrı modeli yükler
        gpu_sure = olc(args.dosya, "GPU")

        # CUDA_VISIBLE_DEVICES ile GPU'yu gizleyip aynı kodu CPU'da çalıştır.
        # ⚠️ torch bir kez içe aktarıldıktan SONRA bu değişken çoğu kurulumda
        # etkisizdir; bu yüzden CPU ölçümü AYRI BİR PROCESS'te yapılmalı.
        print("\n[2] CPU (aynı belge, GPU gizlenerek — ayrı process)")
        import subprocess
        ortam = dict(os.environ, CUDA_VISIBLE_DEVICES="")
        r = subprocess.run(
            [sys.executable, __file__, "--dosya", args.dosya],
            env=ortam, capture_output=True, text=True,
        )
        for satir in r.stdout.splitlines():
            if "CPU" in satir or "sn" in satir:
                print("  " + satir.strip())
    else:
        print("\n[1] CPU (CUDA zaten yok)")
        olc(args.dosya, "ısınma (sayılmaz)")
        cpu_sure = olc(args.dosya, "CPU")

    print("\n" + "=" * 78)
    print("KARAR REHBERİ")
    print("=" * 78)
    print("  Ölçtüğün süre, kullanıcının dosya yükledikten sonra BEKLEYECEĞİ süredir")
    print("  (LLM cevabı bunun ÜSTÜNE biner).")
    print()
    print("  < 5sn    -> CPU'ya geç. 2,3 GB imaj tasarrufu buna değer.")
    print("  5-15sn   -> sınırda. Jüri demosunda PDF yükleyecek misin? Hayırsa CPU.")
    print("  > 15sn   -> GPU'da kal (-f docker-compose.nvidia.yml) ya da OCR'ı")
    print("              yarışma API'sinin görsel modeline taşımayı düşün.")
    print()
    print("  ⚠️ Üçüncü seçenek: OCR'ı hiç kullanmamak. Görseller (png/jpg) ZATEN")
    print("     OCR'ı atlayıp doğrudan modele gidiyor. Sadece PDF/docx yerel")
    print("     OCR'a düşüyor. Demo senaryonda PDF yoksa bu tartışma boşa.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())