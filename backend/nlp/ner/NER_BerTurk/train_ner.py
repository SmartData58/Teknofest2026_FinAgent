# -*- coding: utf-8 -*-
"""
train.json / test.json (span formatlı) verilerle BERTurk tabanlı
bir token-classification (NER) modeli fine-tune eder.

Kurulum:
    pip install transformers torch datasets seqeval evaluate --break-system-packages
"""

import json
import numpy as np
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification,
)
import evaluate

MODEL_ADI = "dbmdz/bert-base-turkish-cased"

ETIKET_ISIMLERI = [
    "BASLANGIC_TARIH", "BITIS_TARIH", "TUR", "KAR_PAYI", "VADE", "MASRAF",
    "ODUL_AVANTAJ", "HEDEF_KITLE", "MGM_DAVET_BASI_KAZANC", "MGM_MAX_KISI_SAYI",
]

# BIO etiket listesi: O + her etiket için B-/I-
label_list = ["O"] + [f"{p}-{e}" for e in ETIKET_ISIMLERI for p in ("B", "I")]
label2id = {l: i for i, l in enumerate(label_list)}
id2label = {i: l for i, l in enumerate(label_list)}


def veri_yukle(path):
    with open(path, encoding="utf-8") as f:
        veriler = json.load(f)
    # [start, end, "TAG"] listelerini {"start":, "end":, "tag":} sözlüğüne çevir
    # (pyarrow karışık tipli listeleri şema çıkarımında reddediyor)
    for kayit in veriler:
        kayit["labels"] = [
            {"start": s, "end": e, "tag": t} for s, e, t in kayit["labels"]
        ]
    return veriler


def span_to_bio_labels(text, spans, offset_mapping):
    """Tokenizer'ın offset_mapping'ine göre her token için BIO etiketi üretir."""
    labels = ["O"] * len(offset_mapping)
    for start, end, tag in spans:
        basladi = False
        for i, (tok_s, tok_e) in enumerate(offset_mapping):
            if tok_s == tok_e:  # özel token ([CLS], [SEP], padding)
                continue
            if tok_s < end and tok_e > start:  # token span ile kesişiyor
                labels[i] = ("B-" if not basladi else "I-") + tag
                basladi = True
    return labels


def veri_hazirla(kayitlar, tokenizer):
    metinler = [k["text"] for k in kayitlar]
    tum_spanlar = [
        [(d["start"], d["end"], d["tag"]) for d in k["labels"]] for k in kayitlar
    ]

    tokenized = tokenizer(
        metinler,
        truncation=True,
        max_length=512,
        padding=False,
        return_offsets_mapping=True,
    )

    tum_etiketler = []
    for i, offsets in enumerate(tokenized["offset_mapping"]):
        bio = span_to_bio_labels(metinler[i], tum_spanlar[i], offsets)
        tum_etiketler.append([label2id[l] for l in bio])

    tokenized["labels"] = tum_etiketler
    tokenized.pop("offset_mapping")
    return tokenized


def main():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ADI)

    train_kayitlar = veri_yukle("train.json")
    test_kayitlar = veri_yukle("test.json")

    train_ds = Dataset.from_list(train_kayitlar)
    train_ds = train_ds.map(
        lambda batch: veri_hazirla(
            [{"text": t, "labels": l} for t, l in zip(batch["text"], batch["labels"])],
            tokenizer,
        ),
        batched=True,
        remove_columns=train_ds.column_names,
    )

    test_ds = Dataset.from_list(test_kayitlar)
    test_ds = test_ds.map(
        lambda batch: veri_hazirla(
            [{"text": t, "labels": l} for t, l in zip(batch["text"], batch["labels"])],
            tokenizer,
        ),
        batched=True,
        remove_columns=test_ds.column_names,
    )

    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_ADI, num_labels=len(label_list), id2label=id2label, label2id=label2id
    )

    data_collator = DataCollatorForTokenClassification(tokenizer)
    seqeval = evaluate.load("seqeval")

    def compute_metrics(p):
        predictions, labels = p
        predictions = np.argmax(predictions, axis=2)

        true_predictions = [
            [id2label[p_] for (p_, l_) in zip(pred, lab) if l_ != -100]
            for pred, lab in zip(predictions, labels)
        ]
        true_labels = [
            [id2label[l_] for (p_, l_) in zip(pred, lab) if l_ != -100]
            for pred, lab in zip(predictions, labels)
        ]
        results = seqeval.compute(predictions=true_predictions, references=true_labels)
        return {
            "precision": results["overall_precision"],
            "recall": results["overall_recall"],
            "f1": results["overall_f1"],
            "accuracy": results["overall_accuracy"],
        }

    args = TrainingArguments(
        output_dir="./ner_model",
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=10,
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=test_ds,
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    print(trainer.evaluate())

    trainer.save_model("./ner_model_final")
    tokenizer.save_pretrained("./ner_model_final")
    print("Model kaydedildi: ./ner_model_final")


if __name__ == "__main__":
    main()