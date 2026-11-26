"""Lab 4 / 1_single_gpu: download model + dataset, split, and write a sample table.

Run on the GPU instance:  python prepare_data.py
"""
import json
import os

from datasets import load_dataset
from huggingface_hub import snapshot_download

MODEL_ID = "Qwen/Qwen3-8B"
DATASET_ID = "b-mc2/sql-create-context"
SEED = 0
N_TRAIN = 4000
N_TEST = 200
N_SAMPLES = 6

ROOT = os.environ.get("LAB_ROOT", "/workspace/lab4")
MODEL_DIR = os.path.join(ROOT, "models", "Qwen3-8B")
DATA_DIR = os.path.join(ROOT, "data")
RESULTS_DIR = os.path.join(ROOT, "results")


def cell(text):
    """Make a string safe for one markdown table cell."""
    return " ".join(str(text).split()).replace("|", "\\|")


def main():
    for d in (MODEL_DIR, DATA_DIR, RESULTS_DIR):
        os.makedirs(d, exist_ok=True)

    # 1) model
    snapshot_download(MODEL_ID, local_dir=MODEL_DIR)
    model_bytes = sum(
        os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(MODEL_DIR) for f in fs
    )

    # 2) dataset -> shuffle(seed=0) -> first 4000 train, next 200 test (no overlap)
    full = load_dataset(DATASET_ID, split="train")
    shuffled = full.shuffle(seed=SEED)
    train = shuffled.select(range(N_TRAIN))
    test = shuffled.select(range(N_TRAIN, N_TRAIN + N_TEST))
    train.to_json(os.path.join(DATA_DIR, "train.jsonl"))
    test.to_json(os.path.join(DATA_DIR, "test.jsonl"))

    # 3) sample table: first 6 rows of the training set
    lines = [
        f"# ตัวอย่างข้อมูล {DATASET_ID}",
        "",
        f"สับด้วย seed {SEED} · Training Set {len(train):,} ตัวอย่าง · Test Set {len(test):,} ตัวอย่าง"
        f" (จากทั้งหมด {len(full):,}) · ตัวอย่างด้านล่างคือ {N_SAMPLES} รายการแรกของ Training Set",
        "",
        "| # | คำถาม (question) | โครงสร้างตาราง (context) | SQL เฉลย (answer) |",
        "|---|---|---|---|",
    ]
    for i in range(N_SAMPLES):
        r = train[i]
        lines.append(
            f"| {i + 1} | {cell(r['question'])} | `{cell(r['context'])}` | `{cell(r['answer'])}` |"
        )
    with open(os.path.join(RESULTS_DIR, "dataset_samples.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    summary = {
        "model": MODEL_ID,
        "model_dir": MODEL_DIR,
        "model_gb": round(model_bytes / 1e9, 2),
        "dataset": DATASET_ID,
        "dataset_total": len(full),
        "seed": SEED,
        "train": len(train),
        "test": len(test),
        "columns": full.column_names,
    }
    with open(os.path.join(RESULTS_DIR, "prepare_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
