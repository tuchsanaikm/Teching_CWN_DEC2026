"""Shared pieces of train.py and eval.py: paths, prompt format, tokenisation, GPU monitor."""
import json
import subprocess
import threading
import time

ROOT = "/workspace/lab4_dp4"
MODEL_DIR = f"{ROOT}/models/Qwen3-8B"
TRAIN_FILE = f"{ROOT}/data/train.jsonl"
TEST_FILE = f"{ROOT}/data/test.jsonl"
MAX_LEN = 256
END = "<|im_end|>"
SYSTEM = ("You are a text-to-SQL assistant. Given the table schema and a question, "
          "reply with exactly one SQL query and nothing else.")


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def prompt_text(tok, ex):
    """Chat prompt up to the start of the assistant answer, thinking disabled."""
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Schema:\n{ex['context']}\n\nQuestion: {ex['question']}"}]
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)


def encode(tok, ex, max_len=MAX_LEN):
    """Token ids of prompt + answer, cut to max_len. Loss is taken on the answer tokens only."""
    p = tok(prompt_text(tok, ex), add_special_tokens=False).input_ids
    a = tok(ex["answer"] + END, add_special_tokens=False).input_ids
    ids = (p + a)[:max_len]
    labels = ([-100] * len(p) + a)[:max_len]
    return {"input_ids": ids, "labels": labels, "full_len": len(p) + len(a), "prompt_len": len(p)}


def collate(batch, pad_id):
    """Right-pad to the longest sequence of the batch."""
    import torch
    n = max(len(b["input_ids"]) for b in batch)
    ids = torch.full((len(batch), n), pad_id, dtype=torch.long)
    lab = torch.full((len(batch), n), -100, dtype=torch.long)
    att = torch.zeros((len(batch), n), dtype=torch.long)
    for i, b in enumerate(batch):
        k = len(b["input_ids"])
        ids[i, :k] = torch.tensor(b["input_ids"])
        lab[i, :k] = torch.tensor(b["labels"])
        att[i, :k] = 1
    return {"input_ids": ids, "attention_mask": att, "labels": lab}


class GpuMonitor:
    """Polls nvidia-smi once a second and keeps (time, [util%], [memory MiB]) for every GPU."""

    def __init__(self, interval_ms=1000):
        self.samples = []
        self.lock = threading.Lock()
        self.proc = subprocess.Popen(
            ["nvidia-smi", "--query-gpu=index,utilization.gpu,memory.used",
             "--format=csv,noheader,nounits", "-lms", str(interval_ms)],
            stdout=subprocess.PIPE, text=True)
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        cur = {}
        for line in self.proc.stdout:
            try:
                i, u, m = [int(x) for x in line.split(",")]
            except ValueError:
                continue
            if i in cur:  # index repeats: one full sweep over the GPUs is complete
                self._push(cur)
                cur = {}
            cur[i] = (u, m)

    def _push(self, cur):
        ks = sorted(cur)
        with self.lock:
            self.samples.append((time.time(), [cur[k][0] for k in ks], [cur[k][1] for k in ks]))

    def window(self, t0, t1=None):
        """Mean util and peak memory of every GPU between two wall-clock times."""
        t1 = t1 or time.time()
        with self.lock:
            s = [x for x in self.samples if t0 <= x[0] <= t1]
        if not s:
            return {"n": 0, "util_mean": [], "mem_peak_mib": []}
        n = len(s[0][1])
        return {"n": len(s),
                "util_mean": [round(sum(x[1][g] for x in s) / len(s), 1) for g in range(n)],
                "mem_peak_mib": [max(x[2][g] for x in s) for g in range(n)]}

    def stop(self):
        self.proc.terminate()
