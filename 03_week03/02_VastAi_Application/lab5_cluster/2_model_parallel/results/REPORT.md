# LAB 5.2 — Model Parallelism บนคลัสเตอร์ 2 Node (Qwen3-8B → SQL)

เครื่อง: Node 1 `vapp-lab5-mp-1` (FR, 2× RTX 3090 24 GB) · Node 2 `vapp-lab5-mp-2` (CZ, 2× RTX 3090 24 GB)
ข้อมูล: b-mc2/sql-create-context · Train 4,000 · Test 200 (seed 0)

## ค่าที่ตรึง (ไม่ได้เปลี่ยน)
Qwen/Qwen3-8B bf16 · thinking ปิด · ไม่ใช้ Gradient Checkpointing · LoRA r 8 / alpha 16 ที่ q_proj + v_proj
(3,833,856 พารามิเตอร์) · lr 2e-4 · seed 0 · ≤ 256 token · 2 Epoch · batch 8 ต่อ Node

ค่าที่ต้องเลือกเอง (โจทย์ไม่ได้กำหนด): AdamW, weight decay 0, lr คงที่, ไม่มี dropout, loss คิดเฉพาะ token ของคำตอบ SQL

## ผลสรุป

| รายการ | ค่า |
|---|---|
| batch ต่อ Node / รวม | 8 / 16 (250 step ต่อ Epoch, รวม 500 step) |
| Layer บน GPU 0 (ทั้ง 2 Node) | embed_tokens + layer 0–17 |
| Layer บน GPU 1 (ทั้ง 2 Node) | layer 18–35 + norm + lm_head |
| VRAM สูงสุด Node 1 (GPU 0 / GPU 1) | 13,907 / 14,212 MiB (torch) · 14,312 / 14,694 MiB (nvidia-smi) |
| VRAM สูงสุด Node 2 (GPU 0 / GPU 1) | 13,907 / 14,224 MiB (torch) · 14,332 / 14,696 MiB (nvidia-smi) |
| วินาทีต่อ step (เฉลี่ย) | 3.27 (มัธยฐาน 2.61 · p10 1.85 · p90 4.32) |
| – เวลาคำนวณบน GPU | 0.70 (Node 1 0.69 · Node 2 0.71) |
| – เวลาส่งและรอ Gradient | 2.56 (Node 1 2.58 · Node 2 2.55; มัธยฐาน 1.90 / 1.83) = 78% ของ step |
| ขนาด Gradient ต่อ step ต่อ Node | ขาขึ้น 7.67 MB (bf16 ไม่สูญเสีย) + ขาลง (ค่าเฉลี่ย float32) 15.34 MB = 23.0 MB |
| ตัวอย่างต่อวินาที | 4.90 (16 ตัวอย่าง / 3.27 s) |
| GPU util เฉลี่ย Node 1 (GPU 0 / GPU 1) | 10.6% / 10.8% |
| GPU util เฉลี่ย Node 2 (GPU 0 / GPU 1) | 10.8% / 9.4% |
| น้ำหนัก LoRA 2 Node หลัง Epoch 1 / 2 | เท่ากันทุกบิต (max \|diff\| = 0, sha256 ตรงกัน) ทั้ง 2 Epoch |

| โมเดล | train loss (เฉลี่ยทั้ง Epoch) | test loss | Exact Match (200 ข้อ) |
|---|---|---|---|
| Base | 1.661 (step แรก) | 1.915 | 1.5% (3/200) |
| หลัง Epoch 1 | 0.121 | 0.0604 | 69.5% (139/200) |
| หลัง Epoch 2 | 0.038 | 0.0544 | 74.0% (148/200) |

Exact Match: เทียบข้อความหลังยุบช่องว่างและตัด `;` ท้ายคำสั่ง (ตรงตัวพิมพ์เล็กใหญ่)
Base ได้ต่ำเพราะตอบด้วย `'...'` (190/200 ข้อ) ขณะที่เฉลยใช้ `"..."` และมักคงตัวพิมพ์ของค่าตามคำถาม

## ข้อสังเกต
- GPU util ต่ำ (~10%) เพราะ 78% ของแต่ละ step คือการส่งและรอ Gradient ข้ามประเทศ และใน 0.7 s ที่คำนวณ
  GPU 2 ใบทำงานสลับกัน (ครึ่งแรก → ครึ่งหลัง) ไม่ได้ทำพร้อมกัน
- เวลาส่งขึ้นกับเครือข่ายมาก: step 0–149 ส่ง+รอเฉลี่ย 3.28 s · step 150–499 (หลัง host ของ Node 1 reboot) 2.24 s
- Node 2 เป็นฝ่ายมาถึงทีหลังทุก step (500/500) → Node 1 รอ Node 2 ตลอด

## เหตุการณ์ระหว่างรัน (ควรรู้)
1. **ลอง 3 step (batch ยาวสุด 256 token ปนสั้น): ไม่ Out of Memory** — สูงสุด 13.9 / 14.3 GB จาก 24 GB
   โค้ดลดหน่วยความจำไว้ตั้งแต่แรก: คำนวณ lm_head เฉพาะตำแหน่งที่มี label และทางเดิน LoRA คำนวณเป็น bf16
   (Node 2 ในการลองนี้ batch ยาวสุด 206 token เพราะตัวอย่าง 256 token มีตัวเดียวและอยู่ในครึ่งของ Node 1)
2. **รันแรก (เก็บไว้ที่ `run_v1_single_stream/`) ถูกยกเลิกที่ ~step 117**: ใช้ 1 connection ต่อ Node แล้ว
   connection ค้างช้ามาก (บาง step รอ 92 s) → เขียนการส่งใหม่เป็น 4 connection ต่อ Node เข้า port เดียวกัน
   + heartbeat + ตัดแล้วต่อใหม่ถ้าไม่มีข้อมูลไหล 8 s แล้วเริ่มเทรนใหม่จาก step 0
3. **Host ของ Node 1 หลุด (Vast แจ้ง offline) แล้ว reboot เองที่ ~step 162–168 ของรันจริง** (~5 นาที)
   ทั้งสอง worker ต่อจาก checkpoint step 150 (ต้องสั่งเปิดโปรแกรมกลาง + worker Node 1 ใหม่ และ kill worker
   Node 2 ให้ย้อนไป step 150 ด้วยมือ) — step 150–167 ถูกคำนวณซ้ำและได้ loss เท่าเดิม
   สถิติเวลานับแต่ละ step ครั้งเดียว (ครั้งสุดท้าย) และไม่นับช่วงเครื่องดับ
4. ทดสอบ kill worker กลางทาง (`resume_test/`): supervisor เปิดใหม่เอง ต่อจาก checkpoint และน้ำหนักตรงกันทั้ง 2 Node

## ไฟล์
- `code/coordinator.py` โปรแกรมกลาง · `code/worker.py` โปรแกรมเทรน · `code/eval.py` วัดผล · `code/common.py` ส่วนร่วม
- `code/start_coordinator.sh`, `code/start_worker.sh`, `code/run_evals.sh` สคริปต์รันแบบ detached บน Node
- `results/run/` log ทุก step, GPU csv, weight check, LoRA ของทั้ง 2 Node ทั้ง 2 Epoch, `summary.json`
- `results/eval/` ผล Exact Match + คำตอบทุกข้อ · `results/smoke/` ผลลอง 3 step
