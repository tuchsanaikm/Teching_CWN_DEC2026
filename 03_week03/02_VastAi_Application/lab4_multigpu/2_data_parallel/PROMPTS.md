# LAB 4.2 · พรอมต์ Copy & Paste — Data Parallelism

คำถามของ LAB: ให้ GPU 2 ใบถือโมเดลคนละชุดแล้วแบ่งข้อมูลกันเทรน จะเร็วแค่ไหน และรับ batch ต่อใบได้ใหญ่แค่ไหน

วางทีละพรอมต์ในช่องพิมพ์ของ Claude Code app (เปิดที่โฟลเดอร์ของบทนี้) · มี 6 ขั้น: ขั้นที่ 1–3 ใช้ GPU 2 ใบ · ขั้นที่ 4–6 ทำซ้ำด้วย GPU 4 ใบบนเครื่องใหม่ (เก็บโค้ดและผลแยกไว้ที่โฟลเดอร์ย่อย `gpu4`) · ทำแต่ละชุดให้ครบในรอบเดียว · โค้ดทุกไฟล์ AI เขียนเองลงใน `lab4_multigpu/2_data_parallel/code` (เริ่มจากโฟลเดอร์ว่าง)

ทุกพรอมต์แบ่งเป็นหัวข้อเดียวกัน: `[ที่ทำงาน]` อยู่ที่ไหน · `[งาน]` ทำอะไร · `[ขั้นตอน]` ทำตามลำดับ · `[ค่าที่ตรึง]` ค่าที่ห้ามเปลี่ยน · `[รายงาน]` ให้สรุปอะไร

## ขั้นที่ 1 · เช่าเครื่อง 2 GPU และเตรียมของ

```text
[ที่ทำงาน]
container `multi-account` · โฟลเดอร์ /workspace/vastapp_lab · สกิล vastai
กุญแจ SSH: /workspace/vastai_lab/Devtool_SSH/devtoolSSH
เก็บโค้ดและผลที่: lab4_multigpu/2_data_parallel ของโฟลเดอร์ที่เปิด Claude Code อยู่ (ไม่ใช่ใน container)

[งาน]
เช่าเครื่อง GPU 2 ใบ แล้วเตรียมโมเดลกับ Dataset

[เครื่องที่ต้องการ]
GPU: RTX 4090 2 ใบในเครื่องเดียว · ราคาไม่เกิน $0.60 ต่อชั่วโมง · ป้าย vapp-lab4-dp
เงื่อนไข: verified · reliability 0.95 ขึ้นไป · ความเร็วเน็ตไม่ต่ำกว่า 1,200 Mbps · ค่าดาวน์โหลดไม่เกิน $0.01 ต่อ GB · CPU 16 cores ขึ้นไป · ไม่อยู่ในจีน
ระบบ: PyTorch 2.8 ที่มี CUDA 12.8 · disk 60 GB

[ขั้นตอน]
1. เช่าเครื่องที่ถูกที่สุดตามเงื่อนไข ถ้าเกิน 10 นาทียังไม่พร้อม ให้ลบแล้วเช่าเครื่องอื่น
2. โหลดโมเดล Qwen/Qwen3-8B และ Dataset b-mc2/sql-create-context ลงเครื่อง
3. สับ Dataset ด้วย seed 0 แล้วแบ่ง Training Set 4,000 ตัวอย่าง และ Test Set 200 ตัวอย่าง
4. ทำตารางตัวอย่าง 6 รายการ (คำถาม · โครงสร้างตาราง · SQL เฉลย) เก็บที่ results/dataset_samples.md

[รายงาน]
สรุปเป็นตาราง: เครื่องที่ได้ · ราคาต่อชั่วโมง · GPU ต่อถึงกันแบบไหน · จำนวนตัวอย่างของแต่ละชุด
อธิบายตัวอย่าง 1 รายการว่าแต่ละช่องคืออะไร · ห้ามแสดงค่า key · บอกว่าเครื่องยังเปิดอยู่
```

