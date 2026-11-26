"""Shared pieces for train.py and eval.py: prompt format, tokenisation,
and the 4-GPU model-parallel placement of Qwen3-8B (one model, layers split in 4)."""
import glob, json, os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "Qwen/Qwen3-8B"
MAX_LEN = 256          # fixed: at most 256 tokens per training text
SEED = 0
LORA = dict(r=8, lora_alpha=16, target_modules=["q_proj", "v_proj"], lora_dropout=0.0,
            bias="none", task_type="CAUSAL_LM")
SYSTEM = ("You are a text-to-SQL assistant. Given the table schema and a question, "
          "answer with one SQL query only.")


def model_path():
    hits = glob.glob(os.path.expanduser("/workspace/hf/hub/models--Qwen--Qwen3-8B/snapshots/*"))
    return hits[0] if hits else MODEL


def read_jsonl(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def load_tokenizer():
    tok = AutoTokenizer.from_pretrained(model_path())
    if tok.pad_token_id is None:
        tok.pad_token = "<|endoftext|>"
    return tok


def prompt_text(tok, row):
    """Chat prompt up to the start of the assistant answer, thinking turned off."""
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Schema:\n{row['context']}\n\nQuestion: {row['question']}"}]
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                   enable_thinking=False)


def encode_example(tok, row, max_len=MAX_LEN):
    """Returns (input_ids, labels). Loss is taken only on the SQL answer + <|im_end|>.
    Texts longer than max_len tokens are cut on the right."""
    p = tok(prompt_text(tok, row), add_special_tokens=False)["input_ids"]
    a = tok(row["answer"] + "<|im_end|>", add_special_tokens=False)["input_ids"]
    ids = (p + a)[:max_len]
    labels = ([-100] * len(p) + a)[:max_len]
    return ids, labels


def collate(tok, examples):
    """Right-pad a list of (ids, labels) to the longest one in the batch."""
    n = max(len(i) for i, _ in examples)
    ids = torch.full((len(examples), n), tok.pad_token_id, dtype=torch.long)
    lab = torch.full((len(examples), n), -100, dtype=torch.long)
    att = torch.zeros((len(examples), n), dtype=torch.long)
    for k, (i, l) in enumerate(examples):
        ids[k, :len(i)] = torch.tensor(i)
        lab[k, :len(l)] = torch.tensor(l)
        att[k, :len(i)] = 1
    return {"input_ids": ids, "attention_mask": att, "labels": lab}


def build_device_map(n_layers, n_gpus=4):
    """Model parallelism: split the decoder layers into n_gpus equal consecutive parts,
    GPU 0 -> GPU n-1. Embedding sits with the first part, final norm + LM head with the last."""
    assert n_layers % n_gpus == 0, "layers must split evenly"
    per = n_layers // n_gpus
    dmap = {"model.embed_tokens": 0, "model.rotary_emb": 0,
            "model.norm": n_gpus - 1, "lm_head": n_gpus - 1}
    for i in range(n_layers):
        dmap[f"model.layers.{i}"] = i // per
    return dmap


def load_base(n_gpus=4):
    from transformers import AutoConfig
    path = model_path()
    cfg = AutoConfig.from_pretrained(path)
    dmap = build_device_map(cfg.num_hidden_layers, n_gpus)
    model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, device_map=dmap)
    return model


def placement(model):
    """Where every block really is, read back from the loaded parameters."""
    base = model.get_base_model() if hasattr(model, "get_base_model") else model
    dec = base.model
    layers = {}
    for i, layer in enumerate(dec.layers):
        devs = {p.device.index for p in layer.parameters()}
        assert len(devs) == 1, f"layer {i} spans {devs}"
        layers[i] = devs.pop()
    per_gpu = {}
    for i, d in layers.items():
        per_gpu.setdefault(d, []).append(i)
    return {
        "embed_tokens": dec.embed_tokens.weight.device.index,
        "final_norm": dec.norm.weight.device.index,
        "lm_head": base.lm_head.weight.device.index,
        "layers_per_gpu": {f"gpu{d}": f"{min(v)}-{max(v)} ({len(v)} layers)" for d, v in sorted(per_gpu.items())},
        "layer_to_gpu": layers,
    }


def gpu_mem_gb():
    """Peak allocated / reserved by PyTorch per GPU, in GB."""
    out = []
    for d in range(torch.cuda.device_count()):
        out.append({"gpu": d,
                    "peak_alloc_gb": round(torch.cuda.max_memory_allocated(d) / 2**30, 2),
                    "peak_reserved_gb": round(torch.cuda.max_memory_reserved(d) / 2**30, 2)})
    return out


def sync_all():
    for d in range(torch.cuda.device_count()):
        torch.cuda.synchronize(d)
