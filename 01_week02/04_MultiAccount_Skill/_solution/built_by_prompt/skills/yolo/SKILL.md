---
name: yolo
description: สั่งงานบัญชี Claude Code (yolo1–yolo5) ใน docker container "multi-account" ได้แก่ ส่ง prompt แบบไม่โต้ตอบ, เลือกบัญชีที่โควตาเหลือมากสุดให้อัตโนมัติ, แปลงความยาก 1–6 เป็นรุ่นและระดับการคิด, อ่านไฟล์ภาพ, ตรวจความพร้อม, ดูโควตา, ดูรุ่น และสรุปสถิติการใช้ ใช้เมื่อผู้ใช้ต้องการส่งงานให้ yolo หรือบัญชี Claude Code
---

# yolo — Claude Code (yolo1–5)

`Y = python <โฟลเดอร์สกิลนี้>/scripts/yolo.py` (ในเครื่องนี้คือ `python C:\t\ma04\b\app\skills\yolo\scripts\yolo.py`)

| ต้องการอะไร | ใช้คำสั่งไหน |
|---|---|
| สั่งงาน 1 ครั้ง (เลือกบัญชีที่โควตาเหลือมากสุดให้) | `Y run -d 2 "คำสั่ง"` |
| ระบุบัญชีเอง | `Y run -a yolo2 -d 3 "คำสั่ง"` (`-a 2` ก็ได้) |
| prompt ยาวหรืออยู่ในไฟล์ | `Y run -d 3 -f prompt.txt` หรือ `type prompt.txt \| Y run -d 3` |
| ให้อ่านหรือตรวจภาพ | `Y run -d 1 -i pic.png "ในภาพมีอะไร"` (ใส่ `-i` ซ้ำได้) |
| สร้างภาพ | **ทำไม่ได้** ให้ใช้สกิล `cyolo` |
| ตรวจความพร้อม (เรียกจริงทุกบัญชี) | `Y check` |
| ดูโควตาที่ใช้ไป (%) | `Y quota` |
| ดูรุ่นที่ใช้ได้และตารางความยาก | `Y models` |
| ดูสถิติการใช้ | `Y stats` · `Y stats --all --since 24` |
| จำกัดให้แตะได้เฉพาะบางบัญชี | ตั้ง `AI_SKILL_ACCOUNTS=yolo2,yolo3` ก่อนรัน (บัญชีอื่นจะไม่ถูกเรียกเลย; `AI_SKILL_AUDIT=<ไฟล์>` จดทุกการเรียก) |
| ได้ผลเป็น JSON | เติม `--json` ได้ทุกคำสั่ง |

**ความยาก (`-d`):**

| `-d` | รุ่น/ระดับการคิด |
|---|---|
| 1 | haiku/low |
| 2 (ค่าเริ่มต้น) | sonnet/low |
| 3 | sonnet/medium |
| 4 | opus/medium |
| 5 | opus/high |
| 6 | fable/xhigh |

ถ้าต้องการระบุเอง ใช้ `-m opus -e high`

## ผลลัพธ์
- **stdout** มีเฉพาะคำตอบ
- **stderr** มีบรรทัดเดียวในรูป `[บัญชี · รุ่น/ระดับ · เวลา · tokens · ok|FAILED ชนิด]`
- exit code: `0` สำเร็จจริง · `1` งานล้ม (ดูชนิดใน `ERROR (...)`) · `2` ใช้คำสั่งผิด · `3` ไม่มีบัญชีพร้อมหรือบัญชีที่ระบุไม่ได้ล็อกอิน
- สคริปต์ตรวจ `is_error` ให้แล้ว (CLI ตอบ `subtype:"success"` แม้งานล้ม) จึงเชื่อ exit code ได้

## เรียกจากที่ไหน
- **เครื่องของผู้ใช้ (นอก container):** รันคำสั่งข้างบนได้เลย สคริปต์จะ `docker cp` ตัวเองเข้าไปแล้ว `docker exec` ให้ ไฟล์ภาพที่ส่งด้วย `-i` ใช้ path บนเครื่องได้ตามปกติ
  - ต้องมี `docker` และ Python 3
  - ถ้า container ชื่ออื่น ให้ตั้ง `AI_SKILL_CONTAINER`
- **ใน container:** `python3 .../yolo.py ...` (ตรวจเจอ `yolo1..5` แล้วรันตรง)
- ถ้าไม่ใช้สคริปต์ ให้ copy เข้าไปเอง: `docker cp yolo.py multi-account:/tmp/ai-skills/bin/` แล้วรัน `docker exec multi-account python3 /tmp/ai-skills/bin/yolo.py check`
- `--cwd` เป็น path **ใน container** (ค่าเริ่มต้นเมื่อเรียกจากเครื่องคือ `/tmp/ai-skills/work`)

## กฎ
- **ห้าม**เปิดไฟล์ credential เช่น `.credentials.json`, `auth.json`, oauth token และไฟล์ในโฟลเดอร์บัญชี
- **ห้าม**ล็อกอินหรือ logout แทนผู้ใช้
- ถ้าเจอ `not_logged_in` ให้บอกผู้ใช้รัน `docker exec -it multi-account yoloN` เองแล้วพิมพ์ `/login` และไม่ต้องลองซ้ำ
- `check` และ `run` ใช้โควตาจริง ส่วน `quota`, `models`, `stats` ไม่เรียกโมเดล
- ทุกครั้งที่ใช้ `run` หรือ `check` สคริปต์จะจด 1 บรรทัดลง `/root/ai-accounts/.skill-usage/usage.jsonl` (บันทึกกลางที่ใช้ร่วมกันทั้ง 3 สกิล) โดยไม่จดข้อความคำสั่ง คำตอบ หรือ secret

## ข้อควรรู้
- ถ้าไม่ระบุรุ่น CLI จะใช้ Fable ซึ่งแพงและมีโควตา Fable แยก สคริปต์จึงใส่ `--model` ให้ทุกครั้ง
- `quota` แสดง % ที่ใช้ไปพร้อม `data_time` ซึ่งเป็นข้อมูลสด ถ้าไม่มีข้อมูลจะเขียนว่า `no data` และไม่เดา
- `check` มีคอลัมน์ `id` เป็นแฮชของการล็อกอิน (ไม่แสดงอีเมล) ถ้า id ซ้ำกันแปลว่าเป็นบัญชีเดียวกัน
- โหมด auto จะลองบัญชีถัดไปให้เองเมื่อเจอ `rate_limited`, `auth_error` หรือ `not_logged_in`
