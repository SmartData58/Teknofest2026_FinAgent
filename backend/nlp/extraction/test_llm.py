from backend.nlp.extraction.hybrid import hibrit_cikar

ornek_metin = """
Sayın Müşterimiz, 
Girişimcilere özel lansman kampanyamız kapsamında 100000 TL limitli finansman 
kullanım imkanı sunulmaktadır. Geri ödemelerinizi 24 ay taksitle gerçekleştirebilirsiniz. 
Ayrıca bu aya özel kâr oranımız % 1,49 olarak uygulanacaktır.
"""

def test_calistir():
    print("\n--- HİBRİT NLP ÇIKARIM TESTİ ---")
    sonuclar = hibrit_cikar("isbankasi", ornek_metin)

    print("\n--- ÇIKARILAN SONUÇLAR ---")
    if not sonuclar:
        print("Hiçbir alan çıkarılamadı.")
    else:
        for alan, bulgu in sonuclar.items():
            print(f"📌 {alan}: {bulgu.deger} (Yöntem: {bulgu.yontem}, Güven: {bulgu.guven})")

if __name__ == "__main__":
    test_calistir()