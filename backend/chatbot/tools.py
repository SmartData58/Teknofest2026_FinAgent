# 🛠️ TEMİZLİK: Bu dosyada SADECE gercek_finansman_hesapla() gerçekten
# kullanılıyordu (generate_response.py'nin "hesaplama" niyetinde çağrılıyor —
# bkz. `from chatbot.tools import gercek_finansman_hesapla`). Aşağıdakiler
# kod tabanının hiçbir yerinden çağrılmadığı grep ile doğrulanarak SİLİNDİ:
#   - init_mongo_db() + 32 kayıtlık sahte örnek veri listesi: sadece dosya
#     doğrudan `python tools.py` ile çalıştırılırsa tetikleniyordu (üstelik
#     finagent.kampanyalar'ı SİLİP test verisiyle dolduruyordu); production
#     akışı buna hiç dokunmuyor, gerçek veri smartdata.* koleksiyonlarında.
#   - safe_json_parse(): hiçbir dosyada import/çağrı yok.
#   - grafigi_hazirla_mongo_dinamik() (bu dosyadaki, düz finagent.kampanyalar
#     şemasına bakan versiyon): hiçbir yerden çağrılmıyor. Gerçek production
#     akışı generate_response.py'nin KENDİ İÇİNDEKİ aynı isimli ama farklı
#     (gerçek islenmis_kampanyalar/smartdata iç içe şemasını okuyan)
#     fonksiyonunu kullanıyor — bu ikisi hiçbir zaman birbirinin yerine
#     geçmiyordu.
# Bu fonksiyonlarla birlikte artık kullanılmayan importlar (os, json, re,
# MongoClient, logger) ve MONGO_URI/DB_NAME/COLLECTION_NAME sabitleri de
# kaldırıldı — hiçbiri chatbot.tools dışından import edilmiyordu (grep ile
# doğrulandı).


def gercek_finansman_hesapla(tutar: float, vade: int, kar_payi: float) -> str:
    if kar_payi == 0:
        return ""
    r = kar_payi / 100
    aylik = tutar * (r * (1 + r) ** vade) / (((1 + r) ** vade) - 1)
    toplam = aylik * vade
    return (
        f"| Parametre | Değer |\n| :--- | :--- |\n"
        f"| **Finansman Tutarı** | {tutar:,.2f} TL |\n"
        f"| **Vade Süresi** | {vade} Ay |\n"
        f"| **Kâr Payı Oranı** | %{kar_payi} |\n"
        f"| **Aylık Taksit** | **{aylik:,.2f} TL** |\n"
        f"| **Toplam Geri Ödeme** | **{toplam:,.2f} TL** |"
    )