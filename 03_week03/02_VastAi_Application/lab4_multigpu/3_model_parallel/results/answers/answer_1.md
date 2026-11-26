เช่าเครื่อง RTX 3090 2 ใบได้แล้ว และโหลดโมเดลกับ Dataset ลงเครื่องพร้อมแบ่งชุดข้อมูลเรียบร้อย **เครื่องยังเปิดอยู่และคิดเงินต่อเนื่อง $0.4067 ต่อชั่วโมง**

## สรุป

| หัวข้อ | ผล |
|---|---|
| เครื่องที่ได้ | instance `<id>` (machine 134131) ป้าย `vapp-lab4-mp` · RTX 3090 24 GB 2 ใบ · United States |
| สเปก | CPU Xeon E5-2673 v4 ได้ 20 cores · verified · reliability 0.990 · ดาวน์โหลด 772 Mbps · ค่าดาวน์โหลด $0.0026 ต่อ GB · disk 60 GB |
| ระบบ | PyTorch 2.8.0+cu128 (CUDA 12.8) · image `vastai/pytorch:2.8.0-cuda-12.8.1-py312-24.04-2026-10-23` |
| ราคาต่อชั่วโมง | $0.4067 (รวมค่า disk 60 GB) |
| GPU ต่อถึงกันแบบไหน | PHB คือผ่าน PCIe และ Host Bridge ของ CPU · ไม่มี NVLink · PCIe gen 3 x16 · อยู่ NUMA node เดียวกัน |
| โมเดล | `Qwen/Qwen3-8B` 16.4 GB อยู่ที่ `/workspace/lab4_mp/models/Qwen3-8B` บนเครื่อง |
| Dataset ทั้งหมด | `b-mc2/sql-create-context` 78,577 ตัวอย่าง |
| Training Set | 4,000 ตัวอย่าง (สับด้วย seed 0) |
| Test Set | 200 ตัวอย่าง (ไม่ซ้ำกับ Training Set) |

- **การเลือกเครื่อง:** ตอนค้นครั้งแรก offer ที่ถูกที่สุดคือ $0.38 แต่ถูกเช่าไปก่อนสคริปต์จะสั่งเช่า จึงได้ตัวถูกที่สุดที่เหลือ คือ $0.4067
- **เวลาที่ใช้:** เครื่องพร้อมใน 542 วินาที ไม่เกิน 10 นาที จึงไม่ต้องลบแล้วเช่าใหม่
- **เงื่อนไข CPU:** ผมกรองด้วยจำนวน cores ที่ได้ใช้จริง (20 cores) ไม่ใช่จำนวน cores ทั้งเครื่อง (80)

## อธิบายตัวอย่าง 1 รายการ (รายการที่ 2 ในตาราง)

| ช่อง | ค่า | คืออะไร |
|---|---|---|
| คำถาม (`question`) | What is the highest pick number of a defensive back with less than 136 overall points? | คำถามภาษาอังกฤษที่ผู้ใช้ถาม เป็น input ของโมเดล |
| โครงสร้างตาราง (`context`) | `CREATE TABLE table_name_99 (pick__number INTEGER, overall VARCHAR, position VARCHAR)` | คำสั่ง `CREATE TABLE` ที่บอกชื่อตาราง ชื่อคอลัมน์ และชนิดข้อมูล โมเดลใช้ดูว่าต้องอ้างคอลัมน์ไหน |
| SQL เฉลย (`answer`) | `SELECT MAX(pick__number) FROM table_name_99 WHERE overall < 136 AND position = "defensive back"` | คำสั่ง SQL ที่ถูกต้อง เป็นคำตอบที่โมเดลต้องสร้าง: "highest" กลายเป็น `MAX` และเงื่อนไขสองข้อกลายเป็น `WHERE ... AND ...` |

## ความปลอดภัยของ key

- ไม่มีค่า key หรือ token อยู่ในโค้ด ผลลัพธ์ หรือรายงานนี้
- HF token ถูกส่งเข้าเครื่องเฉพาะตอนโหลด และลบออกจากเครื่องแล้ว
- กุญแจ SSH `devtoolSSH` ผูกกับ instance นี้เท่านั้น ไม่ได้เพิ่มเข้าบัญชี

## ไฟล์ที่เก็บไว้

อยู่ใน `lab4_multigpu/3_model_parallel`:

- `rent.py`
- `prepare.py`
- `ssh.sh`
- `results/dataset_samples.md`
- `results/instance.json`
- `results/prepare_summary.json`
- `results/gpu_topology.txt`
- `data/train.jsonl`
- `data/test.jsonl`

เมื่อเลิกใช้ ลบเครื่องด้วย `vastai destroy instance <id> -y`