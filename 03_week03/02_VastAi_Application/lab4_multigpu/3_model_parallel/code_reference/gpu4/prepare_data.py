"""Download Qwen/Qwen3-8B and b-mc2/sql-create-context, shuffle (seed 0),
split 4,000 train / 200 test, and write a 6-row sample table."""
import json, os, sys
from datasets import load_dataset
from huggingface_hub import snapshot_download

OUT = sys.argv[1] if len(sys.argv) > 1 else "/workspace/mp4"
MODEL, DATA = "Qwen/Qwen3-8B", "b-mc2/sql-create-context"
N_TRAIN, N_TEST, SEED = 4000, 200, 0
os.makedirs(f"{OUT}/data", exist_ok=True)
os.makedirs(f"{OUT}/results", exist_ok=True)

ds = load_dataset(DATA, split="train")
total = len(ds)
ds = ds.shuffle(seed=SEED)
train = ds.select(range(N_TRAIN))
test = ds.select(range(N_TRAIN, N_TRAIN + N_TEST))
train.to_json(f"{OUT}/data/train.jsonl")
test.to_json(f"{OUT}/data/test.jsonl")

def cell(s):
    return " ".join(str(s).split()).replace("|", "\\|")

lines = [
    f"# ตัวอย่างจาก {DATA}", "",
    f"สับด้วย seed {SEED} · Training Set {len(train):,} ตัวอย่าง · Test Set {len(test):,} ตัวอย่าง "
    f"(จากทั้งหมด {total:,}) · ตาราง 6 รายการแรกของ Training Set", "",
    "| # | คำถาม (question) | โครงสร้างตาราง (context) | SQL เฉลย (answer) |",
    "|---|---|---|---|",
]
for i in range(6):
    r = train[i]
    lines.append(f"| {i+1} | {cell(r['question'])} | `{cell(r['context'])}` | `{cell(r['answer'])}` |")
open(f"{OUT}/results/dataset_samples.md", "w").write("\n".join(lines) + "\n")

path = snapshot_download(MODEL)
size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(path) for f in fs
           if not os.path.islink(os.path.join(dp, f)) or os.path.exists(os.path.join(dp, f)))
info = {"model": MODEL, "model_path": path, "model_gb": round(size / 1e9, 2),
        "dataset": DATA, "dataset_total": total, "seed": SEED,
        "train": len(train), "test": len(test), "columns": ds.column_names}
json.dump(info, open(f"{OUT}/results/prepare_info.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(info, ensure_ascii=False))
