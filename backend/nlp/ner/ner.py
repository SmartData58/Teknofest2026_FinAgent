import json
import numpy as np
from datasets import Dataset, DatasetDict
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    DataCollatorForTokenClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
)
from peft import LoraConfig, get_peft_model, TaskType
import evaluate

MODEL_NAME = "ytu-ce-cosmos/modernbert-tr-base"

TRAIN_PATH = r"D:\ner\datasets\train_ner (9).json"
VAL_PATH = r"D:\ner\datasets\validation_ner (2).json"
TEST_PATH = r"D:\ner\datasets\test_ner (2).json"

OUT_DIR = "./modernbert-tr-ner-lora"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


train_data = load_json(TRAIN_PATH)
val_data = load_json(VAL_PATH)
test_data = load_json(TEST_PATH)

all_data = train_data + val_data + test_data

labels = sorted({tag for ex in all_data for tag in ex["ner_tags"]})
label2id = {label: i for i, label in enumerate(labels)}
id2label = {i: label for label, i in label2id.items()}


def encode_labels(data):
    encoded = []
    for ex in data:
        ex = ex.copy()
        ex["labels"] = [label2id[tag] for tag in ex["ner_tags"]]
        encoded.append(ex)
    return encoded


dataset = DatasetDict({
    "train": Dataset.from_list(encode_labels(train_data)),
    "validation": Dataset.from_list(encode_labels(val_data)),
    "test": Dataset.from_list(encode_labels(test_data)),
})

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)


def tokenize_and_align_labels(examples):
    tokenized = tokenizer(
        examples["tokens"],
        is_split_into_words=True,
        truncation=True,
        max_length=512,
    )

    aligned_labels = []

    for i, labels_for_example in enumerate(examples["labels"]):
        word_ids = tokenized.word_ids(batch_index=i)
        previous_word_id = None
        label_ids = []

        for word_id in word_ids:
            if word_id is None:
                label_ids.append(-100)
            elif word_id != previous_word_id:
                label_ids.append(labels_for_example[word_id])
            else:
                label_ids.append(-100)

            previous_word_id = word_id

        aligned_labels.append(label_ids)

    tokenized["labels"] = aligned_labels
    return tokenized


tokenized_ds = dataset.map(
    tokenize_and_align_labels,
    batched=True,
    remove_columns=dataset["train"].column_names,
)

base_model = AutoModelForTokenClassification.from_pretrained(
    MODEL_NAME,
    num_labels=len(labels),
    id2label=id2label,
    label2id=label2id,
)

lora_config = LoraConfig(
    task_type=TaskType.TOKEN_CLS,
    r=8,
    lora_alpha=16,
    lora_dropout=0.1,
    target_modules=["Wqkv", "Wo"],
)

model = get_peft_model(base_model, lora_config)
model.print_trainable_parameters()

seqeval = evaluate.load("seqeval")


def compute_metrics(pred):
    logits, labels_batch = pred
    predictions = np.argmax(logits, axis=-1)

    true_predictions = []
    true_labels = []

    for prediction, label in zip(predictions, labels_batch):
        pred_tags = []
        label_tags = []

        for pred_id, label_id in zip(prediction, label):
            if label_id == -100:
                continue

            pred_tags.append(id2label[int(pred_id)])
            label_tags.append(id2label[int(label_id)])

        true_predictions.append(pred_tags)
        true_labels.append(label_tags)

    results = seqeval.compute(
        predictions=true_predictions,
        references=true_labels,
        zero_division=0,
    )
    print(results)

    return {
        "precision": results["overall_precision"],
        "recall": results["overall_recall"],
        "f1": results["overall_f1"],
        "accuracy": results["overall_accuracy"],
    }


args = TrainingArguments(
    output_dir=OUT_DIR,
    eval_strategy="epoch",
    save_strategy="epoch",
    learning_rate=2e-4,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    gradient_accumulation_steps=4,
    num_train_epochs=2, #20
    weight_decay=0.01,
    #warmup_ratio=0.1,
    warmup_steps=5,
    logging_steps=5,
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    greater_is_better=True,
    save_total_limit=2,
    fp16=True,
    report_to="none",
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=tokenized_ds["train"],
    eval_dataset=tokenized_ds["validation"],
    data_collator=DataCollatorForTokenClassification(tokenizer),
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
)

trainer.train()

test_metrics = trainer.evaluate(tokenized_ds["test"])
print(test_metrics)

trainer.save_model(OUT_DIR)
tokenizer.save_pretrained(OUT_DIR)