## ขั้นที่ 2 · เทรนแบบ Data Parallelism

```text
[ที่ทำงาน]
container `multi-account` · โฟลเดอร์ /workspace/vastapp_lab · สกิล vastai
เครื่อง: ป้าย vapp-lab4-dp · กุญแจ SSH: /workspace/vastai_lab/Devtool_SSH/devtoolSSH
เก็บโค้ดและผลที่: lab4_multigpu/2_data_parallel ของโฟลเดอร์ที่เปิด Claude Code อยู่ (ไม่ใช่ใน container)

[งาน]
เทรน Qwen3-8B ให้แปลงคำถามเป็น SQL แบบ Data Parallelism
แนวคิด: GPU 2 ใบถือโมเดลคนละชุด แบ่งข้อมูลใบละครึ่ง แล้วเฉลี่ย Gradient ให้เท่ากัน

[ขั้นตอน]
1. เขียน code/train.py เทรนด้วย LoRA บน GPU 2 ใบ ใช้ DDP ของ PyTorch
2. หา batch ต่อ GPU ใหญ่สุด: ลอง 1, 2, 4, 8 … อย่างละ 3 step ด้วยตัวอย่างที่ยาวที่สุด จน Out of Memory
   แล้วประมาณจาก VRAM ที่วัดได้ว่า batch เท่าไรจะพอดี และลองค่าระหว่างตัวที่ผ่านกับตัวที่ล้ม จนได้ batch ใหญ่สุดที่ผ่านจริง
3. เทรน 3 Epoch ด้วย batch ต่อ GPU ใหญ่สุดที่หาได้ในข้อ 2
4. เขียน code/eval.py วัด Exact Match บน Test Set ของโมเดลก่อนเทรน (Base) และหลังจบแต่ละ Epoch
5. ให้งานรันต่อได้แม้การเชื่อมต่อหลุด และรายงานทุก 2–3 นาที

[ค่าที่ตรึง]
โมเดล: Qwen/Qwen3-8B แบบ bf16 · ปิด thinking · ไม่ใช้ Gradient Checkpointing
LoRA: r 8 · alpha 16 · ที่ q_proj กับ v_proj
การเทรน: learning rate 2e-4 · seed 0 · ข้อความยาวไม่เกิน 256 token

[รายงาน]
สรุปเป็นตาราง: batch ต่อ GPU เทียบ VRAM สูงสุดของแต่ละใบ · batch ที่ประมาณไว้ · batch ที่ใช้เทรน (ต่อ GPU และรวม) · วินาทีต่อ step · ตัวอย่างต่อวินาที · GPU util ของแต่ละใบ · loss และ Exact Match ของ Base และหลังจบแต่ละ Epoch
บอกว่าเครื่องยังเปิดอยู่
```

## ขั้นที่ 3 · สรุปและลบเครื่อง (ห้ามข้าม)

```text
[ที่ทำงาน]
container `multi-account` · โฟลเดอร์ /workspace/vastapp_lab · สกิล vastai
เครื่อง: ป้าย vapp-lab4-dp · กุญแจ SSH: /workspace/vastai_lab/Devtool_SSH/devtoolSSH
เก็บโค้ดและผลที่: lab4_multigpu/2_data_parallel ของโฟลเดอร์ที่เปิด Claude Code อยู่ (ไม่ใช่ใน container)

[งาน]
สรุปผลเป็นกราฟ แล้วลบเครื่อง

[ขั้นตอน]
1. นำผลดิบกลับมาที่ results/raw
2. ค้นราคาตลาดของเครื่อง RTX 4090 2 ใบที่ถูกที่สุด
3. เขียน code/report.py รวมตัวเลขลง results/metrics.json พร้อมเงินต่อ 1,000 ตัวอย่าง
4. ให้สคริปต์วาดกราฟที่ results/images (ข้อความอังกฤษ): VRAM ของแต่ละใบเทียบ batch พร้อมเส้น 24 GB · GPU util ของแต่ละใบ · loss ตลอด 3 Epoch · Exact Match ของแต่ละ Epoch
5. ลบเครื่องป้าย vapp-lab4-dp แล้วตรวจว่าไม่เหลือ (ห้ามแตะเครื่องป้ายอื่น)

[รายงาน]
สรุปเป็นตาราง: batch ต่อ GPU ใหญ่สุด · ตัวอย่างต่อวินาที · Exact Match · เงินต่อ 1,000 ตัวอย่าง
ค่าใช้จ่ายจริงของเครื่อง: อายุเครื่อง · ยอดที่ถูกคิด · ห้ามแสดงค่า key
```

