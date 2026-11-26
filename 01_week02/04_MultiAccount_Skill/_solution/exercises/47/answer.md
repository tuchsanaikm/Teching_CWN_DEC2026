# แบบฝึกหัดที่ 47 · เพิ่มคำสั่งใหม่ให้สกิล

ผลจากการรันจริง 1 ครั้ง ผลของแต่ละคนจะต่างกันไปตามบัญชี รุ่น และวันที่รัน

## พรอมต์

```text
เพิ่มความสามารถเล็ก ๆ ให้สกิล agent-team ในสำเนาสำหรับทดลอง ห้ามแตะที่เก็บสกิลกลางใน container multi-account
1. คัดลอกโฟลเดอร์ ./skills เป็น ./skills-lab แล้วแก้เฉพาะใน ./skills-lab
2. เพิ่มคำสั่งที่สรุปงานครั้งล่าสุดเป็นไฟล์ Markdown 1 ไฟล์ มีเป้าหมาย ตารางงาน (งาน บัญชี รุ่น สถานะ เวลา โทเค็น) และผลของงานสุดท้าย
3. เพิ่มคำอธิบายคำสั่งใหม่ในคู่มือของสกิล
4. ทดสอบในโฟลเดอร์ทดลองใน container ด้วยงานส่งต่อ 2 ทอด ความยาก 1 และยืนยันว่าคำสั่งเดิมยังใช้ได้
สรุป: ไฟล์ที่แก้ · ตัวอย่างรายงานที่คำสั่งใหม่สร้าง · ผลทดสอบ แล้วบอกวิธีติดตั้งสำเนานี้ถ้าผมต้องการใช้จริง
```

## คำตอบของ Claude

ผมเพิ่มคำสั่งใหม่ `team.py report` ใน `./skills-lab` แล้ว และทดสอบใน container ผ่านทั้งหมด ที่เก็บสกิลกลาง (`/root/ai-accounts/.{Claude,Codex,Gemini}/shared/skills/agent-team`) ผมไม่ได้แตะเลย

## ไฟล์ที่แก้ (เฉพาะใน `skills-lab/agent-team/`)

| ไฟล์ | สิ่งที่เปลี่ยน |
|---|---|
| `scripts/team.py` | เพิ่มคำสั่ง `report` (ตัวเลือก `--run <id>`, `--output path.md`, `--print`) · ไฟล์รายงานไปที่ `<run_dir>/final/report.md` · คำสั่งนี้ไม่เรียกโมเดลเลย · คืน 1 เฉพาะเมื่อยังไม่มี run |
| `SKILL.md` | เพิ่มแถวในตารางคำสั่ง, หมายเหตุค่าที่คืน และตัวอย่างการเรียกจาก host |
| `references/details.md` | เพิ่มหัวข้อ "รายงาน run" อธิบายว่าแต่ละส่วนของรายงานมาจากข้อมูลไหน |

"งานสุดท้าย" คือ งานที่ไม่มีงานอื่นรอผล และจบเป็นงานล่าสุด

## ตัวอย่างรายงานที่คำสั่งใหม่สร้าง

ส่งต่อ 2 ทอด yolo1 → cyolo1 → gyolo1 ความยาก 1:

```markdown
# รายงาน run 20261124-060123-akfb
- โหมด: run · สร้างเมื่อ: 2026-11-24 06:01:23 · งานจบล่าสุด: 2026-11-24 06:01:49
- สถานะงาน: ok 3
## เป้าหมาย
ทดสอบส่งต่อ 2 ทอด (yolo -> cyolo -> gyolo) ความยาก 1 สำหรับคำสั่ง report
## ตารางงาน
| งาน | บัญชี | รุ่น | สถานะ | เวลา (s) | โทเค็น |
| start | yolo1 | claude-haiku-5-5/low | ok | 4.1 | 19314 |
| plus | cyolo1 | gpt-6.2-sol/low | ok | 6.0 | 12503 |
| final | gyolo1 | gemini-3.8-flash-low/low | ok | 6.9 | 12858 |
| **รวม** | | | | 17.0 | 44675 |
## ผลของงานสุดท้าย
งาน `final` · สถานะ **ok**
ตัวเลข 500 หารด้วย 10 ลงตัว
ห้าร้อย
```

ไฟล์เต็ม: `(โฟลเดอร์ชั่วคราวของ Claude Code app)`

## ผลทดสอบ

- **ส่งต่อ 2 ทอด:** รันจริง 2 ครั้ง ผลถูกทั้งคู่ (391 → 500 → สรุปภาษาไทย)
  - ครั้งแรก haiku ตอบ `17*23 = 391` จึงไม่ผ่าน `expect: number` และงานถัดไปถูกบล็อก
  - ผมสร้างรายงานของ run ที่ล้มนี้ด้วย รายงานแสดง bad_output/blocked ถูกต้อง
  - จากนั้นแก้โจทย์ด้วย `run --resume --set` แล้วผ่านครบ
