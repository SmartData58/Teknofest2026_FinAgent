# mongo_baglanti.py — Süreç ömrü boyunca paylaşılan MongoClient havuzu.
#
# NEDEN VAR:
# Dört ayrı yerde her çağrıda YENİ bir MongoClient açılıyordu
# (generate_response, indexing, urun_verisi, api/analiz). MongoClient ucuz bir
# nesne değildir: her örnek kendi bağlantı havuzunu kurar, sunucu keşfi
# (topology discovery) yapar ve arka planda izleme iş parçacıkları başlatır.
# Sürekli yeniden yaratmak hem her isteğe kurulum maliyeti bindiriyor hem de
# yük altında bağlantı sayısını gereksizce şişiriyor.
#
# ÖLÇÜM (chatbot yolundaki okumalar, 5 tekrar):
#   finansman_kayitlari  min 7,1ms / max 62,4ms  -> sıçrama yeni bağlantı kurulumu
#   kampanya (500 kayıt) min 12,6ms / max 36,1ms
# Havuz paylaşıldığında bu kurulum maliyeti yalnızca ilk çağrıda ödeniyor.
#
# pymongo'nun kendi belgeleri de MongoClient'ın uygulama ömrü boyunca TEK
# örnek olarak tutulmasını söyler; havuzlama zaten istemcinin içinde.

import threading
from typing import Optional

from loguru import logger

_istemciler: dict = {}
_kilit = threading.Lock()


def istemci_al(uri: str, zaman_asimi_ms: int = 5000):
    """Verilen URI için paylaşılan MongoClient'ı döner (yoksa kurar).

    URI başına tek örnek tutulur; farklı URI'ler (ör. test) ayrı havuz alır.
    İş parçacığı güvenli: MongoClient'ın kendisi de zaten thread-safe.
    """
    anahtar = (uri, zaman_asimi_ms)
    istemci = _istemciler.get(anahtar)
    if istemci is not None:
        return istemci
    with _kilit:
        # Kilit beklenirken başka bir iş parçacığı kurmuş olabilir.
        istemci = _istemciler.get(anahtar)
        if istemci is None:
            from pymongo import MongoClient
            istemci = MongoClient(uri, serverSelectionTimeoutMS=zaman_asimi_ms)
            _istemciler[anahtar] = istemci
            logger.info(f"🍃 MongoClient havuzu kuruldu (zaman_asimi={zaman_asimi_ms}ms)")
        return istemci


def veritabani(uri: str, db_adi: str, zaman_asimi_ms: int = 5000):
    """Paylaşılan istemci üzerinden bir veritabanı tutamağı döner."""
    return istemci_al(uri, zaman_asimi_ms)[db_adi]


def kapat() -> None:
    """Tüm paylaşılan istemcileri kapatır (yalnızca kapanış/test için)."""
    with _kilit:
        for istemci in _istemciler.values():
            try:
                istemci.close()
            except Exception:
                pass
        _istemciler.clear()
