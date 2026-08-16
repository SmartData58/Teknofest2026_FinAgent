# =============================================================================
# llm_extractor.py — LLM Çıkarımı ve NoSQL Doküman Dönüştürücü
# =============================================================================
import json
import logging
import os
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ValidationError
from datetime import date, datetime, timezone

logger = logging.getLogger(__name__)

GEÇERLİ_YÖNTEMLER = {"regex", "llm", "rule_based", "manual"}

# LLM Katmanında Sorulabilir Alan Şemaları Tanımı
TUM_ALAN_SEMALARI = {
    "baslangic_tarihi": {"birim": "gün", "aciklama": "YYYY-MM-DD kampanya başlangıcı"},
    "bitis_tarihi": {"birim": "gün", "aciklama": "YYYY-MM-DD kampanya bitişi"},
    "hedef_kitle": {"birim": "metin", "aciklama": "örn: ['yeni_musteriler']"},
    "kampanya_turu": {"birim": "metin", "aciklama": "Finansman, Kredi Kartı, MGM vb."},
    "alt_kategori": {"birim": "metin", "aciklama": "Konut, Taşıt, İhtiyaç vb."},
    "kar_paylasim_orani": {"birim": "yüzde", "aciklama": "Kâr payı oranı (%)"},
    "finansman_kar_orani": {"birim": "yüzde", "aciklama": "Finansman kâr oranı (%)"},
    "max_vade_ay": {"birim": "ay", "aciklama": "Azami vade/taksit sayısı"},
    "min_fin_tutar": {"birim": "TL", "aciklama": "Asgari finansman tutarı"},
    "max_fin_tutar": {"birim": "TL", "aciklama": "Azami finansman tutarı"},
    "tahsis_ucreti": {"birim": "TL", "aciklama": "Tahsis ücreti masrafı"},
    "masraf_tl": {"birim": "TL", "aciklama": "Toplam masraf tutarı"},
    "masraf_bilgi": {"birim": "metin", "aciklama": "Masraf açıklama metni"},
    "masraf_bilgisi": {"birim": "metin", "aciklama": "Detaylı masraf bilgisi"},
    "odul_tutari_tl": {"birim": "TL", "aciklama": "Kazanılan ödül/bonus tutarı"},
    "odul_metni": {"birim": "metin", "aciklama": "Ödül detay açıklaması"},
    "cashback_orani": {"birim": "yüzde", "aciklama": "Nakit iade oranı (%)"},
    "indirim_orani_yuzde": {"birim": "yüzde", "aciklama": "İndirim oranı (%)"},
    "puan_kazanc": {"birim": "TL", "aciklama": "Puan/mil kazancı"},
    "min_harcama_tl": {"birim": "TL", "aciklama": "Minimum harcama şartı"},
    "kazanc_metin": {"birim": "metin", "aciklama": "Kazanç metni açıklaması"},
    "kisi_basi_kazanc": {"birim": "TL", "aciklama": "MGM kişi başı kazanç"},
    "mgm_limit_tl": {"birim": "TL", "aciklama": "MGM toplam limit"}
}


class AlanBulgusuLLM(BaseModel):
    deger: Optional[Union[str, float, int, List[str]]] = Field(default=None)
    ham_metin: Optional[str] = Field(default=None)
    birim: str = Field(default="metin")
    guven: float = Field(default=0.85, ge=0.0, le=1.0)
    kanit_metni: Optional[str] = Field(default=None)
    baslangic_konum: Optional[int] = Field(default=None)
    bitis_konum: Optional[int] = Field(default=None)
    yontem: str = Field(default="llm")


