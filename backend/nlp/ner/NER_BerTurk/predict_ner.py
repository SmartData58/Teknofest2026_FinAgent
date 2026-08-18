# -*- coding: utf-8 -*-
"""
Eğitilmiş NER modelini kullanarak yeni ham_metin'lerden alan çıkarır.
Regex KULLANILMAZ — tamamen model çıktısına dayanır.
"""

import json
from transformers import pipeline

MODEL_YOLU = "./ner_model_final"

ner = pipeline(
    "ner",
    model=MODEL_YOLU,
    tokenizer=MODEL_YOLU,
    aggregation_strategy="simple",
)


def kampanyadan_alan_cikar(ham_metin: str) -> dict:
    sonuclar = ner(ham_metin)
    alanlar = {}
    for r in sonuclar:
        etiket = r["entity_group"]
        deger = r["word"]
        alanlar.setdefault(etiket, []).append(deger)
    return alanlar


if __name__ == "__main__":
    with open("smartdata.temiz_kampanyalar.json", encoding="utf-8") as f:
        veriler = json.load(f)

    sonuclar = []
    for kampanya in veriler:
        alanlar = kampanyadan_alan_cikar(kampanya.get("ham_metin", ""))
        kampanya["ner_alanlar"] = alanlar
        sonuclar.append(kampanya)

    with open("kampanyalar_ner_sonuc.json", "w", encoding="utf-8") as f:
        json.dump(sonuclar, f, ensure_ascii=False, indent=2)

    print(f"{len(sonuclar)} kampanya NER ile işlendi -> kampanyalar_ner_sonuc.json")