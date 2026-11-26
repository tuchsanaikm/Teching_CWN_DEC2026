#!/usr/bin/env python3
"""รันบนเครื่อง GPU: โหลดโมเดล + Dataset, สับด้วย seed 0, แบ่ง train/test, ทำตารางตัวอย่าง

ใช้: python prepare.py [--skip-model]
ผลลัพธ์อยู่ใต้ /workspace/lab4_mp/
"""
import json
import os
import sys

MODEL_ID = "Qwen/Qwen3-8B"
DATASET_ID = "b-mc2/sql-create-context"
SEED = 0
N_TRAIN = 4000
N_TEST = 200
N_SAMPLES = 6

ROOT = "/workspace/lab4_mp"
MODEL_DIR = os.path.join(ROOT, "models", "Qwen3-8B")
DATA_DIR = os.path.join(ROOT, "data")
RESULT_DIR = os.path.join(ROOT, "results")


def cell(text):
    """ทำให้ข้อความอยู่ในช่องตาราง markdown ได้"""
    return " ".join(str(text).split()).replace("|", "\\|")


def write_jsonl(ds, path):
    with open(path, "w", encoding="utf-8") as f:
        for row in ds:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    for d in (MODEL_DIR, DATA_DIR, RESULT_DIR):
        os.makedirs(d, exist_ok=True)

    # ---------- โมเดล ----------
    if "--skip-model" not in sys.argv:
        from huggingface_hub import snapshot_download
        snapshot_download(MODEL_ID, local_dir=MODEL_DIR, max_workers=16)
    model_files = sorted(os.listdir(MODEL_DIR))
    model_bytes = sum(
        os.path.getsize(os.path.join(MODEL_DIR, f)) for f in model_files
        if os.path.isfile(os.path.join(MODEL_DIR, f)))

    # ---------- Dataset ----------
    from datasets import load_dataset
    full = load_dataset(DATASET_ID, split="train")
    full.save_to_disk(os.path.join(DATA_DIR, "full"))
    shuffled = full.shuffle(seed=SEED)
    train = shuffled.select(range(N_TRAIN))
    test = shuffled.select(range(N_TRAIN, N_TRAIN + N_TEST))
    write_jsonl(train, os.path.join(DATA_DIR, "train.jsonl"))
    write_jsonl(test, os.path.join(DATA_DIR, "test.jsonl"))

    # ---------- ตารางตัวอย่าง ----------
    lines = [
        "# ตัวอย่าง Dataset `b-mc2/sql-create-context`",
        "",
        f"สับด้วย seed {SEED} แล้วแบ่ง Training Set {len(train):,} ตัวอย่าง "
        f"และ Test Set {len(test):,} ตัวอย่าง (จากทั้งหมด {len(full):,} ตัวอย่าง)",
        "",
        f"ตารางนี้คือ {N_SAMPLES} รายการแรกของ Training Set",
        "",
        "| # | คำถาม (`question`) | โครงสร้างตาราง (`context`) | SQL เฉลย (`answer`) |",
        "|---|---|---|---|",
    ]
    for i in range(N_SAMPLES):
        r = train[i]
        lines.append(
            f"| {i + 1} | {cell(r['question'])} | `{cell(r['context'])}` "
            f"| `{cell(r['answer'])}` |")
    with open(os.path.join(RESULT_DIR, "dataset_samples.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    summary = {
        "model_id": MODEL_ID,
        "model_dir": MODEL_DIR,
        "model_files": model_files,
        "model_gb": round(model_bytes / 1e9, 2),
        "dataset_id": DATASET_ID,
        "columns": full.column_names,
        "n_full": len(full),
        "seed": SEED,
        "n_train": len(train),
        "n_test": len(test),
        "overlap": len(set(map(json.dumps, train)) & set(map(json.dumps, test))),
    }
    with open(os.path.join(RESULT_DIR, "prepare_summary.json"), "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
