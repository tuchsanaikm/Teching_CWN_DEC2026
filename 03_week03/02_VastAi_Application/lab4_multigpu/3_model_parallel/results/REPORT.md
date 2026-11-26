# Lab 4 · Model Parallelism — Qwen3-8B + LoRA (Text-to-SQL)

เครื่อง: Vast.ai instance <id> (ป้าย `vapp-lab4-mp`) · RTX 3090 24 GB × 2 · $0.407/ชม.
โมเดล Qwen/Qwen3-8B bf16 ชุดเดียว แบ่งลง 2 GPU · ปิด thinking · ไม่ใช้ Gradient Checkpointing
LoRA r 8 · alpha 16 · q_proj + v_proj (เทรนได้ 3,833,856 พารามิเตอร์) · lr 2e-4 (linear decay) · seed 0 · ยาวไม่เกิน 256 token
ข้อมูล: b-mc2/sql-create-context · Train 4,000 · Test 200

## Layer ไหนอยู่ใบไหน

| GPU | ส่วนของโมเดล | น้ำหนัก |
|---|---|---|
| GPU 0 | embed_tokens + Layer 0–17 (18 ชั้น) | 8.19 GB |
| GPU 1 | Layer 18–35 (18 ชั้น) + norm + lm_head | 8.19 GB |

## หา batch ใหญ่สุด (อย่างละ 3 step ด้วยตัวอย่างที่ยาวที่สุด = 256 token)

VRAM สูงสุด = ค่า memory.used จาก nvidia-smi (ในวงเล็บคือ max_memory_allocated ของ PyTorch)

| batch | ผล | GPU 0 (MiB) | GPU 1 (MiB) | วินาที/step |
|---|---|---|---|---|
| 1 | ผ่าน | 9,008 (8,645) | 9,462 (9,027) | 0.27 |
| 2 | ผ่าน | 9,816 (9,436) | 10,720 (10,198) | 0.36 |
| 4 | ผ่าน | 11,738 (11,017) | 13,246 (12,540) | 0.70 |
| 8 | ผ่าน | 14,682 (14,180) | 18,280 (17,224) | 1.36 |
| 16 | Out of Memory ที่ GPU 1 ตั้งแต่ step แรก | 19,980 (19,551) | 23,416 (23,035) | – |

batch ที่ใช้เทรน: **8** (500 step/Epoch รวม 1,500 step)

## ความเร็วและ GPU util ตอนเทรน (batch 8)

| Epoch | วินาที/step | ตัวอย่าง/วินาที | util GPU 0 | util GPU 1 | เวลา (วินาที) |
|---|---|---|---|---|---|
| 1 | 0.791 | 10.12 | 44.7% | 53.4% | 396 |
| 2 | 0.791 | 10.11 | 45.9% | 53.2% | 396 |
| 3 | 0.785 | 10.20 | 49.0% | 48.7% | 393 |
| เฉลี่ย | 0.789 | 10.14 | 46.5% | 51.8% | รวม 1,184 |

## loss และ Exact Match (Test Set 200 ตัวอย่าง, greedy)

| โมเดล | train loss | test loss | Exact Match | EM แบบผ่อนปรน |
|---|---|---|---|---|
| Base | – | 1.914 | 0.0% (0/200) | 54.5% |
| Epoch 1 | 0.0876 | 0.0580 | 70.0% (140/200) | 72.5% |
| Epoch 2 | 0.0305 | 0.0506 | 77.5% (155/200) | 79.5% |
| Epoch 3 | 0.0168 | 0.0529 | 77.0% (154/200) | 79.5% |

- Exact Match = ข้อความตรงกับเฉลยทุกตัวอักษร (ยุบช่องว่างเท่านั้น)
- แบบผ่อนปรน = ไม่สนตัวพิมพ์ ชนิดเครื่องหมายคำพูด และ `;` ท้าย — Base ได้ 0% แบบเข้มเพราะใช้ `'...'` และตัวพิมพ์ใหญ่ ต่างจากเฉลยที่ใช้ `"..."` ตัวพิมพ์เล็ก
- train loss = ค่าเฉลี่ยของ loss ทุก step ใน Epoch นั้น

## ข้อสังเกต

- GPU 1 ใช้ VRAM มากกว่า GPU 0 เพราะ logits ขนาด vocab 151,936 และการคิด loss อยู่ที่ใบนี้ จึงเป็นใบที่ OOM ก่อน
- util ราว 50% ต่อใบ เพราะ 2 ใบทำงานสลับกัน (forward 0→1, backward 1→0) ไม่ได้ทำพร้อมกัน
- ตอนเทรนจริง PyTorch จอง VRAM (reserved) สูงกว่าตอน probe เพราะความยาว batch เปลี่ยนไปมา: allocated สูงสุด 14,630 / 17,674 MiB แต่ nvidia-smi เห็นสูงสุด 18,640 / 23,826 MiB
- ตัวอย่าง Train 1 รายการยาว 320 token ถูกตัดเหลือ 256

## ไฟล์

`code/common.py` `code/train.py` `code/eval.py` `code/run_all.sh` · ผลดิบใน `results/` (probe_b*.json, train_summary.json, train_steps.jsonl, eval_*.json, pred_*.jsonl, adapters/)

## สรุปกราฟและค่าใช้จ่าย (code/report.py)

- ผลดิบจากเครื่องอยู่ที่ `results/raw/` · ตัวเลขรวมที่ `results/metrics.json` · กราฟที่ `results/images/` (`vram_vs_batch.png` `gpu_util.png` `loss.png` `exact_match.png`)
- เงินต่อ 1,000 ตัวอย่าง = ราคา/ชม. ÷ 3600 ÷ ตัวอย่าง/วินาที × 1000 (ดูค่าใน `metrics.json` → `usd_per_1000_samples`)
- ค่าใช้จ่ายจริงของเครื่องและอายุเครื่องอยู่ใน `metrics.json` → `actual_cost` (หลักฐาน: `raw/billing.json`, `raw/instance_final.json`)
- เครื่องป้าย `vapp-lab4-mp` ถูกลบแล้ว
