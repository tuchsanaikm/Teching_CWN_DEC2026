"""Lab4 / 2_data_parallel - step 1: download model + dataset, split, write sample table.

Run on the GPU machine:
    python prepare.py --root /workspace/lab4_dp
"""
import argparse
import json
import os

MODEL_ID = "Qwen/Qwen3-8B"
DATASET_ID = "b-mc2/sql-create-context"
SEED = 0
N_TRAIN = 4000
N_TEST = 200
N_SAMPLES = 6


def md_cell(text: str) -> str:
    """Make a string safe for one markdown table cell."""
    return " ".join(str(text).split()).replace("|", "\\|")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/workspace/lab4_dp")
    ap.add_argument("--skip-model", action="store_true")
    args = ap.parse_args()

    model_dir = os.path.join(args.root, "models", MODEL_ID.split("/")[-1])
    data_dir = os.path.join(args.root, "data")
    res_dir = os.path.join(args.root, "results")
    for d in (model_dir, data_dir, res_dir):
        os.makedirs(d, exist_ok=True)

    # ---- dataset ----
    from datasets import load_dataset

    ds = load_dataset(DATASET_ID, split="train")
    total = len(ds)
    shuffled = ds.shuffle(seed=SEED)
    train = shuffled.select(range(N_TRAIN))
    test = shuffled.select(range(N_TRAIN, N_TRAIN + N_TEST))
    train.to_json(os.path.join(data_dir, "train.jsonl"), force_ascii=False)
    test.to_json(os.path.join(data_dir, "test.jsonl"), force_ascii=False)

    overlap = len(
        {(r["question"], r["context"]) for r in train}
        & {(r["question"], r["context"]) for r in test}
    )

    lines = [
        f"# ตัวอย่างข้อมูลจาก `{DATASET_ID}`",
        "",
        f"สับด้วย seed {SEED} · Training Set {len(train):,} ตัวอย่าง · Test Set {len(test):,} ตัวอย่าง"
        f" (จากทั้งหมด {total:,} ตัวอย่าง)",
        "",
        f"ตารางนี้คือ {N_SAMPLES} รายการแรกของ Training Set หลังสับ",
        "",
        "| # | คำถาม (question) | โครงสร้างตาราง (context) | SQL เฉลย (answer) |",
        "|---|---|---|---|",
    ]
    for i in range(N_SAMPLES):
        r = train[i]
        lines.append(
            f"| {i + 1} | {md_cell(r['question'])} | `{md_cell(r['context'])}` | `{md_cell(r['answer'])}` |"
        )
    with open(os.path.join(res_dir, "dataset_samples.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # ---- model ----
    model_files, model_bytes = 0, 0
    if not args.skip_model:
        from huggingface_hub import snapshot_download

        snapshot_download(MODEL_ID, local_dir=model_dir)
    for dp, _, fns in os.walk(model_dir):
        if ".cache" in dp:
            continue
        for fn in fns:
            model_files += 1
            model_bytes += os.path.getsize(os.path.join(dp, fn))

    info = {
        "model_id": MODEL_ID,
        "model_dir": model_dir,
        "model_files": model_files,
        "model_gb": round(model_bytes / 1e9, 2),
        "dataset_id": DATASET_ID,
        "dataset_total": total,
        "columns": ds.column_names,
        "seed": SEED,
        "n_train": len(train),
        "n_test": len(test),
        "train_test_overlap": overlap,
    }
    with open(os.path.join(res_dir, "prepare_info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
