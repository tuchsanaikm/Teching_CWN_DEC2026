#!/usr/bin/env python3
"""Merge Qwen/Qwen3-VL-2B-Instruct with ReceiptDesk LoRA adapter (lora_g2) for zero-overhead vLLM serving."""
import os, json, time, torch
from pathlib import Path
from transformers import AutoProcessor
try:
    from transformers import AutoModelForImageTextToText as VLMClass
except ImportError:
    from transformers import AutoModelForVision2Seq as VLMClass
from peft import PeftModel

BASE = "Qwen/Qwen3-VL-2B-Instruct"
LORA_DIR = Path("/workspace/receipt_lb/lora_g2")
OUT_DIR = Path("/workspace/receipt_lb/model_merged")

if (OUT_DIR / "config.json").exists() and list(OUT_DIR.glob("*.safetensors")):
    print("Merged model already exists at", OUT_DIR)
    raise SystemExit(0)

t0 = time.time()
print("Loading base model:", BASE, flush=True)
model = VLMClass.from_pretrained(BASE, torch_dtype=torch.bfloat16, device_map="cpu")
proc = AutoProcessor.from_pretrained(BASE)

# Patch base_model_name_or_path in adapter_config.json copy if needed
cfg_path = LORA_DIR / "adapter_config.json"
cfg = json.loads(cfg_path.read_text())
if cfg.get("base_model_name_or_path") != BASE:
    cfg["base_model_name_or_path"] = BASE
    cfg_path.write_text(json.dumps(cfg, indent=2))

print("Applying LoRA from:", LORA_DIR, flush=True)
model = PeftModel.from_pretrained(model, str(LORA_DIR))
model = model.merge_and_unload()

OUT_DIR.mkdir(parents=True, exist_ok=True)
print("Saving merged model to:", OUT_DIR, flush=True)
model.save_pretrained(str(OUT_DIR), safe_serialization=True)
proc.save_pretrained(str(OUT_DIR))
print(f"MERGED OK in {time.time() - t0:.1f}s", flush=True)
