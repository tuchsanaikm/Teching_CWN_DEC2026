เช่าเครื่อง RTX 3090 2 ใบได้แล้ว โหลดโมเดลกับ Dataset ลงเครื่องและแบ่งชุดข้อมูลเสร็จ **เครื่องยังเปิดอยู่และคิดเงินต่อเนื่อง**

เครื่องแรกที่เช่า (instance <id>, สหรัฐฯ, $0.38/ชม.) ดึง image เกิน 10 นาทีแล้วยังไม่พร้อม จึงลบทิ้งแล้วเช่าเครื่องที่ถูกที่สุดถัดไปแทน

| รายการ | ผล |
|---|---|
| เครื่องที่ได้ | instance `<id>` (machine 80363) · Quebec, แคนาดา · ป้าย `vapp-lab4-dp` · สถานะ running |
| GPU | RTX 3090 24 GB × 2 ใบในเครื่องเดียว |
| CPU / disk | AMD EPYC 7551P · 64 cores (ใช้ได้จริง 25.6) · disk 60 GB |
| ระบบ | PyTorch 2.8.0+cu128 · CUDA 12.8 (image `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel`) |
| ราคาต่อชั่วโมง | $0.3767 (รวม disk 60 GB) |
| เงื่อนไขอื่น | verified · reliability 0.989 · ดาวน์โหลด 935 Mbps · ค่าดาวน์โหลด $0.0026/GB |
| GPU ต่อถึงกันแบบไหน | `SYS` คือผ่าน PCIe และข้าม NUMA node (GPU0 อยู่ NUMA 0, GPU1 อยู่ NUMA 3) · ไม่มี NVLink · GPU0 ต่อ PCIe กว้างแค่ x4 ส่วน GPU1 เป็น x16 |
| โมเดล | `Qwen/Qwen3-8B` 16.4 GB อยู่ที่ `/workspace/lab4_dp/models/Qwen3-8B` บนเครื่องเช่า |
| Dataset | `b-mc2/sql-create-context` ทั้งหมด 78,577 ตัวอย่าง สับด้วย seed 0 |
| Training Set | 4,000 ตัวอย่าง (`/workspace/lab4_dp/data/train.jsonl`) |
| Test Set | 200 ตัวอย่าง (`/workspace/lab4_dp/data/test.jsonl`) ไม่ซ้ำกับ Training Set |

การต่อแบบ `SYS` เป็นเส้นทางที่ช้าที่สุดระหว่าง GPU สองใบ และ GPU0 ที่ได้แค่ x4 อาจทำให้การส่งข้อมูลเข้าออกใบนั้นช้ากว่าอีกใบ

## ตัวอย่าง 1 รายการ (รายการที่ 1 ในตาราง)

| ช่อง | ค่า | คืออะไร |
|---|---|---|
| คำถาม (`question`) | What is the lowest unlock order for the athens circuit? | คำถามภาษาอังกฤษที่ผู้ใช้ถาม เป็น input ของโมเดล |
| โครงสร้างตาราง (`context`) | `CREATE TABLE table_24463470_1 (unlock_order INTEGER, circuit VARCHAR)` | คำสั่ง `CREATE TABLE` ที่บอกชื่อตาราง ชื่อคอลัมน์ และชนิดข้อมูล ให้โมเดลรู้ว่าต้องเขียน SQL กับตารางไหน |
| SQL เฉลย (`answer`) | `SELECT MIN(unlock_order) FROM table_24463470_1 WHERE circuit = "Athens"` | คำสั่ง SQL ที่ถูกต้อง ใช้เป็นเป้าหมายตอนฝึกและเป็นเฉลยตอนวัดผล |

ในตัวอย่างนี้ "lowest" กลายเป็น `MIN(unlock_order)` และ "athens circuit" กลายเป็นเงื่อนไข `WHERE circuit = "Athens"`

- กุญแจ SSH `devtoolSSH` ผูกกับ instance นี้แล้ว
- เมื่อเลิกใช้ ให้ลบด้วย `vastai destroy instance <id> -y`

ไฟล์อยู่ใน `lab4_multigpu/2_data_parallel`:
- `prepare.py`
- `results/dataset_samples.md`
- `results/prepare_info.json`
- `results/machine_info.txt`