class LLMExtractionResult(BaseModel):
    baslangic_tarihi: Optional[AlanBulgusuLLM] = Field(default=None)
    bitis_tarihi: Optional[AlanBulgusuLLM] = Field(default=None)
    hedef_kitle: Optional[AlanBulgusuLLM] = Field(default=None)
    kampanya_turu: Optional[AlanBulgusuLLM] = Field(default=None)
    alt_kategori: Optional[AlanBulgusuLLM] = Field(default=None)

    kar_paylasim_orani: Optional[AlanBulgusuLLM] = Field(default=None)
    finansman_kar_orani: Optional[AlanBulgusuLLM] = Field(default=None)
    max_vade_ay: Optional[AlanBulgusuLLM] = Field(default=None)
    min_fin_tutar: Optional[AlanBulgusuLLM] = Field(default=None)
    max_fin_tutar: Optional[AlanBulgusuLLM] = Field(default=None)
    tahsis_ucreti: Optional[AlanBulgusuLLM] = Field(default=None)
    masraf_tl: Optional[AlanBulgusuLLM] = Field(default=None)
    masraf_bilgi: Optional[AlanBulgusuLLM] = Field(default=None)
    masraf_bilgisi: Optional[AlanBulgusuLLM] = Field(default=None)

    odul_tutari_tl: Optional[AlanBulgusuLLM] = Field(default=None)
    odul_metni: Optional[AlanBulgusuLLM] = Field(default=None)
    cashback_orani: Optional[AlanBulgusuLLM] = Field(default=None)
    indirim_orani_yuzde: Optional[AlanBulgusuLLM] = Field(default=None)
    puan_kazanc: Optional[AlanBulgusuLLM] = Field(default=None)
    min_harcama_tl: Optional[AlanBulgusuLLM] = Field(default=None)
    kazanc_metin: Optional[AlanBulgusuLLM] = Field(default=None)

    kisi_basi_kazanc: Optional[AlanBulgusuLLM] = Field(default=None)
    mgm_limit_tl: Optional[AlanBulgusuLLM] = Field(default=None)


def llm_hazir() -> bool:
    """Ollama/LLM servis durumunu simüle eder/kontrol eder."""
    return True


def llm_ile_cikar(metin: str, hedef_alanlar: List[str]) -> Dict[str, Any]:
    """Eksik alanlar için LLM çağrısını gerçekleştirir."""
    extractor = LLMExtractor()
    return extractor.extract_campaign_details(metin, hedef_alanlar=hedef_alanlar)


class LLMExtractor:
    def __init__(self, llm_client=None):
        self.client = llm_client

    def extract_campaign_details(self, text: str, kampanya_adi: str = "", hedef_alanlar: Optional[List[str]] = None) -> Dict[str, Any]:
        if not text:
            return {}

        prompt = f"Kampanya Adı: {kampanya_adi}\nAranacak Alanlar: {hedef_alanlar}\nKampanya Detayı:\n{text}"

        try:
            raw_json = self._mock_or_call_llm(prompt)
            validated_data = LLMExtractionResult.model_validate(raw_json)
            
            bulgular = {}
            for field_name, field_value in validated_data.model_dump(exclude_none=True).items():
                if hedef_alanlar and field_name not in hedef_alanlar:
                    continue
                if field_value and field_value.get("deger") is not None:
                    bulgular[field_name] = field_value

            return bulgular

        except ValidationError as ve:
            logger.error(f"LLM Çıktısı Pydantic şemasına uymadı: {ve}")
            return {}
        except Exception as e:
            logger.error(f"LLM Extraction hatası: {e}")
            return {}

    def _mock_or_call_llm(self, prompt: str) -> dict:
        return {}


# -----------------------------------------------------------------------------
# DÖNÜŞTÜRÜCÜ VE YARDIMCI METOTLAR
# -----------------------------------------------------------------------------
ALAN_TAKMA_ADLARI = {
    "kar_payi_orani": "kar_paylasim_orani",
    "indirim_orani": "indirim_orani_yuzde",
    "odul_miktari": "odul_tutari_tl",
    "vade_ay": "max_vade_ay",
    "azami_vade_ay": "max_vade_ay",
    "finansman_tutari": "max_fin_tutar",
    "azami_finansman_orani": "kar_paylasim_orani",
    "masraf_muafiyet_tutari": "masraf_tl",
    "tahsis_ucreti_orani": "tahsis_ucreti"
}


