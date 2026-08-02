import re
import unicodedata

unicode_esleme = {
    # Boşluklar
        "\xa0": " ",       # Bölünmez boşluk
        "\u200b": "",      # Genişliksiz/Gizli boşluk
        "\u200c": "",      # Zero-width non-joiner
        "\ufeff": "",      # BOM (Byte Order Mark)
        
        # Kesme ve Tırnak İşaretleri
        "’": "'",          # Süslü kesme (Örn: VKart’la -> VKart'la)
        "‘": "'",          # Süslü sol tek tırnak
        "“": '"',          # Süslü sol çift tırnak
        "”": '"',          # Süslü sağ çift tırnak
        "„": '"',          # Alt çift tırnak
        
        # Tire ve Maddeler
        "–": "-",          # En dash (Tarih aralıklarındakiler)
        "—": "-",          # Em dash
        "•": "",          # Madde işareti silinir
        "·": "",          # Orta nokta madde işareti silinir
        ">": "",
        "!": "",
        
        # Finansal / Genel Semboller
        "₺": "TL",         # tek formata getirme
}

def unicode_normalize(metin: str) -> str:
    
    #bazı web kopyalamalarından gelen verilerde ş,ç,ğ... gibi harfler tabanda iki farklı karakterin 
    #birleşimi olarak gelebilir. bu harfleri tek bir karaktere dönüştürür
    metin = unicodedata.normalize("NFKC", metin)
    
    for kaynak, hedef in unicode_esleme.items():
        metin = metin.replace(kaynak, hedef)
    
    return metin      
    
def bosluk_duzelt(metin: str) -> str:
    #ardışık birden fazla boşluğu teke indir
    return " ".join(metin.split())


def temizle(metin: str) -> str:
    #temizlik adımlarını gerçekleştirir
    if not metin:
        return "" 
    metin = unicode_normalize(metin)
    metin= bosluk_duzelt(metin)
    
    return metin 