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
    #Genel Bilgiler
    "baslangic_tarihi": {"birim": "gün", "aciklama": "YYYY-MM-DD kampanya başlangıcı"},
    "bitis_tarihi": {"birim": "gün", "aciklama": "YYYY-MM-DD kampanya bitişi"},
    "sure_gun": {"birim": "gün", "aciklama": "baslangic ve bitis tarihleri arasındaki süre"},
    "hedef_kitle": {"birim": "metin", "aciklama": "örn: ['yeni_musteriler']"},
    "kampanya_turu": {"birim": "metin", "aciklama": "Finansman, Kredi Kartı, MGM vb."},
    "alt_kategori": {"birim": "metin", "aciklama": "Konut, Taşıt, İhtiyaç vb."},
    
    "kar_paylasim_orani": {"birim": "yüzde", "aciklama": "Kâr payı oranı (%)"},
    "taksit": {"birim": "ay", "acıklama": "azami taksit sayısı"},
    "vade_ay": {"birim": "ay", "aciklama": "Azami vade sayısı"},
    "finansman_tutari": {"birim": "TL", "acıklama": "kampanya finansman tutarı"},
    "min_fin_tutar": {"birim": "TL", "aciklama": "Asgari finansman tutarı"},
    "max_fin_tutar": {"birim": "TL", "aciklama": "Azami finansman tutarı"},
    "tahsis_ucreti": {"birim": "TL", "aciklama": "Tahsis/masraf ücreti masrafı"},
    #"masraf_tl": {"birim": "TL", "aciklama": "Toplam masraf tutarı"},
    "masraf_bilgi": {"birim": "metin", "aciklama": "Masraf açıklama metni"},
    #"masraf_bilgisi": {"birim": "metin", "aciklama": "Detaylı masraf bilgisi"},
    "odul_tutari_tl": {"birim": "TL", "aciklama": "Kazanılan ödül/bonus tutarı"},
    "odul_metni": {"birim": "metin", "aciklama": "Ödül detay açıklaması"},
    #"cashback_orani": {"birim": "yüzde", "aciklama": "Nakit iade oranı (%)"},
    #"indirim_orani_yuzde": {"birim": "yüzde", "aciklama": "İndirim oranı (%)"},
    "odul_tip": {"birim": "metin", "acıklama": "örn: puan, iade "},
    "puan_kazanc": {"birim": "TL", "aciklama": "Puan/mil kazancı"},
    #"min_harcama_tl": {"birim": "TL", "aciklama": "Minimum harcama şartı"},
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
    sure_gun: Optional[AlanBulgusuLLM] = Field(default=None)
    hedef_kitle: Optional[AlanBulgusuLLM] = Field(default=None)
    kampanya_turu: Optional[AlanBulgusuLLM] = Field(default=None)
    alt_kategori: Optional[AlanBulgusuLLM] = Field(default=None)

    kar_paylasim_orani: Optional[AlanBulgusuLLM] = Field(default=None)
    #finansman_kar_orani: Optional[AlanBulgusuLLM] = Field(default=None)
    taksit: Optional[AlanBulgusuLLM] = Field(default=None)
    vade_ay: Optional[AlanBulgusuLLM] = Field(default=None)
    finansman_tutari: Optional[AlanBulgusuLLM] = Field(default=None)
    min_fin_tutar: Optional[AlanBulgusuLLM] = Field(default=None)
    max_fin_tutar: Optional[AlanBulgusuLLM] = Field(default=None)
    tahsis_ucreti: Optional[AlanBulgusuLLM] = Field(default=None)
    #masraf_tl: Optional[AlanBulgusuLLM] = Field(default=None)
    masraf_bilgi: Optional[AlanBulgusuLLM] = Field(default=None)
    #masraf_bilgisi: Optional[AlanBulgusuLLM] = Field(default=None)

    odul_tutari_tl: Optional[AlanBulgusuLLM] = Field(default=None)
    odul_metni: Optional[AlanBulgusuLLM] = Field(default=None)
    #cashback_orani: Optional[AlanBulgusuLLM] = Field(default=None)
    #indirim_orani_yuzde: Optional[AlanBulgusuLLM] = Field(default=None)
    odul_tip: Optional[AlanBulgusuLLM] = Field(default=None)
    puan_kazanc: Optional[AlanBulgusuLLM] = Field(default=None)
    #min_harcama_tl: Optional[AlanBulgusuLLM] = Field(default=None)
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