def _get_val(bulgular: dict, key: str, default: Any = None) -> Any:
    """Bulgular sözlüğünden takma ad duyarlı biçimde 'deger' çeker."""
    hedef_key = ALAN_TAKMA_ADLARI.get(key, key)
    item = bulgular.get(hedef_key) or bulgular.get(key)
    
    if isinstance(item, dict):
        return item.get("deger", default)
    elif hasattr(item, "deger"):
        return item.deger
    return item if item is not None else default


def process_and_build_documents(doc: dict, bulgular: dict):
    def _safe_float(val):
        try: return float(val) if val is not None else None
        except: return None

    def _safe_int(val):
        try: return int(val) if val is not None else None
        except: return None
        

    def _fix_date(val):
        """datetime.date nesnelerini ISO string'e (veya datetime.datetime'a) dönüştürür."""
        if isinstance(val, date) and not isinstance(val, datetime):
            return val.isoformat()  # MongoDB'de string ("2026-08-31") saklamak için
            # BSON Date olarak saklamak isterseniz üstteki satır yerine bunu kullanın:
            # return datetime.combine(val, datetime.min.time()).replace(tzinfo=timezone.utc)
        return val

    banka_kodu = doc.get("banka_kodu", "genel")
    raw_id = str(doc["_id"])

    structured_doc = {
        "_id": f"kamp_{banka_kodu}_{raw_id}",
        "genel_bilgi": {
            "banka_id": banka_kodu,
            "temiz_kampanya_id": raw_id,
            "kampanya_adi": doc.get("kampanya_adi"),
            "kaynak_url": doc.get("url"),
            "baslangic_tarihi": _fix_date(_get_val(bulgular, "baslangic_tarihi")),
            "bitis_tarihi": _fix_date(_get_val(bulgular, "bitis_tarihi")),
            "sure_gun": doc.get("sure_gun"),
            "is_active": "aktif",
            "hedef_kitle": _get_val(bulgular, "hedef_kitle", ["tum_musteriler"]),
            "kampanya_turu": _get_val(bulgular, "kampanya_turu"),
            "alt_kategori": _get_val(bulgular, "alt_kategori")
        },
        "finansman_detay": {
            "k_kar_paylasım_orani": _safe_float(_get_val(bulgular, "kar_paylasim_orani")),
            "k_vade_ay": _safe_int(_get_val(bulgular, "max_vade_ay")),
            "k_finansman_tutari": _safe_float(_get_val(bulgular, "max_fin_tutar")),
            "taksit": _get_val(bulgular, "taksit_sayisi", _get_val(bulgular, "max_vade_ay")),
            "hesaplanan_kar_tl": doc.get("hesaplanan_kar_tl"),
            "k_tahsis_ucreti": _get_val(bulgular, "tahsis_ucreti"),
            "k_masraf_bilgi": _get_val(bulgular, "masraf_bilgi", "Tahsis ücreti belirtilmemiştir.")
        },
        "promosyon_detay": {
            "odul_tutari_tl": _safe_float(_get_val(bulgular, "odul_tutari_tl")),
            "odul_metni": _get_val(bulgular, "odul_metni"),
            "nakit_iade_yuzde": _safe_float(_get_val(bulgular, "cashback_orani")),
            "indirim_orani_yuzde": _safe_float(_get_val(bulgular, "indirim_orani_yuzde")),
            "puan_kazanc": _safe_float(_get_val(bulgular, "puan_kazanc")),
            "min_harcama_tl": _safe_float(_get_val(bulgular, "min_harcama_tl")),
            "kazanc_metin": _get_val(bulgular, "kazanc_metin")
        },
        "mgm_detay": {
            "kisi_basi_kazanc": _get_val(bulgular, "kisi_basi_kazanc"),
            "mgm_limit_tl": _get_val(bulgular, "mgm_limit_tl")
        }
    }

    finansman_doc = {
        "_id": f"fin_{banka_kodu}_{raw_id}",
        "banka_id": banka_kodu,
        "alt_kategori": _get_val(bulgular, "alt_kategori"),
        "hedef_kitle": _get_val(bulgular, "hedef_kitle", ["tum_musteriler"]),
        "sfinansman_kar_orani": _safe_float(_get_val(bulgular, "finansman_kar_orani", _get_val(bulgular, "kar_paylasim_orani"))),
        "maks_vade_ay": _safe_int(_get_val(bulgular, "max_vade_ay")),
        "min_finansman_tutari": _safe_float(_get_val(bulgular, "min_fin_tutar")),
        "maks_finansman_tutari": _safe_float(_get_val(bulgular, "max_fin_tutar")),
        "standart_masraf_tutari": _safe_float(_get_val(bulgular, "masraf_tl")),
        "standart_masraf_bilgisi": _get_val(bulgular, "masraf_bilgisi", _get_val(bulgular, "masraf_bilgi")),
        "durum": "aktif",
        "olusturma_tarihi": datetime.now(timezone.utc).isoformat()
    }

    kanit_dokumanlari = []
    for alan_adi, bulgu_obj in bulgular.items():
        std_alan_adi = ALAN_TAKMA_ADLARI.get(alan_adi, alan_adi)
        kanit = _kanit_dokumani_hazirla(doc, std_alan_adi, bulgu_obj)
        if kanit:
            kanit_dokumanlari.append(kanit)

    return structured_doc, finansman_doc, kanit_dokumanlari