# GPU 4 ใบ

ทำซ้ำการทดลองเดิมทุกอย่าง เปลี่ยนแค่จำนวน GPU จาก 2 เป็น 4 ใบ บนเครื่องเช่าเครื่องใหม่

## ขั้นที่ 4 · เช่าเครื่อง 4 GPU และเตรียมของ

```text
[ที่ทำงาน]
container `multi-account` · โฟลเดอร์ /workspace/vastapp_lab · สกิล vastai
กุญแจ SSH: /workspace/vastai_lab/Devtool_SSH/devtoolSSH
เก็บโค้ดและผลที่: lab4_multigpu/2_data_parallel/gpu4 ของโฟลเดอร์ที่เปิด Claude Code อยู่ (ไม่ใช่ใน container)

[งาน]
เช่าเครื่อง GPU 4 ใบ แล้วเตรียมโมเดลกับ Dataset

[เครื่องที่ต้องการ]
GPU: RTX 4090 4 ใบในเครื่องเดียว · ราคาไม่เกิน $1.40 ต่อชั่วโมง · ป้าย vapp-lab4-dp4
เงื่อนไข: verified · reliability 0.95 ขึ้นไป · ความเร็วเน็ตไม่ต่ำกว่า 1,200 Mbps · ค่าดาวน์โหลดไม่เกิน $0.01 ต่อ GB · CPU 16 cores ขึ้นไป · ไม่อยู่ในจีน
ระบบ: PyTorch 2.8 ที่มี CUDA 12.8 · disk 60 GB

[ขั้นตอน]
1. เช่าเครื่องที่ถูกที่สุดตามเงื่อนไข ถ้าเกิน 10 นาทียังไม่พร้อม ให้ลบแล้วเช่าเครื่องอื่น
2. โหลดโมเดล Qwen/Qwen3-8B และ Dataset b-mc2/sql-create-context ลงเครื่อง
3. สับ Dataset ด้วย seed 0 แล้วแบ่ง Training Set 4,000 ตัวอย่าง และ Test Set 200 ตัวอย่าง
4. ทำตารางตัวอย่าง 6 รายการ (คำถาม · โครงสร้างตาราง · SQL เฉลย) เก็บที่ results/dataset_samples.md

[รายงาน]
สรุปเป็นตาราง: เครื่องที่ได้ · ราคาต่อชั่วโมง · GPU ต่อถึงกันแบบไหน · จำนวนตัวอย่างของแต่ละชุด
อธิบายตัวอย่าง 1 รายการว่าแต่ละช่องคืออะไร · ห้ามแสดงค่า key · บอกว่าเครื่องยังเปิดอยู่
```

## ขั้นที่ 5 · เทรนแบบ Data Parallelism ด้วย GPU 4 ใบ