- **กรณีอื่นของ `report`:** ยังไม่มี run (คืน 1) และ run แบบ `--dry-run` ที่งานยังเป็น pending ใช้ได้ทั้งสองกรณี
- **คำสั่งเดิมยังใช้ได้:** `run`, `run --resume --set`, `--dry-run`, `--json`, `status`, `stats`, `stats --json`, `check`, `quota`, `board`, `msg` คืนค่าเหมือนเดิมทุกคำสั่ง
- **แยกจากของกลาง:** run ทดลองอยู่ที่ `/workspace/skills-lab-runs` (ใช้ `MA_TEAM_DIR`) และไม่มีแถวไหนเข้า ledger กลาง

## เรื่องที่ควรรู้

- **มี session อื่นทำงานใน container และในโฟลเดอร์นี้พร้อมกัน**
  - เวลา 05:59 มีบางอย่างนอก session นี้อัปเดต `ma_common.py` ของทั้ง 4 สกิล ทั้งในที่เก็บกลางและใน `./skills` และสร้าง `skills-lab/poster-team` ด้วย
  - ผมคัดลอก `ma_common.py` รุ่นใหม่เข้า `skills-lab` แล้วทดสอบซ้ำ เพื่อไม่ให้การติดตั้งย้อนไฟล์นี้กลับเป็นรุ่นเก่า
  - ผมไม่ได้แตะ `poster-team`
- **ผมเคยรัน `rm -rf /workspace/skills-lab` ใน container ตอนติดตั้งซ้ำ (ราว 06:00)** ตอนนี้ `poster-team` ใน container ตรงกับฉบับล่าสุดบน host แต่ถ้า session นั้นเคยวางไฟล์ไว้เฉพาะใน container ไฟล์นั้นอาจหายไปแล้ว หลังจากนั้นผมคัดลอกเฉพาะไฟล์ที่ต้องใช้
- **ผมเผลอสร้างโฟลเดอร์ `/workspace/C:` ใน container** เพราะ Git Bash แปลง path ผิด ในนั้นมีแค่ไฟล์ cache ผมย้ายไฟล์ cache ไปที่ที่ถูกแล้วลบโฟลเดอร์นี้ทิ้ง

## วิธีติดตั้งใช้จริง

คัดลอกแค่ 3 ไฟล์ของ agent-team อย่าคัดลอกทั้ง `skills-lab` เพราะ `poster-team` ไม่ใช่งานของผม ควรติดตั้งตอน session อื่นไม่ได้รันงานอยู่ ใช้ Git Bash ที่ `./`:

```bash
export MSYS_NO_PATHCONV=1
# 1) ตรวจว่า team.py กลางยังเป็นรุ่นที่ผมแก้ต่อ (ต้องได้ 2ec4b571a8bba81cdee58c453b8d72b4) ถ้าไม่ตรงต้อง merge ก่อน
docker exec multi-account md5sum /root/ai-accounts/.Claude/shared/skills/agent-team/scripts/team.py
# 2) สำรองไว้นอก shared/skills แล้วติดตั้งให้ครบ 3 ฝั่ง
for s in .Claude .Codex .Gemini; do
  d=/root/ai-accounts/$s/shared/skills/agent-team
  docker exec multi-account sh -c "mkdir -p /root/skill-backup/$s && cp -a $d /root/skill-backup/$s/"
  docker cp skills-lab/agent-team/scripts/team.py       multi-account:$d/scripts/team.py
  docker cp skills-lab/agent-team/SKILL.md              multi-account:$d/SKILL.md
  docker cp skills-lab/agent-team/references/details.md multi-account:$d/references/details.md
done
# 3) ตรวจ แล้วอัปเดตสำเนาบน host ให้ตรงกัน
docker exec multi-account python3 /root/ai-accounts/.Claude/shared/skills/agent-team/scripts/team.py report --print
cp skills-lab/agent-team/scripts/team.py skills/agent-team/scripts/
cp skills-lab/agent-team/SKILL.md skills/agent-team/
cp skills-lab/agent-team/references/details.md skills/agent-team/references/
```

ถ้าต้องย้อนกลับ ให้คัดลอกจาก `/root/skill-backup/<ฝั่ง>/agent-team` กลับที่เดิม โฟลเดอร์ทดลอง `/workspace/skills-lab` และ `/workspace/skills-lab-runs` ใน container ลบได้หลังติดตั้ง แต่ `skills-lab-runs/poster-team-v0` เป็นของ session อื่น ห้ามลบ