def _kanit_dokumani_hazirla(doc: dict, alan_adi: str, bulgu_obj) -> dict | None:
    if bulgu_obj is None:
        return None

    if hasattr(bulgu_obj, "deger"):
        norm_deger = bulgu_obj.deger
        ham_değer = getattr(bulgu_obj, "ham_metin", None) or getattr(bulgu_obj, "ham", str(norm_deger))
        unit_val = getattr(bulgu_obj, "birim", "metin")
        metot = getattr(bulgu_obj, "yontem", "regex")
        guven_score = getattr(bulgu_obj, "guven", 1.0)
        kanıt_metin = getattr(bulgu_obj, "kanit_metni", "") or doc.get("kampanya_adi", "")
        start_pos = getattr(bulgu_obj, "baslangic_konum", None)
        end_pos = getattr(bulgu_obj, "bitis_konum", None)
    elif isinstance(bulgu_obj, dict):
        norm_deger = bulgu_obj.get("deger")
        ham_değer = bulgu_obj.get("ham_metin", str(norm_deger))
        unit_val = bulgu_obj.get("birim", "metin")
        metot = bulgu_obj.get("yontem", "llm")
        guven_score = bulgu_obj.get("guven", 0.85)
        kanıt_metin = bulgu_obj.get("kanit_metni", "") or doc.get("kampanya_adi", "")
        start_pos = bulgu_obj.get("baslangic_konum")
        end_pos = bulgu_obj.get("bitis_konum")
    else:
        return None

    if norm_deger is None:
        return None

    if metot not in GEÇERLİ_YÖNTEMLER:
        metot = "regex"

    simdi = datetime.now(timezone.utc).isoformat()
    banka_id = doc.get("banka_kodu", "genel")
    raw_campaign_id = str(doc.get("_id", "0"))
    kampanya_id = f"kamp_{banka_id}_{raw_campaign_id}"

    return {
        "_id": f"field_{raw_campaign_id}_{alan_adi}",
        "kampanya_id": kampanya_id,
        "raw_campaign_id": raw_campaign_id,
        "banka_id": banka_id,
        "alan_adi": alan_adi,
        "ham_değer": ham_değer,
        "norm_deger": norm_deger,
        "unit": unit_val,
        "metod": metot,
        "guven_score": float(guven_score) if guven_score is not None else 0.0,
        "kanıt_metin": kanıt_metin,
        "start_char": start_pos,
        "end_char": end_pos,
        "created_at": simdi
    }