```text
[ที่ทำงาน]
container `multi-account` · โฟลเดอร์ /workspace/vastapp_lab · สกิล vastai
เครื่อง: ป้าย vapp-lab4-dp4 · กุญแจ SSH: /workspace/vastai_lab/Devtool_SSH/devtoolSSH
เก็บโค้ดและผลที่: lab4_multigpu/2_data_parallel/gpu4 ของโฟลเดอร์ที่เปิด Claude Code อยู่ (ไม่ใช่ใน container)

[งาน]
เทรน Qwen3-8B ให้แปลงคำถามเป็น SQL แบบ Data Parallelism
แนวคิด: GPU 4 ใบถือโมเดลคนละชุด แบ่งข้อมูลใบละ 1 ใน 4 แล้วเฉลี่ย Gradient ให้เท่ากัน

[ขั้นตอน]
1. เขียน code/train.py เทรนด้วย LoRA บน GPU 4 ใบ ใช้ DDP ของ PyTorch
2. หา batch ต่อ GPU ใหญ่สุด: ลอง 1, 2, 4, 8 … อย่างละ 3 step ด้วยตัวอย่างที่ยาวที่สุด จน Out of Memory
   แล้วประมาณจาก VRAM ที่วัดได้ว่า batch เท่าไรจะพอดี และลองค่าระหว่างตัวที่ผ่านกับตัวที่ล้ม จนได้ batch ใหญ่สุดที่ผ่านจริง
3. เทรน 3 Epoch ด้วย batch ต่อ GPU ใหญ่สุดที่หาได้ในข้อ 2
4. เขียน code/eval.py วัด Exact Match บน Test Set ของโมเดลก่อนเทรน (Base) และหลังจบแต่ละ Epoch
5. ให้งานรันต่อได้แม้การเชื่อมต่อหลุด และรายงานทุก 2–3 นาที

[ค่าที่ตรึง]
โมเดล: Qwen/Qwen3-8B แบบ bf16 · ปิด thinking · ไม่ใช้ Gradient Checkpointing
LoRA: r 8 · alpha 16 · ที่ q_proj กับ v_proj
การเทรน: learning rate 2e-4 · seed 0 · ข้อความยาวไม่เกิน 256 token

[รายงาน]
สรุปเป็นตาราง: batch ต่อ GPU เทียบ VRAM สูงสุดของแต่ละใบ · batch ที่ประมาณไว้ · batch ที่ใช้เทรน (ต่อ GPU และรวม) · วินาทีต่อ step · ตัวอย่างต่อวินาที · GPU util ของแต่ละใบ · loss และ Exact Match ของ Base และหลังจบแต่ละ Epoch
บอกว่าเครื่องยังเปิดอยู่
```

## ขั้นที่ 6 · สรุปและลบเครื่อง 4 GPU (ห้ามข้าม)

```text
[ที่ทำงาน]
container `multi-account` · โฟลเดอร์ /workspace/vastapp_lab · สกิล vastai
เครื่อง: ป้าย vapp-lab4-dp4 · กุญแจ SSH: /workspace/vastai_lab/Devtool_SSH/devtoolSSH
เก็บโค้ดและผลที่: lab4_multigpu/2_data_parallel/gpu4 ของโฟลเดอร์ที่เปิด Claude Code อยู่ (ไม่ใช่ใน container)

[งาน]
สรุปผลเป็นกราฟ แล้วลบเครื่อง

[ขั้นตอน]
1. นำผลดิบกลับมาที่ results/raw
2. ค้นราคาตลาดของเครื่อง RTX 4090 4 ใบที่ถูกที่สุด
3. เขียน code/report.py รวมตัวเลขลง results/metrics.json พร้อมเงินต่อ 1,000 ตัวอย่าง
4. ให้สคริปต์วาดกราฟที่ results/images (ข้อความอังกฤษ): VRAM ของแต่ละใบเทียบ batch พร้อมเส้น 24 GB · GPU util ของแต่ละใบ · loss ตลอด 3 Epoch · Exact Match ของแต่ละ Epoch
5. ลบเครื่องป้าย vapp-lab4-dp4 แล้วตรวจว่าไม่เหลือ (ห้ามแตะเครื่องป้ายอื่น)

[รายงาน]
สรุปเป็นตาราง: batch ต่อ GPU ใหญ่สุด · ตัวอย่างต่อวินาที · Exact Match · เงินต่อ 1,000 ตัวอย่าง
ค่าใช้จ่ายจริงของเครื่อง: อายุเครื่อง · ยอดที่ถูกคิด · ห้ามแสดงค่า key
```
