# -*- coding: utf-8 -*-
"""
bagimlilik_denetimi.py — "requirements.txt'te ne var, kod NEYİ kullanıyor?"

NEDEN VAR
---------
Yarışma API'sine geçtikten sonra backend artık YEREL ÇIKARIM YAPMIYOR: embedding,
rerank ve LLM uzak sunucuda. Ama requirements.txt hâlâ o dönemden kalma ağır
paketleri istiyor — en başta 526 MB'lık `torch`. Build tam da onu indirirken
patladı (hash uyuşmazlığı: yavaş bağlantıda dosya bozuk indi).

Silmeden önce KANIT lazım: gerçekten hiçbir modül import etmiyor mu? Bu script
kaynak ağacını tarayıp her paketin GERÇEKTEN import edilip edilmediğini söyler.
Tahminle paket silmek, üretimde patlayan bir imaj üretir.

KULLANIM
    python bagimlilik_denetimi.py                 # bulunduğun dizini tara
    python bagimlilik_denetimi.py --kok ./backend
    python bagimlilik_denetimi.py --req backend/requirements.txt
"""
import argparse
import ast
import os
import re
import sys
from collections import defaultdict

# PyPI adı -> import edildiğinde görünen modül adları
PAKET_MODULLERI = {
    "torch": {"torch"},
    "accelerate": {"accelerate"},
    "transformers": {"transformers"},
    "sentence-transformers": {"sentence_transformers"},
    "psycopg2-binary": {"psycopg2"},
    "llama-index-core": {"llama_index"},
    "llama-index-vector-stores-qdrant": {"llama_index"},
    "pandas": {"pandas"},
    "openpyxl": {"openpyxl"},
    "PyMuPDF": {"fitz", "pymupdf"},
    "python-docx": {"docx"},
    "psutil": {"psutil"},
    "qdrant-client": {"qdrant_client"},
    "langchain": {"langchain"},
    "langchain-core": {"langchain_core"},
    "langchain-openai": {"langchain_openai"},
    "langchain-qdrant": {"langchain_qdrant"},
    "langchain-community": {"langchain_community"},
    "langchain-ollama": {"langchain_ollama"},
    "httpx": {"httpx"},
    "requests": {"requests"},
    "pymongo": {"pymongo"},
    "redis": {"redis"},
    "python-dotenv": {"dotenv"},
    "python-multipart": {"multipart"},
    "loguru": {"loguru"},
    "fastapi": {"fastapi"},
    "uvicorn": {"uvicorn"},
    "pillow": {"PIL"},
    "numpy": {"numpy"},
    "scipy": {"scipy"},
    "easyocr": {"easyocr"},
    "paddleocr": {"paddleocr"},
    "pytesseract": {"pytesseract"},
    "rapidocr-onnxruntime": {"rapidocr_onnxruntime"},
    "onnxruntime": {"onnxruntime"},
    "reportlab": {"reportlab"},
}

# Bunlar büyük; gereksizse imajdan ciddi yer kazandırır
AGIR = {
    "torch": "~2,5 GB (CUDA'sız bile ~800 MB)",
    "accelerate": "torch'u ZORUNLU kılar",
    "transformers": "~500 MB + model indirmeleri",
    "sentence-transformers": "torch + transformers çeker",
    "easyocr": "torch çeker",
    "paddleocr": "paddlepaddle çeker",
    "onnxruntime": "~200 MB",
    "scipy": "~90 MB",
    "llama-index-core": "~120 MB (kod langchain kullanıyorsa gereksiz)",
    "psycopg2-binary": "compose'da Postgres yoksa gereksiz",
}

ATLA_DIZIN = {".git", "__pycache__", "node_modules", ".venv", "venv",
              "env", ".mypy_cache", ".pytest_cache", "test_belgeleri"}


def modulleri_topla(kok: str):
    """Kaynak ağacındaki TÜM top-level import adlarını (dosyalarıyla) toplar."""
    bulunan = defaultdict(set)
    okunamayan = []
    for dizin, altlar, dosyalar in os.walk(kok):
        altlar[:] = [d for d in altlar if d not in ATLA_DIZIN]
        for d in dosyalar:
            if not d.endswith(".py"):
                continue
            yol = os.path.join(dizin, d)
            try:
                agac = ast.parse(open(yol, encoding="utf-8-sig").read(), filename=yol)
            except Exception as e:
                okunamayan.append((yol, f"{type(e).__name__}: {e}"))
                continue
            gorece = os.path.relpath(yol, kok)
            for dugum in ast.walk(agac):
                if isinstance(dugum, ast.Import):
                    for a in dugum.names:
                        bulunan[a.name.split(".")[0]].add(gorece)
                elif isinstance(dugum, ast.ImportFrom):
                    if dugum.level == 0 and dugum.module:
                        bulunan[dugum.module.split(".")[0]].add(gorece)
    return bulunan, okunamayan


