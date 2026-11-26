"""Shared pieces for Lab4 / 2_data_parallel: prompt format, tokenizing, GPU monitor."""
import json
import os
import subprocess
import threading
import time

MODEL_NAME = "Qwen3-8B"
SYSTEM_PROMPT = (
    "You are a text-to-SQL assistant. Given the table schema and a question, "
    "reply with only the SQL query."
)
EOT = "<|im_end|>"


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_json(path, obj):
    """Atomic JSON write (safe if the job is killed mid-write)."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def build_prompt(tok, row):
    """Chat prompt ending at the assistant turn, with thinking turned off."""
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Schema:\n" + row["context"] + "\n\nQuestion: " + row["question"]},
    ]
    return tok.apply_chat_template(
        msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )


def encode_example(tok, row, max_len):
    """Return (input_ids, labels, full_len). Loss is only on the SQL answer tokens.

    Text longer than max_len tokens is cut at the right end.
    """
    p = tok(build_prompt(tok, row), add_special_tokens=False).input_ids
    a = tok(row["answer"] + EOT, add_special_tokens=False).input_ids
    full = len(p) + len(a)
    ids = (p + a)[:max_len]
    labels = ([-100] * len(p) + a)[:max_len]
    return ids, labels, full


def collate(examples, pad_id, device):
    """Right-pad a list of (ids, labels) to the longest one in the batch."""
    import torch

    n = max(len(e[0]) for e in examples)
    ids = torch.full((len(examples), n), pad_id, dtype=torch.long)
    lab = torch.full((len(examples), n), -100, dtype=torch.long)
    att = torch.zeros((len(examples), n), dtype=torch.long)
    for i, e in enumerate(examples):
        k = len(e[0])
        ids[i, :k] = torch.tensor(e[0])
        lab[i, :k] = torch.tensor(e[1])
        att[i, :k] = 1
    return ids.to(device), att.to(device), lab.to(device)


class GpuMonitor:
    """Poll nvidia-smi in a thread; keeps util and memory samples per GPU."""

    def __init__(self, interval=1.0):
        self.interval = interval
        self.samples = []  # (time, [util per gpu], [mem MiB per gpu])
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self._stop.is_set():
            try:
                out = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=10,
                ).stdout.strip().splitlines()
                rows = [[float(x) for x in line.split(",")] for line in out]
                self.samples.append((time.time(), [r[0] for r in rows], [r[1] for r in rows]))
            except Exception:
                pass
            self._stop.wait(self.interval)

    def start(self):
        self._t.start()
        return self

    def stop(self):
        self._stop.set()
        self._t.join(timeout=15)

    def summary(self, since=0.0):
        s = [x for x in self.samples if x[0] >= since]
        if not s:
            return {"n": 0}
        n_gpu = len(s[0][1])
        return {
            "n": len(s),
            "util_mean": [round(sum(x[1][g] for x in s) / len(s), 1) for g in range(n_gpu)],
            "mem_max_mib": [max(x[2][g] for x in s) for g in range(n_gpu)],
        }
