---
name: cyolo
description: สั่งงานบัญชี Codex CLI (cyolo1–cyolo5) ใน docker container "multi-account" ได้แก่ ส่ง prompt แบบไม่โต้ตอบ, เลือกบัญชีที่โควตาเหลือมากสุดให้อัตโนมัติ, แปลงความยาก 1–6 เป็นรุ่นและระดับการคิด, สร้างภาพเป็นไฟล์, อ่านไฟล์ภาพ, ตรวจความพร้อม, ดูโควตา, ดูรุ่น และสรุปสถิติการใช้ ใช้เมื่อผู้ใช้ต้องการส่งงานให้ cyolo, Codex หรือต้องการสร้างภาพ
---

# cyolo — Codex CLI (cyolo1–5)

`C = python <โฟลเดอร์สกิลนี้>/scripts/cyolo.py` (ในเครื่องนี้คือ `python C:\t\ma04\b\app\skills\cyolo\scripts\cyolo.py`)

| ต้องการอะไร | ใช้คำสั่งไหน |
|---|---|
| สั่งงาน 1 ครั้ง (เลือกบัญชีที่โควตาเหลือมากสุดให้) | `C run -d 2 "คำสั่ง"` |
| ระบุบัญชีเอง | `C run -a cyolo2 -d 3 "คำสั่ง"` (`-a 2` ก็ได้) |
| prompt ยาวหรืออยู่ในไฟล์ | `C run -d 3 -f prompt.txt` หรือ `type prompt.txt \| C run -d 3` |
| **สร้างภาพเป็นไฟล์** | `C image -o out.png "คำอธิบายภาพ"` |
| ให้อ่านหรือตรวจภาพ | `C run -d 1 -i pic.png "ในภาพมีอะไร"` (ใส่ `-i` ซ้ำได้) |
| ตรวจความพร้อม (เรียกจริงทุกบัญชี) | `C check` |
| ดูโควตาที่ใช้ไป (%) | `C quota` |
| ดูรุ่นที่ใช้ได้และตารางความยาก | `C models` |
| ดูสถิติการใช้ | `C stats` · `C stats --all --since 24` |
| จำกัดให้แตะได้เฉพาะบางบัญชี | ตั้ง `AI_SKILL_ACCOUNTS=cyolo2,cyolo3` ก่อนรัน (บัญชีอื่นจะไม่ถูกเรียกเลย; `AI_SKILL_AUDIT=<ไฟล์>` จดทุกการเรียก) |
| ได้ผลเป็น JSON | เติม `--json` ได้ทุกคำสั่ง |

**ความยาก (`-d`):**

| `-d` | รุ่น/ระดับการคิด |
|---|---|
| 1 | gpt-6-luna/low |
| 2 (ค่าเริ่มต้น) | gpt-6.2-sol/low |
| 3 | gpt-6.2-sol/medium |
| 4 | gpt-6.2-astra/medium |
| 5 | gpt-6.2-astra/high |
| 6 | gpt-6.2-astra/xhigh |

- ถ้ารุ่นที่ต้องการหายไป สคริปต์จะเลือกรุ่นสำรองจาก `C models` ให้เอง
- ถ้าต้องการระบุเอง ใช้ `-m gpt-6.2-sol -e high` (ระดับที่มี: low, medium, high, xhigh, max, ultra)

## ผลลัพธ์
- **stdout** มีเฉพาะคำตอบ หรือ path ของไฟล์ภาพเมื่อใช้ `image`
- **stderr** มีบรรทัดเดียวในรูป `[บัญชี · รุ่น/ระดับ · เวลา · tokens · ok|FAILED ชนิด]`
- exit code: `0` สำเร็จจริง · `1` งานล้ม · `2` ใช้คำสั่งผิด · `3` ไม่มีบัญชีพร้อมหรือบัญชีที่ระบุไม่ได้ล็อกอิน
- คำสั่ง `image` นับว่าสำเร็จเมื่อพบไฟล์ภาพจริงใน `generated_images/<thread>` ของบัญชีแล้ว copy ไปที่ `-o` ได้เท่านั้น

## เรียกจากที่ไหน
- **เครื่องของผู้ใช้ (นอก container):** รันคำสั่งข้างบนได้เลย สคริปต์จะ `docker cp` ตัวเองเข้าไปแล้ว `docker exec` ให้ ไฟล์ที่ส่งด้วย `-i` และ `-o` ใช้ path บนเครื่องได้ สคริปต์ copy เข้าออกให้
  - ต้องมี `docker` และ Python 3
  - ถ้า container ชื่ออื่น ให้ตั้ง `AI_SKILL_CONTAINER`
- **ใน container:** `python3 .../cyolo.py ...`
- ถ้าไม่ใช้สคริปต์ ให้ copy เข้าไปเอง: `docker cp cyolo.py multi-account:/tmp/ai-skills/bin/` แล้วรัน `docker exec multi-account python3 /tmp/ai-skills/bin/cyolo.py check`
- `--cwd` เป็น path **ใน container**

## กฎ
- **ห้าม**เปิดไฟล์ credential (`auth.json` ในโฟลเดอร์บัญชี)
- **ห้าม**ล็อกอินหรือ logout แทนผู้ใช้
- ถ้าเจอ `not_logged_in` ให้บอกผู้ใช้รัน `docker exec -it multi-account cyoloN` เอง
- `check`, `run` และ `image` ใช้โควตาจริง ส่วน `quota` อ่านจาก app-server โดยไม่เรียกโมเดล
- ทุกครั้งที่ใช้ `run`, `image` หรือ `check` สคริปต์จะจด 1 บรรทัดลง `/root/ai-accounts/.skill-usage/usage.jsonl` (บันทึกกลาง) โดยไม่จดข้อความคำสั่ง คำตอบ หรือ secret

## ข้อควรรู้
- cyolo1 กับ cyolo2 เป็นการล็อกอินเดียวกัน (`check` แสดง id ซ้ำ และ `quota` แสดงตัวเลขเหมือนกัน) สลับไปใช้อีกบัญชีจึงไม่ได้โควตาเพิ่ม
- บัญชีที่ไม่ได้ล็อกอิน CLI จะ retry 401 นานราว 30 วินาที สคริปต์ตรวจ `login status` ก่อนจึงจบได้ทันที
- สคริปต์จัดการเรื่องที่พลาดง่ายของ Codex ให้แล้ว:
  - ส่ง prompt ทาง stdin
  - ใส่ `--image=` ไว้เพราะ `-i` แบบธรรมดาจะกลืนอาร์กิวเมนต์ถัดไป
  - ใส่ `--skip-git-repo-check`
  - ไม่ถือ event `Reconnecting...` ว่าเป็นความล้มเหลว
