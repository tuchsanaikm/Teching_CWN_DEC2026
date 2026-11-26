#!/usr/bin/env python3
"""Runs on every node: download model + dataset, build the identical train/test split.

Shuffle the full dataset with seed 0, first 4,000 rows -> train, next 200 rows -> test.
Writes /workspace/lab5/data/{train,test}.jsonl and /workspace/lab5/prepare_report.json
"""
import hashlib, json, os, time
from huggingface_hub import snapshot_download
from datasets import load_dataset

MODEL = "Qwen/Qwen3-8B"
DATASET = "b-mc2/sql-create-context"
ROOT = "/workspace/lab5"
SEED, N_TRAIN, N_TEST = 0, 4000, 200
os.makedirs(f"{ROOT}/data", exist_ok=True)

t0 = time.time()
model_dir = snapshot_download(MODEL, local_dir=f"{ROOT}/models/Qwen3-8B", max_workers=8)
t_model = time.time() - t0
model_bytes = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(model_dir)
                  for f in fs if ".cache" not in r)

t0 = time.time()
ds = load_dataset(DATASET, split="train", cache_dir=f"{ROOT}/hf_datasets")
total = len(ds)
sh = ds.shuffle(seed=SEED)
train = sh.select(range(N_TRAIN))
test = sh.select(range(N_TRAIN, N_TRAIN + N_TEST))
t_data = time.time() - t0

def dump(d, path):
    h = hashlib.sha256()
    with open(path, "w", encoding="utf-8") as f:
        for r in d:
            line = json.dumps({"question": r["question"], "context": r["context"], "answer": r["answer"]},
                              ensure_ascii=False, sort_keys=True) + "\n"
            f.write(line); h.update(line.encode())
    return h.hexdigest()

rep = dict(model=MODEL, model_dir=model_dir, model_gb=round(model_bytes / 1e9, 2),
           model_files=sorted(f for f in os.listdir(model_dir) if not f.startswith(".")),
           model_download_s=round(t_model, 1), dataset=DATASET, dataset_total=total,
           dataset_s=round(t_data, 1), seed=SEED, n_train=len(train), n_test=len(test),
           train_sha256=dump(train, f"{ROOT}/data/train.jsonl"),
           test_sha256=dump(test, f"{ROOT}/data/test.jsonl"))
json.dump(rep, open(f"{ROOT}/prepare_report.json", "w"), indent=1)
print(json.dumps(rep))
