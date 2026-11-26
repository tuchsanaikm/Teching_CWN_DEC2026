"""Download Qwen/Qwen3-8B and b-mc2/sql-create-context, shuffle (seed 0), split 4000/200, write sample table."""
import json, os
from datasets import load_dataset
from huggingface_hub import snapshot_download

ROOT = "/workspace/lab4_dp4"
MODEL_DIR = f"{ROOT}/models/Qwen3-8B"
DATA_DIR = f"{ROOT}/data"
RES_DIR = f"{ROOT}/results"
SEED, N_TRAIN, N_TEST, N_SAMPLES = 0, 4000, 200, 6
os.makedirs(DATA_DIR, exist_ok=True); os.makedirs(RES_DIR, exist_ok=True)

path = snapshot_download("Qwen/Qwen3-8B", local_dir=MODEL_DIR)
model_bytes = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(path) for f in fs
                  if ".cache" not in dp)

raw = load_dataset("b-mc2/sql-create-context", split="train")
ds = raw.shuffle(seed=SEED)
train = ds.select(range(N_TRAIN))
test = ds.select(range(N_TRAIN, N_TRAIN + N_TEST))
raw.save_to_disk(f"{DATA_DIR}/raw")
train.to_json(f"{DATA_DIR}/train.jsonl", force_ascii=False)
test.to_json(f"{DATA_DIR}/test.jsonl", force_ascii=False)

overlap = len({(r["question"], r["context"], r["answer"]) for r in train}
              & {(r["question"], r["context"], r["answer"]) for r in test})

def cell(s):
    return "`" + " ".join(s.split()).replace("|", "\\|").replace("`", "'") + "`"

lines = ["# ตัวอย่างข้อมูล b-mc2/sql-create-context", "",
         f"สับด้วย seed {SEED} · Training Set {len(train):,} ตัวอย่าง · Test Set {len(test):,} ตัวอย่าง "
         f"(จากทั้งหมด {len(raw):,} ตัวอย่าง) · ตัวอย่างด้านล่างคือ {N_SAMPLES} รายการแรกของ Training Set", "",
         "| # | คำถาม (question) | โครงสร้างตาราง (context) | SQL เฉลย (answer) |", "|---|---|---|---|"]
for i in range(N_SAMPLES):
    r = train[i]
    lines.append(f"| {i+1} | {' '.join(r['question'].split()).replace('|', chr(92)+'|')} | {cell(r['context'])} | {cell(r['answer'])} |")
open(f"{RES_DIR}/dataset_samples.md", "w").write("\n".join(lines) + "\n")

info = {"model": "Qwen/Qwen3-8B", "model_dir": MODEL_DIR, "model_gb": round(model_bytes / 1e9, 2),
        "model_files": sorted(f for f in os.listdir(MODEL_DIR) if not f.startswith(".")),
        "dataset": "b-mc2/sql-create-context", "columns": raw.column_names, "total": len(raw),
        "seed": SEED, "train": len(train), "test": len(test), "train_test_overlap": overlap}
json.dump(info, open(f"{RES_DIR}/prepare_info.json", "w"), indent=2, ensure_ascii=False)
print(json.dumps(info, indent=2))