def req_oku(yol: str):
    """requirements.txt'i (paket_adi, ham_satir) listesine çevirir."""
    if not os.path.isfile(yol):
        return []
    satirlar = []
    for ham in open(yol, encoding="utf-8-sig"):
        t = ham.strip()
        if not t or t.startswith("#") or t.startswith("-"):
            continue
        ad = re.split(r"[<>=!~\[; ]", t, 1)[0].strip()
        if ad:
            satirlar.append((ad, t))
    return satirlar


def main():
    ap = argparse.ArgumentParser(description="requirements ↔ gerçek import denetimi")
    ap.add_argument("--kok", default=".", help="taranacak kaynak kökü")
    ap.add_argument("--req", default="", help="requirements.txt yolu")
    args = ap.parse_args()

    kok = os.path.abspath(args.kok)
    req_yolu = args.req or os.path.join(kok, "requirements.txt")

    print("=" * 78)
    print(f"KAYNAK : {kok}")
    print(f"REQ    : {req_yolu}  {'' if os.path.isfile(req_yolu) else '(BULUNAMADI)'}")
    print("=" * 78)

    bulunan, okunamayan = modulleri_topla(kok)
    print(f"\n{len(bulunan)} farklı top-level modül import ediliyor.")
    if okunamayan:
        print(f"⚠️ {len(okunamayan)} dosya ayrıştırılamadı:")
        for y, h in okunamayan[:5]:
            print(f"   {y}: {h}")

    reqler = req_oku(req_yolu)
    if not reqler:
        print("\n⚠️ requirements.txt okunamadı — yalnızca ağır paket taraması yapılıyor.\n")

    # --- 1. requirements'ta OLUP hiç import edilmeyenler ---
    if reqler:
        print("\n" + "-" * 78)
        print("[1] requirements.txt'TE VAR ama KODDA HİÇ IMPORT EDİLMİYOR")
        print("-" * 78)
        aday = []
        for ad, ham in reqler:
            modul_adlari = PAKET_MODULLERI.get(ad) or PAKET_MODULLERI.get(ad.lower()) \
                or {ad.replace("-", "_").lower()}
            if not (modul_adlari & set(bulunan)):
                aday.append((ad, ham))
        if not aday:
            print("  (yok — hepsi kullanılıyor)")
        for ad, ham in aday:
            not_ = AGIR.get(ad, "")
            print(f"  • {ham:<34} {'⚠️ ' + not_ if not_ else ''}")
        if aday:
            print("\n  ⚠️ 'import edilmiyor' HER ZAMAN 'gereksiz' demek DEĞİLDİR:")
            print("     bazı paketler eklenti/sürücü olarak dolaylı çekilir")
            print("     (ör. uvicorn'un http parser'ı, bir kütüphanenin isteğe bağlı")
            print("     bağımlılığı). Silmeden önce imajı kurup /health'i açtır.")

    # --- 2. Kodda kullanılıp requirements'ta OLMAYANLAR (asıl tehlike) ---
    if reqler:
        print("\n" + "-" * 78)
        print("[2] KODDA KULLANILIYOR ama requirements.txt'TE YOK  ← ÇÖKME SEBEBİ")
        print("-" * 78)
        req_modulleri = set()
        for ad, _ in reqler:
            req_modulleri |= (PAKET_MODULLERI.get(ad) or
                              {ad.replace("-", "_").lower()})
        eksik = []
        for pypi_ad, moduller in PAKET_MODULLERI.items():
            kullanilan = moduller & set(bulunan)
            if kullanilan and not (moduller & req_modulleri):
                ornek = sorted(bulunan[sorted(kullanilan)[0]])[:3]
                eksik.append((pypi_ad, ornek))
        if not eksik:
            print("  (yok)")
        for pypi_ad, ornek in eksik:
            print(f"  ❌ {pypi_ad:<28} kullanan: {', '.join(ornek)}")

    # --- 3. Ağır paketler gerçekten kullanılıyor mu? ---
    print("\n" + "-" * 78)
    print("[3] AĞIR PAKETLER — gerçekten import ediliyor mu?")
    print("-" * 78)
    for pypi_ad, neden in AGIR.items():
        moduller = PAKET_MODULLERI.get(pypi_ad, set())
        kullanan = set()
        for m in moduller:
            kullanan |= bulunan.get(m, set())
        if kullanan:
            print(f"  ✅ KULLANILIYOR  {pypi_ad:<26} ({neden})")
            for y in sorted(kullanan)[:4]:
                print(f"       └─ {y}")
        else:
            print(f"  🗑️ import YOK     {pypi_ad:<26} ({neden})")

    print("\n" + "=" * 78)
    print("Yorum: [2] boş DEĞİLSE backend import hatasıyla çöker — önce onu düzelt.")
    print("       [3]'te '🗑️ import YOK' olanlar imajı küçültme adaylarıdır.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())