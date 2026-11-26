#!/usr/bin/env python3
"""Runs ON a node: download model + dataset, shuffle (seed 0), split, save.

Output (under /workspace/lab5_dp):
  model/                 Qwen/Qwen3-8B snapshot
  data/train.jsonl       4,000 examples
  data/test.jsonl        200 examples
  prepare_report.json    counts, checksums, revisions, GPU info
The split is deterministic (same dataset revision + seed 0), and the sha256 of each
file is reported so the two nodes can be compared.
"""
import hashlib, json, os, subprocess, sys, time

MODEL_ID = "Qwen/Qwen3-8B"
DATASET_ID = "b-mc2/sql-create-context"
SEED, N_TRAIN, N_TEST = 0, 4000, 200
ROOT = "/workspace/lab5_dp"
MODEL_DIR, DATA_DIR = f"{ROOT}/model", f"{ROOT}/data"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_jsonl(ds, path):
    with open(path, "w", encoding="utf-8") as f:
        for row in ds:
            f.write(json.dumps({"question": row["question"], "context": row["context"],
                                "answer": row["answer"]}, ensure_ascii=False) + "\n")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
    from huggingface_hub import HfApi, snapshot_download
    from datasets import load_dataset
    import torch

    rep = {"model_id": MODEL_ID, "dataset_id": DATASET_ID, "seed": SEED}
    api = HfApi()
    rep["model_revision"] = api.model_info(MODEL_ID).sha
    rep["dataset_revision"] = api.dataset_info(DATASET_ID).sha

    t = time.time()
    snapshot_download(MODEL_ID, revision=rep["model_revision"], local_dir=MODEL_DIR)
    rep["model_download_seconds"] = round(time.time() - t, 1)
    files = sorted(os.listdir(MODEL_DIR))
    weights = [f for f in files if f.endswith(".safetensors")]
    rep["model_files"] = len([f for f in files if os.path.isfile(f"{MODEL_DIR}/{f}")])
    rep["model_weight_files"] = len(weights)
    rep["model_weight_bytes"] = sum(os.path.getsize(f"{MODEL_DIR}/{f}") for f in weights)
    cfg = json.load(open(f"{MODEL_DIR}/config.json"))
    rep["model_config"] = {k: cfg.get(k) for k in ("model_type", "num_hidden_layers",
                                                    "hidden_size", "vocab_size")}
    # proves the weights are complete without loading 16 GB into RAM
    from safetensors import safe_open
    n_params = 0
    for w in weights:
        with safe_open(f"{MODEL_DIR}/{w}", framework="pt") as sf:
            for k in sf.keys():
                n = 1
                for d in sf.get_slice(k).get_shape():
                    n *= d
                n_params += n
    rep["model_params"] = n_params
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODEL_DIR)
    rep["tokenizer_check"] = len(tok("SELECT COUNT(*) FROM head WHERE age > 56")["input_ids"])

    ds = load_dataset(DATASET_ID, revision=rep["dataset_revision"], split="train")
    rep["dataset_total"] = len(ds)
    rep["dataset_columns"] = ds.column_names
    ds = ds.shuffle(seed=SEED)
    train = ds.select(range(N_TRAIN))
    test = ds.select(range(N_TRAIN, N_TRAIN + N_TEST))
    write_jsonl(train, f"{DATA_DIR}/train.jsonl")
    write_jsonl(test, f"{DATA_DIR}/test.jsonl")
    for name in ("train", "test"):
        p = f"{DATA_DIR}/{name}.jsonl"
        rep[f"{name}_count"] = sum(1 for _ in open(p, encoding="utf-8"))
        rep[f"{name}_sha256"] = sha256(p)
    tr = {l for l in open(f"{DATA_DIR}/train.jsonl", encoding="utf-8")}
    te = {l for l in open(f"{DATA_DIR}/test.jsonl", encoding="utf-8")}
    rep["train_test_identical_rows"] = len(tr & te)

    rep["torch"] = torch.__version__
    rep["torch_cuda"] = torch.version.cuda
    rep["cuda_available"] = torch.cuda.is_available()
    rep["gpus"] = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
    rep["disk_free_gb"] = round(os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize / 1e9, 1)
    rep["nproc"] = os.cpu_count()
    rep["hostname"] = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()
    json.dump(rep, open(f"{ROOT}/prepare_report.json", "w"), indent=2)
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    sys.exit(main())
