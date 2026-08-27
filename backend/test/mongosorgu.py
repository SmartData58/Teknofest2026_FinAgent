import os
import pymongo
from pymongo.errors import ConnectionFailure, OperationFailure

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def alanlari_teker_teker_sorgula():
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        user = os.getenv("MONGO_USER", "admin")
        pwd = os.getenv("MONGO_PASSWORD", "")
        host = os.getenv("MONGO_HOST", "localhost")
        port = os.getenv("MONGO_PORT", "27017")
        if pwd:
            mongo_uri = f"mongodb://{user}:{pwd}@{host}:{port}/?authSource=admin"
        else:
            mongo_uri = f"mongodb://{host}:{port}/?authSource=admin"
    
    try:
        client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        
        db = client["smartdata"]
        collection = db["islenmis_kampanyalar"]
        
        # Görselden alınan finansman detay alanları
        finansman_alanlari = [
            "finansman_tutari", 
            "kar_payi_orani", 
            "masraf_bilgi", 
            "tahsis_ucreti", 
            "taksit", 
            "vade_ay"
        ]
        
        # Görselden alınan promosyon detay alanları
        promosyon_alanlari = [
            "kazanc_metin", 
            "nakit_iade_yuzde", 
            "odul_metni", 
            "odul_tip", 
            "odul_tutari", 
            "puan_kazanc"
        ]
        
        toplam_kampanya = collection.count_documents({})
        print(f"\nVeritabanındaki Toplam Kampanya Sayısı: {toplam_kampanya}\n")
        
        print("-" * 40)
        print(" FİNANSMAN DETAY ALANLARI (Dolu Kayıtlar)")
        print("-" * 40)
        for alan in finansman_alanlari:
            tam_yol = f"finansman_detay.{alan}"
            # Alanın var olduğu ve boş olmadığı durumu sorguluyoruz
            query = {tam_yol: {"$exists": True, "$ne": None}}
            sayi = collection.count_documents(query)
            print(f"{alan:<20} : {sayi} kayıt")
            
        print("\n" + "-" * 40)
        print(" PROMOSYON DETAY ALANLARI (Dolu Kayıtlar)")
        print("-" * 40)
        for alan in promosyon_alanlari:
            tam_yol = f"promosyon_detay.{alan}"
            query = {tam_yol: {"$exists": True, "$ne": None}}
            sayi = collection.count_documents(query)
            print(f"{alan:<20} : {sayi} kayıt")
            
        print("\nSorgulama tamamlandı.\n")
            
    except OperationFailure as e:
        print(f"HATA: Yetkilendirme veya veritabanı işlemi sorunu: {e}")
    except Exception as e:
        print(f"Beklenmeyen bir hata oluştu: {e}")
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    alanlari_teker_teker_sorgula()