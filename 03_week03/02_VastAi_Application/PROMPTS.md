# พรอมต์ของบท 02 · VastAi Application (หน้ารวม)

พรอมต์ของแต่ละ LAB อยู่ใน `PROMPTS.md` ของ LAB นั้น เรียงตามลำดับขั้น คัดลอกไปวางได้ทันทีโดยไม่ต้องอ่าน README ทั้ง LAB

**ก่อนเริ่ม:** Claude Code app เปิดที่โฟลเดอร์ `02_VastAi_Application` · container `multi-account` รันอยู่และมีสกิล `vastai` ([บท 01](../01_VastAi_Skill/PROMPTS.md) ถึง LAB 2) · Docker Desktop บนเครื่องนี้

**LAB 0 · เตรียม key 3 ตัว** (ไม่มีพรอมต์) คัดลอก `.env_example` เป็น `.env` แล้วใส่ `VAST_API_KEY` · `ROBOFLOW_API_KEY` · `HF_TOKEN` วิธีหา key อยู่ใน [README.md](README.md#lab-0--เตรียม-key-3-ตัว)

> ⚠️ **เสียเงินจริง** — ทุก LAB จบด้วยพรอมต์ **ลบเครื่อง** ห้ามข้าม แล้วดูหน้า [Instances](https://cloud.vast.ai/instances/) ว่าว่าง

| LAB | ทำอะไร | พรอมต์ |
|---|---|---|
| 1 | เทรน YOLO ตรวจหมวกนิรภัย → เว็บตรวจความปลอดภัยหน้างาน | [lab1_yolo/PROMPTS.md](lab1_yolo/PROMPTS.md) |
| 2 | Fine-tune VLM อ่านใบเสร็จ → เว็บสมุดรายจ่าย | [lab2_vlm/PROMPTS.md](lab2_vlm/PROMPTS.md) |
| 3 | QLoRA โมเดลเล็กให้แชทบอทร้านนวด | [lab3_qlora/PROMPTS.md](lab3_qlora/PROMPTS.md) |
| 4 | LoRA บน GPU 1 · 2 · 4 ใบ: Single GPU · Data Parallelism · Model Parallelism | [หน้ารวม](lab4_multigpu/PROMPTS.md) · [4.1 Single GPU](lab4_multigpu/1_single_gpu/PROMPTS.md) · [4.2 Data Parallelism](lab4_multigpu/2_data_parallel/PROMPTS.md) · [4.3 Model Parallelism](lab4_multigpu/3_model_parallel/PROMPTS.md) |
| 5 | LoRA บนคลัสเตอร์ 2 และ 3 เครื่อง | [หน้ารวม](lab5_cluster/PROMPTS.md) · [5.1 Data Parallelism](lab5_cluster/1_data_parallel/PROMPTS.md) · [5.2 Model Parallelism](lab5_cluster/2_model_parallel/PROMPTS.md) |
| 6 | API ตรวจภาพ (Inference 1 โหนด หลาย GPU): Load Test · Micro-batching · Load Balancer ด้วย NGINX | [lab6_microbatch_lb/PROMPTS.md](lab6_microbatch_lb/PROMPTS.md) |
| 7 | LLM Serving หลัง NGINX แบบ Least Connections: Continuous Batching · Data Parallel · Model Parallel | [lab7_llm_serving_lb/PROMPTS.md](lab7_llm_serving_lb/PROMPTS.md) |
| 8 | อ่านใบเสร็จเป็นงานคิว: RabbitMQ + GPU Worker 1 → 2 ใบ | [lab8_job_queue/PROMPTS.md](lab8_job_queue/PROMPTS.md) |
| 9 | บริการสร้างภาพ: API gateway + RabbitMQ + GPU Worker | [lab9_hybrid/PROMPTS.md](lab9_hybrid/PROMPTS.md) |
