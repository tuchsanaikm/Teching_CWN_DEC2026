#!/usr/bin/env python3
"""Runs on every node: download model + dataset, shuffle (seed 0), split 4000/200.
Writes /workspace/data/{train,test}.jsonl and /workspace/data/manifest.json (with sha256
so we can prove all nodes hold the identical split)."""
import hashlib, json, os, sys
MODEL = "Qwen/Qwen3-8B"
DATASET = "b-mc2/sql-create-context"
SEED, N_TRAIN, N_TEST = 0, 4000, 200
OUT = "/workspace/data"
MODEL_DIR = "/workspace/models/Qwen3-8B"

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def main():
    os.makedirs(OUT, exist_ok=True)
    from datasets import load_dataset
    ds = load_dataset(DATASET, split="train")
    total = len(ds)
    ds = ds.shuffle(seed=SEED)
    train = ds.select(range(N_TRAIN))
    test = ds.select(range(N_TRAIN, N_TRAIN + N_TEST))
    for name, part in (("train", train), ("test", test)):
        with open(f"{OUT}/{name}.jsonl", "w", encoding="utf-8") as f:
            for r in part:
                f.write(json.dumps({"question": r["question"], "context": r["context"],
                                    "answer": r["answer"]}, ensure_ascii=False, sort_keys=True) + "\n")
    man = {"dataset": DATASET, "dataset_rows": total, "seed": SEED,
           "train_n": len(train), "test_n": len(test),
           "train_sha256": sha(f"{OUT}/train.jsonl"), "test_sha256": sha(f"{OUT}/test.jsonl")}

    if "--no-model" not in sys.argv:
        from huggingface_hub import snapshot_download
        snapshot_download(MODEL, local_dir=MODEL_DIR,
                          allow_patterns=["*.json", "*.safetensors", "*.txt", "tokenizer*", "*.jinja"])
        files = sorted(os.listdir(MODEL_DIR))
        st = [f for f in files if f.endswith(".safetensors")]
        size = sum(os.path.getsize(os.path.join(MODEL_DIR, f)) for f in st)
        # light check: config + tokenizer load, and every shard listed in the index exists
        from transformers import AutoConfig, AutoTokenizer
        cfg = AutoConfig.from_pretrained(MODEL_DIR)
        tok = AutoTokenizer.from_pretrained(MODEL_DIR)
        idx = json.load(open(f"{MODEL_DIR}/model.safetensors.index.json"))
        need = sorted(set(idx["weight_map"].values()))
        man.update({"model": MODEL, "model_dir": MODEL_DIR, "model_weight_files": len(st),
                    "model_weight_gb": round(size / 1e9, 2), "shards_complete": need == st,
                    "hidden_size": cfg.hidden_size, "num_layers": cfg.num_hidden_layers,
                    "vocab": len(tok)})
    import torch
    man.update({"torch": torch.__version__, "cuda": torch.version.cuda,
                "gpus": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]})
    json.dump(man, open(f"{OUT}/manifest.json", "w"), indent=1)
    print("MANIFEST " + json.dumps(man))

if __name__ == "__main__":
    main()
