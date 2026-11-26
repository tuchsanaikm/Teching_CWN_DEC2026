"""Lab 4 / 1_single_gpu: shared pieces for train.py and eval.py.

Fixed settings: Qwen/Qwen3-8B in bf16, thinking off, no gradient checkpointing,
LoRA r=8 alpha=16 on q_proj + v_proj, max 256 tokens per text.
"""
import json
import os
import subprocess
import threading
import time

import torch

ROOT = os.environ.get("LAB_ROOT", "/workspace/lab4")
MODEL_DIR = os.path.join(ROOT, "models", "Qwen3-8B")
DATA_DIR = os.path.join(ROOT, "data")
RESULTS_DIR = os.path.join(ROOT, "results")
RUN_DIR = os.path.join(ROOT, "run")  # checkpoints / adapters

MAX_LEN = 256
SEED = 0
LORA_R = 8
LORA_ALPHA = 16
LORA_TARGETS = ["q_proj", "v_proj"]

SYSTEM_PROMPT = (
    "You are a text-to-SQL assistant. Given the table schema and a question, "
    "answer with one SQL query only. No explanation, no markdown."
)


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_json(path, obj):
    """Atomic JSON write (safe if the job is killed mid-write)."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def load_tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(MODEL_DIR)


def load_base_model():
    """Whole model on the single GPU, bf16, gradient checkpointing left off."""
    from transformers import AutoModelForCausalLM

    model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, dtype=torch.bfloat16)
    model.to("cuda:0")
    return model


def add_lora(model):
    from peft import LoraConfig, get_peft_model

    cfg = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        target_modules=LORA_TARGETS,
        lora_dropout=0.0,
        bias="none",
        task_type="CAUSAL_LM",
    )
    # adapter weights are kept in fp32 (peft default); forward runs under bf16 autocast
    return get_peft_model(model, cfg)


def build_prompt(tok, row):
    """Chat prompt ending at the assistant turn, thinking disabled."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Schema:\n{row['context']}\n\nQuestion: {row['question']}"},
    ]
    return tok.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )


def encode_example(tok, row, max_len=MAX_LEN):
    """prompt + answer + <|im_end|>, cut to max_len tokens. Loss only on the answer part."""
    p_ids = tok(build_prompt(tok, row), add_special_tokens=False)["input_ids"]
    a_ids = tok(row["answer"] + "<|im_end|>", add_special_tokens=False)["input_ids"]
    full_len = len(p_ids) + len(a_ids)
    ids = (p_ids + a_ids)[:max_len]
    labels = ([-100] * len(p_ids) + a_ids)[:max_len]
    return {"input_ids": ids, "labels": labels, "full_len": full_len, "prompt_len": len(p_ids)}


def collate(examples, pad_id, device="cuda:0"):
    """Right-pad a list of encoded examples to the longest one in the batch."""
    n = max(len(e["input_ids"]) for e in examples)
    ids = torch.full((len(examples), n), pad_id, dtype=torch.long)
    labels = torch.full((len(examples), n), -100, dtype=torch.long)
    mask = torch.zeros((len(examples), n), dtype=torch.long)
    for i, e in enumerate(examples):
        k = len(e["input_ids"])
        ids[i, :k] = torch.tensor(e["input_ids"])
        labels[i, :k] = torch.tensor(e["labels"])
        mask[i, :k] = 1
    return ids.to(device), mask.to(device), labels.to(device)


class GpuMonitor:
    """Samples GPU utilisation and used memory once a second with nvidia-smi."""

    def __init__(self, interval=1.0):
        self.interval = interval
        self.util = []
        self.mem = []
        self._stop = threading.Event()
        self._thread = None

    def _run(self):
        while not self._stop.is_set():
            try:
                out = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used",
                     "--format=csv,noheader,nounits", "-i", "0"],
                    capture_output=True, text=True, timeout=10,
                ).stdout.strip()
                u, m = [float(x) for x in out.split(",")]
                self.util.append(u)
                self.mem.append(m)
            except Exception:
                pass
            self._stop.wait(self.interval)

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=15)

    def take(self):
        """Return (mean util %, max used MiB, n samples) since the last take() and reset."""
        u, m = self.util, self.mem
        self.util, self.mem = [], []
        if not u:
            return None, None, 0
        return sum(u) / len(u), max(m), len(u)


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")
