"""ส่วนที่ train.py และ eval.py ใช้ร่วมกัน: prompt, การโหลดโมเดลแบบแบ่ง 2 GPU, ตัววัด GPU"""
import json
import subprocess
import threading
import time

import torch

ROOT = "/workspace/lab4_mp"
MODEL_DIR = f"{ROOT}/models/Qwen3-8B"
TRAIN_FILE = f"{ROOT}/data/train.jsonl"
TEST_FILE = f"{ROOT}/data/test.jsonl"
RESULT_DIR = f"{ROOT}/results"
CKPT_DIR = f"{ROOT}/ckpt"

MAX_LEN = 256          # ข้อความยาวไม่เกิน 256 token
SEED = 0
LORA_R, LORA_ALPHA = 8, 16
LORA_TARGETS = ["q_proj", "v_proj"]

SYSTEM = ("You are a text-to-SQL assistant. Given the table schema and a question, "
          "answer with a single SQL query only.")


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_tokenizer():
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODEL_DIR)
    if tok.pad_token_id is None:
        tok.pad_token = "<|endoftext|>"
    return tok


def prompt_text(tok, row):
    """ข้อความถึงจุดที่โมเดลต้องเริ่มตอบ (ปิด thinking)"""
    msgs = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Schema:\n{row['context']}\n\nQuestion: {row['question']}"},
    ]
    return tok.apply_chat_template(
        msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)


def encode_example(tok, row):
    """คืน (input_ids, labels) ยาวไม่เกิน MAX_LEN; คิด loss เฉพาะส่วนคำตอบ SQL"""
    p = tok(prompt_text(tok, row), add_special_tokens=False)["input_ids"]
    a = tok(row["answer"] + "<|im_end|>", add_special_tokens=False)["input_ids"]
    ids = (p + a)[:MAX_LEN]
    labels = ([-100] * len(p) + a)[:MAX_LEN]
    return ids, labels


def collate(tok, examples, device):
    """pad ด้านขวาให้ยาวเท่าตัวที่ยาวที่สุดใน batch"""
    n = max(len(i) for i, _ in examples)
    ids = torch.full((len(examples), n), tok.pad_token_id, dtype=torch.long)
    lab = torch.full((len(examples), n), -100, dtype=torch.long)
    att = torch.zeros((len(examples), n), dtype=torch.long)
    for k, (i, l) in enumerate(examples):
        ids[k, :len(i)] = torch.tensor(i)
        lab[k, :len(l)] = torch.tensor(l)
        att[k, :len(i)] = 1
    return ids.to(device), att.to(device), lab.to(device)


def split_device_map(n_layers):
    """Model Parallelism: โมเดลชุดเดียว ครึ่งแรกอยู่ GPU 0 ครึ่งหลังอยู่ GPU 1"""
    half = n_layers // 2
    dm = {"model.embed_tokens": 0, "model.rotary_emb": 0}
    for i in range(n_layers):
        dm[f"model.layers.{i}"] = 0 if i < half else 1
    dm["model.norm"] = 1
    dm["lm_head"] = 1
    return dm


def load_base_model():
    """โหลด Qwen3-8B แบบ bf16 ชุดเดียว แบ่งลง GPU 2 ใบ"""
    from transformers import AutoConfig, AutoModelForCausalLM
    assert torch.cuda.device_count() >= 2, "ต้องมี GPU 2 ใบ"
    cfg = AutoConfig.from_pretrained(MODEL_DIR)
    dm = split_device_map(cfg.num_hidden_layers)
    try:
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_DIR, dtype=torch.bfloat16, device_map=dm)
    except Exception as e:  # รุ่นที่ไม่มี rotary_emb เป็น module
        if "rotary_emb" not in str(e):
            raise
        dm.pop("model.rotary_emb")
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_DIR, dtype=torch.bfloat16, device_map=dm)
    model.config.use_cache = False
    assert not getattr(model, "is_gradient_checkpointing", False)
    return model


def add_lora(model):
    from peft import LoraConfig, get_peft_model
    cfg = LoraConfig(r=LORA_R, lora_alpha=LORA_ALPHA, lora_dropout=0.0, bias="none",
                     target_modules=LORA_TARGETS, task_type="CAUSAL_LM")
    return get_peft_model(model, cfg)


def layer_placement(model):
    """สรุปว่าส่วนไหนของโมเดลอยู่ GPU ใบไหน (อ่านจาก device จริงของ parameter)"""
    place = {}
    for name, p in model.named_parameters():
        if "lora_" in name:
            continue
        name = name.replace("base_model.model.", "")
        parts = name.split(".")
        key = ".".join(parts[:3]) if parts[1] == "layers" else ".".join(parts[:2])
        if parts[0] == "lm_head":
            key = "lm_head"
        d = place.setdefault(key, {"device": str(p.device), "params": 0})
        assert d["device"] == str(p.device), f"{key} คร่อม 2 device"
        d["params"] += p.numel()
    out = {}
    for dev in sorted({v["device"] for v in place.values()}):
        keys = [k for k, v in place.items() if v["device"] == dev]
        layers = sorted(int(k.split(".")[2]) for k in keys if ".layers." in k)
        out[dev] = {
            "layers": f"{layers[0]}-{layers[-1]}" if layers else "",
            "n_layers": len(layers),
            "others": [k for k in keys if ".layers." not in k],
            "params": sum(place[k]["params"] for k in keys),
            "weights_gb": round(sum(place[k]["params"] for k in keys) * 2 / 1e9, 2),
        }
    return out


def vram_peaks():
    """VRAM สูงสุดของแต่ละใบ (MiB) ตามที่ PyTorch จองจริง"""
    return {
        f"gpu{i}": {
            "allocated_mib": round(torch.cuda.max_memory_allocated(i) / 2**20),
            "reserved_mib": round(torch.cuda.max_memory_reserved(i) / 2**20),
        } for i in range(torch.cuda.device_count())
    }


class GpuMonitor:
    """อ่าน nvidia-smi ทุก 1 วินาที เก็บ util และ memory.used ของแต่ละใบ"""

    def __init__(self):
        self.samples = []  # (t, [util...], [mem...])
        self.active = False
        self._stop = False
        self._th = threading.Thread(target=self._run, daemon=True)
        self._th.start()

    def _run(self):
        cmd = ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used",
               "--format=csv,noheader,nounits"]
        while not self._stop:
            try:
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout
                rows = [[int(x) for x in l.split(",")] for l in out.strip().splitlines()]
                if self.active:
                    self.samples.append(
                        (time.time(), [r[0] for r in rows], [r[1] for r in rows]))
            except Exception:
                pass
            time.sleep(1.0)

    def reset(self):
        self.samples = []

    def summary(self):
        if not self.samples:
            return {}
        n = len(self.samples[0][1])
        return {
            f"gpu{i}": {
                "util_mean": round(sum(s[1][i] for s in self.samples) / len(self.samples), 1),
                "util_max": max(s[1][i] for s in self.samples),
                "smi_mem_max_mib": max(s[2][i] for s in self.samples),
            } for i in range(n)
        } | {"n_samples": len(self.samples)}

    def stop(self):
        self._stop = True
