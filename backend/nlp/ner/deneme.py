import json
import re
from typing import Dict, List, Any

class CampaignNERExtractor:
    def __init__(self):
        # 1. Sabit Tanımlı Kurum ve Banka İsimleri
        self.organizations = [
            "Hayat Finans", "GastroClub", "Troy", "Spotify", "Netflix", 
            "ChatGPT", "OpenAI", "HBO Max", "YouTube Premium", "tabii", "TOD",
            "App Store", "Google Play Store", "App Gallery", "İstanbul Kart"
        ]
        
        # 2. Ürün / Kart / Hizmet İsimleri
        self.products = [
            "Avantajlı Hesap", "Hayat Avantajlı Katılma Hesabı", "Avantajlı Günlük Hesap",
            "TL Katılma Hesabı", "TL Günlük Hesap", "Cari Hesap", "Katılma Hesabı",
            "Hayat Finans Banka Kartı", "Biz Kart", "Biz Kart QR",
            "Hayat FX", "Hayat Pay"
        ]
        
        # 3. İşlem / Kanal Türleri
        self.channels = [
            "Hayat Finans Mobil Uygulaması", "SMS", "Görüntülü Görüşme", 
            "EFT", "FAST", "Havale", "Virman", "QR Kod", "ATM"
        ]

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        entities = {
            "ORGANIZATION": [],
            "PRODUCT": [],
            "CHANNEL": [],
            "DATE": [],
            "MONEY": [],
            "PERCENT": [],
            "QUANTITY": []
        }
        
        # --- Regex Desenleri ---
        # Para Tutarları (Örn: 2.000 TL, 10.000TL, 5.000 USD, 80.000 TL)
        money_pattern = r'\b\d{1,3}(?:\.\d{3})*\s*(?:TL|USD|EUR)\b'
        
        # Yüzdeler (Örn: %20, %0,1, %75)
        percent_pattern = r'%\s*\d+(?:[\.,]\d+)?'
        
        # Tarih Aralıkları ve Belirteçleri
        date_pattern = r'\b\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)(?:\s+\d{4})?\b'
        duration_pattern = r'\b\d+\s*(?:gün|günlük|iş günü|ay|yıl)\b'
        
        # Nicel Değerler / Kotalar (Örn: 5 kişi, 1.000 kişi, 4 taksit)
        quantity_pattern = r'\b\d+(?:\.\d{3})*\s*(?:kişi|taksit|adet)\b'

        # --- Regex Yakalamaları ---
        entities["MONEY"] = list(set(re.findall(money_pattern, text, re.IGNORECASE)))
        entities["PERCENT"] = list(set(re.findall(percent_pattern, text)))
        
        dates_found = re.findall(date_pattern, text, re.IGNORECASE)
        durations_found = re.findall(duration_pattern, text, re.IGNORECASE)
        entities["DATE"] = list(set(dates_found + durations_found))
        
        entities["QUANTITY"] = list(set(re.findall(quantity_pattern, text, re.IGNORECASE)))

        # --- Kelime/Sözlük Eşleştirme ---
        for org in self.organizations:
            if re.search(r'\b' + re.escape(org) + r'\b', text, re.IGNORECASE):
                entities["ORGANIZATION"].append(org)
                
        for prod in self.products:
            if re.search(r'\b' + re.escape(prod) + r'\b', text, re.IGNORECASE):
                entities["PRODUCT"].append(prod)
                
        for ch in self.channels:
            if re.search(r'\b' + re.escape(ch) + r'\b', text, re.IGNORECASE):
                entities["CHANNEL"].append(ch)

        # Liste İçindeki Tekrarları Temizle
        for key in entities:
            entities[key] = sorted(list(set(entities[key])))

        return entities

    def process_mongodb_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for doc in records:
            doc_id = str(doc.get("_id", {}).get("$oid", doc.get("_id", "")))
            ham_metin = doc.get("ham_metin", "")
            
            extracted_entities = self.extract_entities(ham_metin)
            
            result_doc = {
                "id": doc_id,
                "url": doc.get("url"),
                "banka_adi": doc.get("banka_adi"),
                "baslik": doc.get("baslik"),
                "kategori": doc.get("kategori"),
                "entities": extracted_entities
            }
            results.append(result_doc)
        return results


# --- Test Çalıştırması ---
if __name__ == "__main__":
    # Girdi verisi (MongoDB doküman grubunuz)
    raw_data = [
        {
            "_id": {"$oid": "6a8081dd697da0af8c7ac650"},
            "url": "https://hayatfinans.com.tr/kampanyalar/arkadasini-getir-avantajli-hesap-ac-nakit-odul-kazan",
            "banka_adi": "Hayat Finans",
            "baslik": "Arkadaşını Davet Et, Avantajlı Hesapla Kazanmaya Başla",
            "kategori": "Arkadaşını Getir",
            "ham_metin": "Hayat Finans Kampanyalar Arkadaşını Davet Et, Avantajlı Hesapla Kazanmaya Başla. Davet eden kişi başı maksimum 2.000 TL, toplamda 5 kişi için maksimum 10.000 TL nakit ödül kazanabilir. Kampanya 16 Temmuz - 16 Ağustos 2026 tarihleri arasında geçerlidir. Müşteri ilk Avantajlı Katılma Hesabı açtıktan sonra %20 nakit ödül kazanır. Hayat Finans Mobil Uygulaması üzerinden SMS ile bilgilendirme yapılır."
        }
    ]

    extractor = CampaignNERExtractor()
    ner_results = extractor.process_mongodb_records(raw_data)

    print(json.dumps(ner_results, ensure_ascii=False, indent=2))