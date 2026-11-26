# LAB 4.1 · พรอมต์ Copy & Paste — Single GPU

คำถามของ LAB: GPU 1 ใบ เทรนโมเดล 8 พันล้าน parameter ได้ batch ใหญ่แค่ไหน และเร็วเท่าไร

วางทีละพรอมต์ในช่องพิมพ์ของ Claude Code app (เปิดที่โฟลเดอร์ของบทนี้) · มี 3 ขั้น ทำตามลำดับให้ครบในรอบเดียว · โค้ดทุกไฟล์ AI เขียนเองลงใน `lab4_multigpu/1_single_gpu/code` (เริ่มจากโฟลเดอร์ว่าง)

ทุกพรอมต์แบ่งเป็นหัวข้อเดียวกัน: `[ที่ทำงาน]` อยู่ที่ไหน · `[งาน]` ทำอะไร · `[ขั้นตอน]` ทำตามลำดับ · `[ค่าที่ตรึง]` ค่าที่ห้ามเปลี่ยน · `[รายงาน]` ให้สรุปอะไร

## ขั้นที่ 1 · เช่าเครื่องและเตรียมของ

```text
[ที่ทำงาน]
container `multi-account` · โฟลเดอร์ /workspace/vastapp_lab · สกิล vastai
กุญแจ SSH: /workspace/vastai_lab/Devtool_SSH/devtoolSSH
เก็บโค้ดและผลที่: lab4_multigpu/1_single_gpu ของโฟลเดอร์ที่เปิด Claude Code อยู่ (ไม่ใช่ใน container)

[งาน]
เช่าเครื่อง GPU 1 ใบ แล้วเตรียมโมเดลกับ Dataset

[เครื่องที่ต้องการ]
GPU: RTX 4090 1 ใบ · ราคาไม่เกิน $0.30 ต่อชั่วโมง · ป้าย vapp-lab4-single
เงื่อนไข: verified · reliability 0.95 ขึ้นไป · ความเร็วเน็ตไม่ต่ำกว่า 1,200 Mbps · ค่าดาวน์โหลดไม่เกิน $0.01 ต่อ GB · ไม่อยู่ในจีน
ระบบ: PyTorch 2.8 ที่มี CUDA 12.8 · disk 60 GB

[ขั้นตอน]
1. เช่าเครื่องที่ถูกที่สุดตามเงื่อนไข ถ้าเกิน 10 นาทียังไม่พร้อม ให้ลบแล้วเช่าเครื่องอื่น
2. โหลดโมเดล Qwen/Qwen3-8B และ Dataset b-mc2/sql-create-context ลงเครื่อง
3. สับ Dataset ด้วย seed 0 แล้วแบ่ง Training Set 4,000 ตัวอย่าง และ Test Set 200 ตัวอย่าง
4. ทำตารางตัวอย่าง 6 รายการ (คำถาม · โครงสร้างตาราง · SQL เฉลย) เก็บที่ results/dataset_samples.md

[รายงาน]
สรุปเป็นตาราง: เครื่องที่ได้ · ราคาต่อชั่วโมง · จำนวนตัวอย่างของแต่ละชุด
อธิบายตัวอย่าง 1 รายการว่าแต่ละช่องคืออะไร · ห้ามแสดงค่า key · บอกว่าเครื่องยังเปิดอยู่
```

## ขั้นที่ 2 · เทรนด้วย GPU 1 ใบ

```text
[ที่ทำงาน]
container `multi-account` · โฟลเดอร์ /workspace/vastapp_lab · สกิล vastai
เครื่อง: ป้าย vapp-lab4-single · กุญแจ SSH: /workspace/vastai_lab/Devtool_SSH/devtoolSSH
เก็บโค้ดและผลที่: lab4_multigpu/1_single_gpu ของโฟลเดอร์ที่เปิด Claude Code อยู่ (ไม่ใช่ใน container)

[งาน]
เทรน Qwen3-8B ให้แปลงคำถามเป็น SQL ด้วย GPU 1 ใบ
แนวคิด: โมเดลทั้งชุดและข้อมูลทั้ง batch อยู่บน GPU ใบเดียว

[ขั้นตอน]
1. เขียน code/train.py เทรนด้วย LoRA บน GPU 1 ใบ
2. หา batch ใหญ่สุด: ลอง 1, 2, 4, 8 … อย่างละ 3 step ด้วยตัวอย่างที่ยาวที่สุด จน Out of Memory
   แล้วประมาณจาก VRAM ที่วัดได้ว่า batch เท่าไรจะพอดี และลองค่าระหว่างตัวที่ผ่านกับตัวที่ล้ม จนได้ batch ใหญ่สุดที่ผ่านจริง
3. เทรน 3 Epoch ด้วย batch ใหญ่สุดที่หาได้ในข้อ 2
4. เขียน code/eval.py วัด Exact Match บน Test Set ของโมเดลก่อนเทรน (Base) และหลังจบแต่ละ Epoch
5. ให้งานรันต่อได้แม้การเชื่อมต่อหลุด และรายงานทุก 2–3 นาที

[ค่าที่ตรึง]
โมเดล: Qwen/Qwen3-8B แบบ bf16 · ปิด thinking · ไม่ใช้ Gradient Checkpointing
LoRA: r 8 · alpha 16 · ที่ q_proj กับ v_proj
การเทรน: learning rate 2e-4 · seed 0 · ข้อความยาวไม่เกิน 256 token

[รายงาน]
สรุปเป็นตาราง: batch เทียบ VRAM สูงสุด · batch ที่ประมาณไว้ · batch ที่ใช้เทรน · วินาทีต่อ step · ตัวอย่างต่อวินาที · GPU util · loss และ Exact Match ของ Base และหลังจบแต่ละ Epoch
บอกว่าเครื่องยังเปิดอยู่
```

## ขั้นที่ 3 · สรุปและลบเครื่อง (ห้ามข้าม)

```text
[ที่ทำงาน]
container `multi-account` · โฟลเดอร์ /workspace/vastapp_lab · สกิล vastai
เครื่อง: ป้าย vapp-lab4-single · กุญแจ SSH: /workspace/vastai_lab/Devtool_SSH/devtoolSSH
เก็บโค้ดและผลที่: lab4_multigpu/1_single_gpu ของโฟลเดอร์ที่เปิด Claude Code อยู่ (ไม่ใช่ใน container)

[งาน]
สรุปผลเป็นกราฟ แล้วลบเครื่อง

[ขั้นตอน]
1. นำผลดิบกลับมาที่ results/raw
2. ค้นราคาตลาดของ RTX 4090 1 ใบที่ถูกที่สุด
3. เขียน code/report.py รวมตัวเลขลง results/metrics.json พร้อมเงินต่อ 1,000 ตัวอย่าง
4. ให้สคริปต์วาดกราฟที่ results/images (ข้อความอังกฤษ): VRAM เทียบ batch พร้อมเส้น 24 GB · loss ตลอด 3 Epoch · Exact Match ของแต่ละ Epoch
5. ลบเครื่องป้าย vapp-lab4-single แล้วตรวจว่าไม่เหลือ (ห้ามแตะเครื่องป้ายอื่น)

[รายงาน]
สรุปเป็นตาราง: batch ใหญ่สุด · ตัวอย่างต่อวินาที · Exact Match · เงินต่อ 1,000 ตัวอย่าง
ค่าใช้จ่ายจริงของเครื่อง: อายุเครื่อง · ยอดที่ถูกคิด · ห้ามแสดงค่า key
```
