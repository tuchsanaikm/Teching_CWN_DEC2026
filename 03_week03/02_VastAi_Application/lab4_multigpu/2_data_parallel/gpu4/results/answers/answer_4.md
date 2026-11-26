## สรุปผล: เช่าเครื่อง GPU 4 ใบ และเตรียมโมเดลกับ Dataset

เครื่อง RTX 3090 4 ใบเช่าได้แล้ว และโมเดลกับ Dataset อยู่บนเครื่องครบ **เครื่องยังเปิดอยู่และคิดเงินต่อเนื่อง $0.87 ต่อชั่วโมง**

| หัวข้อ | ผล |
|---|---|
| เครื่องที่ได้ | instance `<id>` (machine 155684) ป้าย `vapp-lab4-dp4` · RTX 3090 24 GB × 4 · Chile · verified · reliability 0.987 |
| สเปก | CPU Xeon E5-2680 v4 2 ซ็อกเก็ต 56 cores · RAM 94 GB · disk 60 GB (ใช้ไป 16 GB) · ดาวน์โหลด 897 Mbps · ค่าดาวน์โหลด $0.0026 ต่อ GB |
| ระบบ | PyTorch 2.8.0+cu128 (CUDA 12.8) · image `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime` · มองเห็น GPU ครบ 4 ใบ |
| ราคาต่อชั่วโมง | **$0.87** (เพดาน $1.40) |
| GPU ต่อถึงกันแบบไหน | ผ่าน PCIe 3.0 x16 ไม่มี NVLink · GPU0–GPU1 และ GPU2–GPU3 อยู่ใต้ CPU ตัวเดียวกัน (PHB) · ข้ามคู่ต้องผ่านทางเชื่อมระหว่าง CPU 2 ตัว (SYS) ซึ่งช้ากว่า |
| โมเดล | `Qwen/Qwen3-8B` 16.4 GB ที่ `/workspace/lab4_dp4/models/Qwen3-8B` บนเครื่องเช่า |
| Dataset | `b-mc2/sql-create-context` ทั้งหมด 78,577 ตัวอย่าง · สับด้วย seed 0 |
| Training Set | **4,000 ตัวอย่าง** (`data/train.jsonl`) |
| Test Set | **200 ตัวอย่าง** (`data/test.jsonl`) · ไม่มีตัวอย่างซ้ำกับ Training Set |

### เรื่องที่ควรรู้เกี่ยวกับการเช่า
- **เครื่องที่ได้ไม่ใช่เครื่องถูกที่สุด** เครื่องถูกสุดที่ผ่านเงื่อนไข ($0.78, US) เช่าแล้วค้างที่สถานะ loading เกิน 10 นาที จึงลบ (instance `<id>`) แล้วเช่าเครื่องถัดไปที่ $0.87 ซึ่งพร้อมใน 436 วินาที
- **ข้ามข้อเสนอ $0.76 (Taiwan)** เพราะไดรเวอร์ของเครื่องนั้นรองรับ CUDA ได้ถึง 12.2 เท่านั้น จึงใช้ PyTorch ที่มี CUDA 12.8 ไม่ได้
- **ลงทะเบียนกุญแจ SSH** `devtoolSSH.pub` เพิ่มเข้าบัญชี Vast.ai เพราะยังไม่มีในบัญชี

### อธิบายตัวอย่าง 1 รายการ (รายการที่ 1 ในตาราง)

| ช่อง | ค่า | คืออะไร |
|---|---|---|
| คำถาม (`question`) | What is the lowest unlock order for the athens circuit? | คำถามภาษาอังกฤษที่ผู้ใช้ถาม เป็นข้อความป้อนเข้าโมเดล |
| โครงสร้างตาราง (`context`) | `CREATE TABLE table_24463470_1 (unlock_order INTEGER, circuit VARCHAR)` | คำสั่ง `CREATE TABLE` ที่บอกชื่อตาราง ชื่อคอลัมน์ และชนิดข้อมูล โมเดลใช้เป็นบริบทเพื่อรู้ว่ามีคอลัมน์อะไรให้อ้างถึง |
| SQL เฉลย (`answer`) | `SELECT MIN(unlock_order) FROM table_24463470_1 WHERE circuit = "Athens"` | คำสั่ง SQL ที่ถูกต้อง เป็นเป้าหมายที่โมเดลต้องสร้าง: "lowest" กลายเป็น `MIN(unlock_order)` และ "athens circuit" กลายเป็นเงื่อนไข `WHERE circuit = "Athens"` |

### ไฟล์ที่เก็บไว้
อยู่ใน `lab4_multigpu/2_data_parallel/gpu4`
- `code/rent.sh`
- `code/prepare.py`
- `results/dataset_samples.md`
- `results/prepare_info.json`
- `results/machine.json`
- `results/gpu_topology.txt`
- `results/offers.json`
- `results/instance.txt`

เมื่อเลิกใช้ให้ลบด้วย `vastai destroy instance <id> -y`

ไม่มีการแสดงค่า key หรือ token ใด ๆ ในรายงานและไฟล์ผลลัพธ์