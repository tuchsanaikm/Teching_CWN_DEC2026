# สรุปผล Lab 5 · model parallel · 3 Node

ทั้ง 3 Node พร้อมใช้งาน: เช่าครบ โหลดโมเดลกับ Dataset แล้ว แบ่งชุดข้อมูลได้ตรงกันทุกเครื่อง และ RTT ต่ำกว่า 100 ms จึงไม่ต้องเปลี่ยนเครื่องเลย

**⚠️ เครื่องทั้ง 3 ยังเปิดอยู่ (running) และคิดเงินรวมประมาณ $1.33 ต่อชั่วโมง**

## เครื่องที่ได้

| Node | ป้าย | instance | ที่ตั้ง | GPU | CPU (effective) | ราคา/ชม. |
|---|---|---|---|---|---|---|
| 1 | vapp-lab5-3mp-1 | <id> | Argentina | 2x RTX 3090 | 18.7 cores | $0.3900 |
| 2 | vapp-lab5-3mp-2 | <id> | Chile | 2x RTX 3090 | 28 cores | $0.4433 |
| 3 | vapp-lab5-3mp-3 | <id> | Chile | 2x RTX 3090 | 28 cores | $0.4967 |

- **การเลือกเครื่อง:** เลือกกลุ่มอเมริกาใต้ เพราะเป็นกลุ่มที่อยู่ใกล้กันและราคารวมถูกที่สุด ($1.33 เทียบกับกลุ่มไต้หวัน $1.38) ทั้ง 3 เครื่องมี IP สาธารณะต่างกัน
- **เงื่อนไข CPU:** นับ 16 cores จากจำนวนที่ได้ใช้จริง (effective) จึงตัดเครื่องในบัลแกเรียและโรมาเนียที่ได้จริงไม่ถึง 16 ออก
- **ระบบ:** image `vastai/pytorch:2.8.0-cuda-12.8.1-py312-24.04` ตรวจบนเครื่องแล้วเป็น torch 2.8.0+cu128, CUDA 12.8 เห็น GPU 2 ใบทุกเครื่อง disk 60 GB
- **เวลาเตรียมเครื่อง:** ทั้ง 3 เครื่องพร้อมภายในประมาณ 7 นาที ไม่เกินเกณฑ์ 10 นาที
- **port ของ Node 1:** เปิด container port 9000 ออกเป็น `203.0.113.10:<ext_port>`

## เน็ตระหว่าง Node

วัดด้วย TCP ผ่าน port ของ Node 1 จำนวน 2 รอบ รอบละ 10 วินาทีต่อทิศ ตัวเลขในตารางคือ รอบ 1 / รอบ 2

| เส้นทาง | ต่อเข้า port ได้ | RTT เฉลี่ย (ms) | Node N → Node 1 (Mbit/s) | Node 1 → Node N (Mbit/s) |
|---|---|---|---|---|
| Node 2 → Node 1 | ได้ | 34.2 / 35.6 | 644 / 210 | 262 / 619 |
| Node 3 → Node 1 | ได้ | 28.8 / 29.4 | 82 / 306 | 198 / 148 |

ความเร็วส่งข้อมูลแกว่งมากระหว่างสองรอบ (82–644 Mbit/s) ส่วน RTT นิ่งทั้งสองรอบ

## โมเดลและ Dataset

| รายการ | Node 1 | Node 2 | Node 3 |
|---|---|---|---|
| Qwen/Qwen3-8B | 16.4 GB | 16.4 GB | 16.4 GB |
| b-mc2/sql-create-context (ทั้งหมด) | 78,577 | 78,577 | 78,577 |
| Training Set | 4,000 | 4,000 | 4,000 |
| Test Set | 200 | 200 | 200 |

สับด้วย seed 0 แล้วใช้ 4,000 แถวแรกเป็น Training Set และ 200 แถวถัดไปเป็น Test Set ค่า sha256 ของ `train.jsonl` และ `test.jsonl` ตรงกันทั้ง 3 Node จึงยืนยันได้ว่าเป็นชุดเดียวกัน บนเครื่องเก็บไว้ที่ `/workspace/lab5/` (โมเดลใน `models/Qwen3-8B` ข้อมูลใน `data/`)

## อธิบายตัวอย่าง 1 รายการ

ตัวอย่างนี้คือรายการที่ 1 ในตาราง 6 รายการของ `results/dataset_samples.md`

| ช่อง | ค่า | ความหมาย |
|---|---|---|
| คำถาม (question) | What is the lowest unlock order for the athens circuit? | คำถามภาษาธรรมชาติที่ผู้ใช้ถาม เป็น input ของโมเดล |
| โครงสร้างตาราง (context) | `CREATE TABLE table_24463470_1 (unlock_order INTEGER, circuit VARCHAR)` | คำสั่ง CREATE TABLE ที่บอกชื่อตาราง ชื่อคอลัมน์ และชนิดข้อมูล ให้โมเดลรู้ว่าต้องเขียน SQL กับตารางใด |
| SQL เฉลย (answer) | `SELECT MIN(unlock_order) FROM table_24463470_1 WHERE circuit = "Athens"` | คำสั่ง SQL ที่ถูกต้อง เป็นคำตอบที่ให้โมเดลเรียนและใช้เทียบตอนวัดผล |

ในตัวอย่างนี้ "lowest" กลายเป็น `MIN(unlock_order)` และ "athens circuit" กลายเป็นเงื่อนไข `WHERE circuit = "Athens"`

## ไฟล์ที่เก็บไว้

อยู่ใน `lab5_cluster/2_model_parallel/node3/` โค้ดทั้งหมดเขียนใหม่ในงานนี้ และไม่มีค่า key อยู่ในไฟล์หรือในรายงาน

- `results/summary.md`
- `results/dataset_samples.md`
- `results/net_probe_run1.json`
- `results/net_probe_run2.json`
- `results/prepare_node1.json` (และ node2, node3)
- `data/train.jsonl`
- `data/test.jsonl`