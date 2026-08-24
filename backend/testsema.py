# -*- coding: utf-8 -*-
"""Gerçek islenmis_kampanyalar şemasıyla alan eşleme testleri.

Buradaki sahte kayıtlar mongo_kontrol.py çıktısından BİREBİR alındı:
  • üst seviye banka_kodu YOK, kod genel_bilgi.banka_id içinde
  • finansman_detay.taksit düz bir sayı (9.0), alt belge değil
  • kar_payi_orani çoğu kayıtta null
  • genel_bilgi.hedef_kitle bazen liste, bazen düz metin
  • _id "kamp_<banka>_<hash>" biçiminde bir string
"""
import sys, os, types

_BURASI = os.path.dirname(os.path.abspath(__file__))
for _yol in (_BURASI, os.path.dirname(_BURASI)):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)


def sahte_modul(ad, **icerik):
    m = types.ModuleType(ad)
    for k, v in icerik.items():
        setattr(m, k, v)
    sys.modules[ad] = m
    return m


class _Any:
    def __init__(self, *a, **k): pass
    def __call__(self, *a, **k): return self
    def __getattr__(self, n): return _Any()


class _Logger:
    def __getattr__(self, n): return lambda *a, **k: None


sahte_modul("loguru", logger=_Logger())
sahte_modul("httpx", AsyncClient=_Any)
sahte_modul("fastapi", responses=None)
sahte_modul("fastapi.responses", StreamingResponse=_Any)
sahte_modul("langchain_core")
sahte_modul("langchain_core.embeddings", Embeddings=object)
sahte_modul("langchain_qdrant", QdrantVectorStore=_Any)
sahte_modul("qdrant_client", QdrantClient=_Any)
sahte_modul("qdrant_client.models", Filter=_Any, FieldCondition=_Any, MatchValue=_Any)
sahte_modul("pymongo", MongoClient=_Any)
sahte_modul("embedding_client", embed_batch=lambda *a, **k: [])
sahte_modul("chatbot.agents", suggestion_chain=_Any(), derin_dusunme_gerekli_mi=_Any(),
            hyde_belgesi_uret=_Any(), step_back_sorgu_uret=_Any(), coklu_sorgu_uret=_Any(),
            yapisal_analiz_parametreleri_uret=_Any(), supervisor_denetle=_Any(),
            gorsel_niyeti_sor=_Any(), persona_belirle=lambda *a, **k: "", TIMEOUT_ONERI=10)
sahte_modul("chatbot.redis_cache", get_cached_full_response=_Any(), set_cached_full_response=_Any())
sahte_modul("chatbot.tools", gercek_finansman_hesapla=lambda *a, **k: "")

from chatbot.generate_response import extract_campaign_data  # noqa: E402
from chatbot.intent import banka_kodu_coz  # noqa: E402

# --- mongo_kontrol.py çıktısındaki GERÇEK doküman -----------------------------
GERCEK = {
    "_id": "kamp_kuveytturk_6a873644c5af541599a67092",
    "finansman_detay": {
        "kar_payi_orani": 3.49, "vade_ay": None, "finansman_tutari": None,
        "taksit": 9.0, "tahsis_ucreti": None,
        "masraf_bilgi": "Sağlam Business Kart Avantajları...",
    },
    "genel_bilgi": {
        "banka_id": "kuveytturk",
        "temiz_kampanya_id": "6a873644c5af541599a67092",
        "kampanya_adi": "Sağlam Business Kart'tan Dev Kampanya",
        "kaynak_url": "https://www.kuveytturk.com.tr/kampanyalar/...",
        "baslangic_tarihi": "2026-05-18", "bitis_tarihi": "2026-12-31",
        "sure_gun": 227, "is_active": "aktif", "hedef_kitle": "segment",
        "kampanya_turu": "kart_kampanyasi", "alt_kategori": "kart_kampanyalari",
        "metin": "Kampanya Tarihleri 18.05.2026 - 31.12.2026...",
        "cekilis_tarihi": "2026-08-22T12:49:15.992417+00:00",
    },
    "mgm_detay": {"is_mgm": False, "kisi_basi_kazanc": None, "mgm_limit_tl": None},
    "promosyon_detay": {"odul_tip": None, "odul_tutari": None, "odul_metni": None,
                        "nakit_iade_yuzde": None, "puan_kazanc": None, "kazanc_metin": None},
}

# hedef_kitle'nin LİSTE geldiği varyant (raporda 'tum_musteriler' listesi görüldü)
LISTE_KITLE = {
    "_id": "kamp_albaraka_abc123",
    "finansman_detay": {"kar_payi_orani": None, "vade_ay": 12, "taksit": None},
    "genel_bilgi": {"banka_id": "albaraka", "kampanya_adi": "8 Taksit Fırsatıyla KASKO",
                    "hedef_kitle": ["tum_musteriler"], "kampanya_turu": "Genel",
                    "metin": "Albaraka Mobil üzerinden...", "bitis_tarihi": "2026-08-31"},
    "promosyon_detay": {"odul_tutari": 30000.0},
}

# banka_id'nin hiç olmadığı, sadece _id'den çözülebilen varyant
SADECE_ID = {
    "_id": "kamp_tom_katilim_zzz999",
    "finansman_detay": {}, "genel_bilgi": {"kampanya_adi": "X"}, "promosyon_detay": {},
}

hata = 0


def kontrol(ad, gercek, beklenen):
    global hata
    ok = gercek == beklenen
    hata += 0 if ok else 1
    print(f"{'✅' if ok else '❌'} {ad:<42} = {gercek!r}  (beklenen {beklenen!r})")


print("=== GERÇEK DOKÜMAN (Kuveyt Türk, taksit=9.0, vade_ay=null) ===")
c = extract_campaign_data(GERCEK)
kontrol("banka_kodu (genel_bilgi.banka_id'den)", c["banka_kodu"], "kuveytturk")
kontrol("banka (görünen ad)", c["banka"], "Kuveyt Türk")
kontrol("kar_payi", c["kar_payi"], 3.49)
kontrol("vade (taksit=9.0 düz sayıdan)", c["vade"], 9.0)
kontrol("kat (kampanya_turu)", c["kat"], "Kart Kampanyasi")
kontrol("kitle", c["kitle"], "Segment")
kontrol("bitis", c["bitis"], "2026-12-31")

print("\n=== LİSTE hedef_kitle + ödül dolu varyant (Albaraka) ===")
c2 = extract_campaign_data(LISTE_KITLE)
kontrol("banka_kodu", c2["banka_kodu"], "albaraka")
kontrol("banka", c2["banka"], "Albaraka Türk")
kontrol("odul", c2["odul"], 30000.0)
kontrol("vade (vade_ay öncelikli)", c2["vade"], 12.0)
kontrol("kitle (liste düzleştirildi)", c2["kitle"], "Tum Musteriler")

print("\n=== SADECE _id'den banka çözümü (tom_katilim) ===")
kontrol("banka_kodu_coz(_id öneki)", banka_kodu_coz(SADECE_ID), "tom_katilim")

print("\n=== 'sure_gun' AY sütununa sızmamalı (227 gün!) ===")
kontrol("vade (sure_gun kullanılmadı)", extract_campaign_data(SADECE_ID)["vade"], 0.0)

print("\n" + ("TÜM ŞEMA TESTLERİ GEÇTİ ✅" if hata == 0 else f"{hata} TEST BAŞARISIZ ❌"))
sys.exit(1 if hata else 0)