## สรุปงาน: เช่า 2 Node และเตรียมโมเดลกับ Dataset

| รายการ | Node 1 (`vapp-lab5-dp-1`) | Node 2 (`vapp-lab5-dp-2`) |
|---|---|---|
| เครื่องที่ได้ | instance <id> · Taiwan · RTX 3090 2 ใบ | instance <id> · Taiwan · RTX 3090 2 ใบ |
| ราคาต่อชั่วโมง | $0.4862 | $0.4940 |

| เน็ตระหว่าง Node | ผล |
|---|---|
| Node 2 ต่อเข้า port ของ Node 1 | ได้ |
| RTT | เฉลี่ย 5.95 ms |
| ความเร็ว Node 2 → Node 1 | 143 Mbps |
| ความเร็ว Node 1 → Node 2 | 784 Mbps |

| ชุดข้อมูล | จำนวนตัวอย่าง |
|---|---|
| Training Set | 4,000 |
| Test Set | 200 |

ตัวอย่าง 1 รายการ: คำถาม `Which engine has a year larger than 1956?` คือสิ่งที่ผู้ใช้ถาม, โครงสร้างตาราง `CREATE TABLE table_name_74 (engine VARCHAR, year INTEGER)` บอกชื่อตารางและคอลัมน์ที่ใช้ได้, และ SQL เฉลย `SELECT engine FROM table_name_74 WHERE year > 1956` คือคำตอบที่ถูกต้องซึ่งใช้ฝึกและวัดผล

ไม่มีการแสดงค่า key ใด ๆ และ **เครื่องทั้ง 2 เครื่องยังเปิดอยู่** คิดเงินรวมประมาณ $0.98 ต่อชั่วโมง