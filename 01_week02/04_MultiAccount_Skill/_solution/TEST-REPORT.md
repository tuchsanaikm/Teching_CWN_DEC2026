# TEST-REPORT — สกิล yolo · cyolo · gyolo · agent-team (3 CLI)

- วันที่ 2026-11-23 (เวลา container UTC+7) · container `multi-account` · Claude Code 2.1.330 · codex-cli 0.171.0 · Antigravity CLI (agy) 1.5.15 · Python 3.12.3
- โค้ดที่ทดสอบ: สำเนาที่ `/workspace/skill-test/skills/{yolo,cyolo,gyolo,agent-team}` (จากโฟลเดอร์ต้นฉบับของสกิล) · `ma_common.py` md5 เดียวกันทั้ง 4 สกิล · **ไม่ได้แตะ** `/root/ai-accounts/.{Claude,Codex,Gemini}/shared/skills`
- บัญชีที่เรียก: yolo2, yolo3 (เบา), cyolo1, cyolo2, gyolo1, gyolo2
- ไม่ได้ล็อกอิน: yolo4, yolo5, cyolo3–5, gyolo3–5 (ไม่ได้ล็อกอินแทน ไม่ได้อ่านไฟล์ credential/token)
- รุ่นที่ใช้ทดสอบ: difficulty 1 แทบทั้งหมด (haiku/low · gpt-6.2-sol/low · gemini-3.8-flash-low) ยกเว้นหัวหน้าทีม (sonnet/medium, sol/medium, flash-medium), ผู้ตัดสินภาพ (sonnet/medium), การวัดรุ่น Gemini และ code review (gemini-4-carbon-high)
- สคริปต์ทดสอบ/กราฟอยู่ในโฟลเดอร์สคริปต์ทดสอบ และ log ทุกตัวที่ `/workspace/skill-test/logs/<ชื่อ>.log`

## 1. Regression — รายการ "ทดสอบใน container" ของสกิลรุ่นก่อน

| # | รายการ | ผล | หลักฐาน | เวลา |
|---|---|---|---|---|
| R1 | คัดลอกโฟลเดอร์แล้วทุกบัญชีเห็นสกิล | **ไม่ได้ทดสอบตามสเปก** | ทดสอบบนสำเนาแยกและไม่ได้แก้ไขโฟลเดอร์ shared skills จึงไม่ได้คัดลอกสกิลใหม่ไป 3 ที่ · ตรวจกลไกฝั่งใหม่แทน: `~/.gemini/config/skills/shared-check` ของ gyolo2 เป็น symlink ไป `.Gemini/shared/skills/shared-check` และ gyolo2 ตอบรายชื่อสกิลของตัวเองว่ามี `shared-check` | 9s |
| R2 | ตรวจความพร้อมด้วยการเรียกจริง แยกสถานะ | PASS | `team.py check --workers yolo2,yolo4,cyolo1,cyolo3,gyolo1,gyolo2,gyolo3` → พร้อม 4 / ไม่ได้ล็อกอิน 3 (ทั้ง 3 CLI) · `check yolo3 --json` shape เดิม · สถานะ "หมดอายุ/ใช้ไม่ได้" ไม่มีบัญชีจริง ทดสอบที่ตัวจำแนกด้วยผลจำลอง (N3) | 12s |
| R3 | งานเดียว Claude + Codex ผลถูก + ledger ครบฟิลด์ | PASS | `yolo.py run -a yolo2 -d 1` และ `cyolo.py run -a cyolo1 -d 1` ตอบ 861 (123*7) · ทุก 193 แถวเรียกใน ledger มีครบ 19 ฟิลด์เดิม (+`real_model`) | 8s |
| R4 | relay 3 ทอด 42 → 142 → 426 | PASS | `relay_old.json` yolo2 → cyolo1 → yolo3 ได้ `42, 142, 426` · มี `msgs/a__b.md` `msgs/b__c.md` | 22s |
| R5 | fan-out 3 บัญชี + fan-in | PASS | `fanout3.json` yolo2/cyolo1/gyolo1 ได้ Jupiter/Mercury/Saturn → cyolo2 รวมเป็น JSON (`expect: json` ผ่าน) | 25s |
| R6 | ข้อมูลยาวผ่าน `{{file:node}}` | PASS | ดู N5 (Claude 120 บรรทัด → Gemini นับ 120 · Gemini 150 บรรทัด → Codex นับ 150 · นับเองด้วย grep ตรงกัน) | 39s |
| R7 | review loop จบด้วย APPROVED | PASS | worker cyolo2 + reviewer **gyolo2** → `APPROVED รอบ 1 โดย gyolo2` (max_rounds 3) | 61s (รวม R10) |
| R8 | board | PASS | ดู N6 (gyolo1 เขียน `service_port=8731` → yolo3 ตอบ 8731) | 24s |
| R9 | สถิติรวมตรงกับ ledger | PASS | `stats_check.py`: แถวรวมของทั้ง 3 ตาราง `stats --all` = ผลรวมจาก ledger (193 ครั้ง, 174 สำเร็จ, input 5,608,813, cached 7,269,481, cache_write 711,000, output 44,017, reasoning 14,776, $0.7079) | <1s |
| R10 | debate + best-of-N พร้อมเหตุผลผู้ตัดสิน | PASS | debate `accounts: [yolo, gyolo]` ผู้ตัดสิน cyolo1: `{"winner":"both","answer":"25",...}` · best_of yolo2/cyolo1/gyolo1 ผู้ตัดสิน gyolo2 (ไม่ซ้ำผู้ตอบ) คะแนน A7 B9 C10 พร้อมเหตุผล | 61s |
| R11 | router + failover (`--simulate-limit`) | PASS | router (`--dry-run`): image→cyolo1, vision→gyolo1, review→cyolo2, code→cyolo1, doc→yolo2 · failover เดิม: review บน cyolo1 จำลองโควตาหมด → ย้ายไป cyolo2 + `worker_switch` · ฝั่ง gyolo ดู N9 | 16s |
| R12 | human gate | PASS | `deploy` ค้าง `waiting_approval` จนสั่ง `team.py approve t-gate deploy` (30 วินาทีต่อมา) แล้วได้ 101 | 37s |
| R13 | งบโทเค็นลูกทีม | PASS | ฝั่ง gyolo: `--worker-token-budget gyolo1=1 --per-account 1` → q1 บน gyolo1 จบปกติ (121) แล้ว gyolo1 หยุดรับงาน q3 ในคิวย้ายไป gyolo2 · `status` แสดง `หยุดรับงาน (เกินงบโทเค็นลูกทีม (9398 > 1))` | 42s |
| R14 | สลับหัวหน้าเชิงรุก | PASS | `--leader yolo2 --lead-token-budget yolo2=1` → `สลับหัวหน้าเชิงรุก: yolo2 → cyolo1 (17833 > 1)` cyolo1 ทำต่อจนจบ 225/1024/63 · (รอบแรกใช้หัวหน้า Codex งบ 1 แล้วไม่เกิดการสลับ — ดูหมายเหตุ ก) | 58s |
| R15 | สลับหัวหน้าเชิงรับ | PASS | `--simulate-crash yolo2` → yolo2 ถูก kill หลังสั่ง 3 งาน → cyolo2 อ่าน handoff ทำต่อจนจบ · exit 1 เพราะลูกทีม haiku ตอบ `15*15 = 225` ไม่ผ่าน `expect=number` หัวหน้าสั่ง `q1-retry` ได้ 225 (exit 1 ถูกตามกติกาเดิม) | 68s |
| R16a | `lead --demo` ครบ 3 เหตุการณ์ | PASS | workers yolo2,yolo3,cyolo1,gyolo1: เชิงรับ yolo2→yolo3 · เชิงรุก yolo3→cyolo1 · ย้ายงาน q1 yolo2→yolo3 · yolo3 หยุดรับงาน · ผล 391/4096/1275/10 ถูกทุกข้อ (ลูกทีมรวม gyolo1) · ซ้ำอีกครั้งจาก host (R17) ได้ครบเหมือนกัน | 63s |
| R16b | `--demo --goal` ใหม่ | PASS (บางส่วน) | เป้าหมายคู่มือดูแลแมว 3 หัวข้อ → `final/cat.md` ครบ · เกิดเชิงรับ + ย้ายงาน + หยุดรับงาน แต่**ไม่เกิดเชิงรุก** เพราะ workers ชุดนั้นมี Claude ตัวเดียว หัวหน้าคนที่ 2 จึงเป็น Codex (หมายเหตุ ก) | 71s |
| R17 | เรียกจาก host ทุกบรรทัดใน SKILL.md | PASS | **Git Bash บน Windows จริง** ไม่ตั้ง MSYS_NO_PATHCONV: 25 บรรทัดจาก 4 SKILL.md exit 0 ทั้งหมด (รวมกราฟตัวอย่าง → `fix = OK`, `lead --demo`) · **PowerShell 5.1**: 6 บรรทัด (cat, check, run อาร์กิวเมนต์ภาษาไทย, quota, stats, pipe กราฟ `--dry-run`) ทำงาน · ข้อต่างจากเอกสารที่จำเป็น: path สกิลเป็น `//workspace/skill-test/skills`, yolo1→yolo2 | ~6 นาที |
| R18 | `run` จบด้วยตาราง + `--resume` เฉพาะงานที่ล้ม | PASS | b (gyolo1) `expect=contains:ผลลัพธ์คือ` → `bad_output`, c `blocked` → `--resume --set b.expect=int` → 42/142/426 · ledger ของ run มีแถว a แถวเดียว | 44s |
| R19 | ทดสอบแบบผู้ใช้จริง | PASS (1 แบบ จาก 3) | yolo2 sonnet อ่านเฉพาะ SKILL.md แล้วทำโจทย์ใหม่: fan-out 3 CLI + debate Claude vs Gemini + ภาพป้ายพร้อมตรวจข้าม CLI → 6 tool calls, **0 คำสั่งล้ม**, ไม่เปิด scripts/references · ได้ Ember/Daybreak/Crema, 3^13 = 1594323, ภาพ ACCEPT รอบ 1 · ต้อง resume 1 ครั้งเพราะ haiku ตั้งชื่อเป็นภาษาไทย (ผู้ใช้แก้ prompt เอง) · แบบ (ก) และ (ข) ของสกิลรุ่นก่อนไม่ได้รันซ้ำ (ครอบคลุมโดย R16 และกราฟตัวอย่างใน R17) | 150s |
| R20 | ภาพผ่าน cyolo เป็น PNG จริง | PASS | `cyolo.py image … --out /workspace/skill-test/tdata/blue.png` 8 ไบต์แรก `\211PNG\r\n\032\n` | 24s |
| R21 | กราฟที่ระบุบัญชีเจาะจงไม่เรียกบัญชีอื่น | PASS | relay_old: รายชื่อที่อนุญาต/ตรวจ และ ledger ของ run = `cyolo1, yolo2, yolo3` เท่านั้น | (ใน R4) |

## 2. ทดสอบใหม่

| # | รายการ | ผล | หลักฐาน | เวลา |
|---|---|---|---|---|
| N1 | gyolo งานเดียว + แถว ledger | PASS | `gyolo.py run "123*7…" -a gyolo1 -d 1` → 861 · แถว: `cli gemini, model gemini-3.8-flash-low, effort low, input 9227, cached 0, output 3, reasoning 0, cost_usd null, status ok` | 7s |
| N2 | gyolo check: พร้อม vs ไม่ได้ล็อกอิน | PASS | `gyolo.py check` → gyolo1/gyolo2 พร้อม (6.6s/7.3s), gyolo3–5 ไม่ได้ล็อกอิน (`models: Please sign in`) ใน 9s รวม · ยืนยัน gyolo2 แยกด้วย `check` ของสกิล → พร้อม | 9s |
| N3 | สถานะอื่นของ gyolo (ตัวจำแนก) | PASS | `unit_gemini.py` ใช้ผล agy จำลอง: RESOURCE_EXHAUSTED→limit · UNAUTHENTICATED→auth_expired → check "ล็อกอินแล้วแต่ใช้ไม่ได้" · print_timeout→timeout · ข้อความ sign-in→not_logged_in · timeout จริง (`--timeout 3`) → `timeout after 3s` · `-p` บนบัญชีไม่ล็อกอินจริง (gyolo3) → not_logged_in ใน 1.2s (agy เองรอ 60s) | <10s |
| N4 | gyolo quota + เวลาของข้อมูล | PASS | `gyolo.py quota` → gyolo1 session 1% · week 2% (แปลงจาก remaining 99%/98%) พร้อม reset และเวลาของข้อมูล · `--json` มี `groups` ทั้งกลุ่ม Gemini และ Claude/GPT · บัญชีไม่ล็อกอิน: "ไม่มีข้อมูลโควตา (ไม่ได้ล็อกอิน)" | 9s |
| N5 | relay 3 CLI + relay ที่เริ่มจาก gyolo | PASS | yolo2→cyolo1→**gyolo1** = 42/142/426 · **gyolo2**→yolo3→cyolo2 = 42/142/426 | 28s / 32s |
| N6 | fan-out 1 บัญชีต่อ CLI + fan-in | PASS | ดู R5 | 25s |
| N7 | `{{file:node}}` ข้าม CLI | PASS | yolo2 เขียน 120 บรรทัด → gyolo1 นับจากไฟล์ = 120 · gyolo2 เขียน 150 บรรทัด → cyolo1 นับ = 150 · `grep -c` บนไฟล์ผลได้ 120 / 150 | 39s |
| N8 | board ที่ gyolo เขียนแล้ว Claude ใช้ | PASS | `board.md`: `[… · find@gyolo1] service_port=8731` → yolo3 (ไม่รู้ path config) ตอบ 8731 | 24s |
| N9 | router: ตรวจภาพ → gyolo · สร้างภาพ → cyolo | PASS | `--dry-run`: `look (kind vision) → gyolo1`, `gen (type image) → cyolo1` · ในกราฟภาพ+ตรวจ ผู้ตรวจที่ router เลือกเป็น gyolo1/gyolo2 ทุกรอบ | 13s |
| N10 | failover ของงาน gyolo (`--simulate-limit gyolo1`) | PASS | **ฝั่งเดียวกันก่อน** (workers มี gyolo2): งาน any+vision gyolo1→**gyolo2** บันทึก `worker_switch` · งาน `account: gyolo` ไป gyolo2 · **ข้ามฝั่ง** (workers ไม่มี gyolo2): งาน any → **cyolo1** (`worker_switch` gyolo1→cyolo1) · งาน `account: gyolo` ล้ม (ไม่มี gyolo อื่น) · งาน `account: gyolo1` (เจาะจง) ทั้งสองกรณี: ล้มพร้อม `บัญชี gyolo1 ที่ผู้ใช้ระบุล้ม (limit) ไม่ย้ายอัตโนมัติ` | 22s |
| N11 | ภาพ + ตรวจข้าม CLI: ผ่านรอบ 1 | PASS | `red`: cyolo1 สร้าง → gyolo1 `PASS` → yolo2 `ACCEPT` · ไฟล์ `out/red.r1.png` `red.r1.check.md` `red.judge.md` · คัดลอกไป `path` · ledger `red#g1 red#c1 red#judge` · งานถัดไปได้ `{{red}}` = path | 141s (ทั้งกราฟ) |
| N12 | ภาพ + ตรวจ: FAIL แล้วสร้างใหม่ | PASS | `sign` (prompt ไม่บอกข้อความ, เกณฑ์ต้องมี `OPEN 9AM-5PM`): รอบ 1 gyolo2 `FAIL` + คำสั่งแก้ ("เพิ่มข้อความ OPEN 9AM-5PM…") → ส่งเป็นคำสั่งรอบ 2 ให้ cyolo2 → รอบ 2 gyolo1 `PASS` → yolo2 `ACCEPT` · เปิดดูภาพเองแล้ว: r1 ไม่มีข้อความ, r2 มี `OPEN 9AM-5PM` ถูกต้อง | (ใน N11) |
| N13 | กราฟ Claude+Codex เท่านั้น ไม่เรียก gyolo | PASS | `sides_only.json` (ฝั่ง yolo/cyolo, `--recheck`): บัญชีที่อนุญาตและที่ตรวจมีแต่ yolo/cyolo · แถว ledger กลางในช่วงเวลานั้น 5 แถว gemini 0 แถว · relay_old/fo_old ก็ไม่มีแถว gemini · (งาน a ของกราฟนี้เป็น bad_output เพราะ haiku ตอบ `3*3 = 9` ไม่ใช่ปัญหาของการเลือกบัญชี) | 17s |
| N14 | dag-planner ใช้ team.py ใหม่โดยไม่แก้ | PASS | คัดลอก dag-planner ไว้ข้าง 4 สกิลใหม่ (`/workspace/skill-test/dagtest/skills`) · `doctor` ✅ (team.py check ใหม่) · `dag` · `plan --accounts …:%` (สมมติ ไม่เรียก team.py) · `export` (`team.validate_graph` ของใหม่) exit 0 ทั้งหมด · `plan` แบบโควตาจริงก็ exit 0 (ดูปัญหาที่เปิดอยู่ 1) | 10s + 24s |
| N15 | gyolo ดูภาพ (`--image`) | PASS | gyolo2 flash-low อ่านป้ายใน `sign.r2.png` ได้ `OPEN 9AM-5PM` | 15s |
| N16 | หัวหน้าทีมเป็น gyolo | PASS (จำกัด) | `lead --leader gyolo1 --succession gyolo1 --workers gyolo2,cyolo2`: gyolo1 (flash-medium) ใช้ `status/dispatch/wait/checkpoint/finish` ได้จริง (checkpoint 3 ครั้ง) สั่งงานใหม่เองเมื่อ 2 งานล้ม แล้วเขียน `final/result.md` ถูก 225/1024/63 · ใช้ 260s · exit 1 เพราะ 2 งานแรกล้มด้วยบั๊กการอ่าน models_cache ของ Codex (แก้แล้ว ดูหมายเหตุ ข) · ไม่ได้ทดสอบการสลับหัวหน้าเข้า/ออกจาก gyolo | 273s |
| N17 | gyolo หลาย `-p` พร้อมกัน | PASS | gyolo1 รัน 3 ตัวพร้อมกัน ถูกทั้ง 3 (5.9/6.9/8.3s, รวม 8s) · gyolo1 + gyolo2 ขนานกัน 5.7/6.4s | 14s |
| N18 | gyolo สร้างภาพ (ตรวจซ้ำด้วยรุ่นแรงกว่า) | ยืนยันว่าใช้ไม่ได้ | gemini-4-hydrogen-high: agy เรียก subagent `image-generator` (gemini-3.1-flash-image) แต่ล้ม 2 ครั้ง HTTP 503 no capacity ตอบ CANNOT ไม่มีไฟล์ | 74s |
| N19 | review ที่ reviewer เจาะจงบัญชีใช้ไม่ได้ (หลังแก้ตาม review ข้อ 1) | PASS | `reviewer: gyolo3` (ไม่ล็อกอิน) worker gyolo1 → `⛔ rv#r1: บัญชี gyolo3 ที่ผู้ใช้ระบุ ใช้ไม่ได้ … ไม่ย้ายอัตโนมัติ` จบใน 33s (โค้ดเดิมกรณีนี้วนไม่รู้จบ) | 33s |
| N20 | กราฟ Claude+Codex เดิมที่มี node ภาพ `account: any` ไม่ดึง gyolo (หลังแก้ตาม review ข้อ 2) | PASS | `--dry-run`: บัญชีที่อนุญาต/ตรวจ = yolo2–5, cyolo1–5 เท่านั้น · แผน img→cyolo1 | 16s |

## 3. Code review โดย gyolo1 (gemini-4-carbon-high)

ส่ง path ของ `team.py` `ma_common.py` `gyolo.py` (ใหม่) และ `team.py` `ma_common.py` (เดิม) ให้ตอบเป็นรายการตัวเลข ห้ามแก้ไฟล์ · ใช้ 1,187 วินาที (input 641,649 · cache read 1,873,909 · output 77,932 · thinking 67,345) · ได้ 15 ข้อ ไม่มีการแก้ไฟล์

| # | ข้อค้นพบ | ตัดสิน | สิ่งที่ทำ |
|---|---|---|---|
| 1 | sub-role (checker/judge/reviewer) ที่เจาะจงบัญชีที่ใช้ไม่ได้ → `acquire_slot` ตอบ "stopped" แล้ว `choose` คืนบัญชีเดิม → วนไม่รู้จบ | รับ (มีในโค้ดเดิมด้วย) | `acquire_slot(..., pinned=)` ใช้ spec ของการเรียกนั้น · ถ้าเลือกใหม่ได้บัญชีเดิมให้หยุด · ทดสอบ N19 |
| 2 | node ภาพ `account: any` ทำให้ pool ขยายเป็น 3 ฝั่ง → กราฟ Claude/Codex เดิมไปตรวจ gyolo | รับ (ผิดเงื่อนไข compat) | `node_accounts`: ภาพที่ไม่ระบุบัญชี = `cyolo` · ทดสอบ N20 |
| 3 | `_run_agy` ทิ้งบรรทัด stderr ที่มี URL รวมถึง `AGY_ERROR` | รับ | ตัดเฉพาะ URL (`[url]`) ยกเว้นบรรทัด sign-in ที่ทิ้งทั้งบรรทัด |
| 4 | `prefer_side` ไม่ย้ายฝั่งเดิมขึ้นหน้าเมื่ออยู่ใน order แล้ว · การย้ายจาก stop/ใช้ไม่ได้ ไม่ใช้กฎฝั่งเดียวกันก่อน | รับ | ย้ายฝั่งเดิมขึ้นหน้าเสมอ และใส่ `prefer_side` ใน `stop_account`, `re_choose`, `pre` |
| 5 | `_verdict` จับคำแบบ substring (`PASSING`, `UNACCEPTABLE`) · ผู้ตัดสินภาพอาจเป็นผู้สร้าง | รับ | จับทั้งคำ ข้อความกำกวมถือเป็น FAIL/REJECT · ผู้ตัดสินเลี่ยงทั้งผู้ตรวจและผู้สร้าง |
| 6 | หัวหน้า Gemini/Codex ไม่มี tokens สด → งบหัวหน้าไม่ทำงานกลางรอบ · `or True` ในตัวหน่วง | ปฏิเสธ (บันทึกเป็นข้อจำกัด) | พฤติกรรมเดิมของหัวหน้า Codex · agy json ไม่มี event ระหว่างรอบ · เขียนไว้ใน references · `or True` เป็นโค้ดเดิม ไม่แตะ |
| 7 | ผู้ตรวจ/ผู้ตัดสินที่ไปตก Codex ไม่ได้แนบภาพ `-i` · PNG เก่าจากรอบก่อนถูกนับว่าใหม่ | รับ | `call_on(images=)` ส่ง `-i` ให้ Codex และภาพให้ gyolo · ภาพต้องถูกเขียนหลังเริ่มเรียก (mtime) |
| 8 | `_kill` ส่งแค่ SIGTERM | รับ | SIGKILL ตามหลัง 5 วินาทีถ้ายังไม่ตาย |
| 9 | `gemini_check` ตีทุกความล้มเหลวเป็น "ล็อกอินแล้วแต่ใช้ไม่ได้" | รับบางส่วน | timeout/ไม่รู้สถานะล็อกอิน → `error` · not_logged_in เมื่อ `models` ไม่ผ่าน · ที่เหลือ (ล็อกอินแล้ว) → `unusable` |
| 10 | `_LIMIT_RE` จับ `exceeded` ทั่วไป (context length) → failover ผิด | ปฏิเสธ | regex เดิม การแคบลงเสี่ยงพลาดข้อความโควตาจริงของ Claude/Codex · บันทึกเป็นปัญหาที่เปิดอยู่ |
| 11 | `gyolo.py` เลือกบัญชีโดยไม่มีข้อมูลโควตา · `--schema` ไฟล์ · ไม่ตรวจชื่อบัญชี | รับข้อแรก ปฏิเสธที่เหลือ | ถ้ามีหลายบัญชีพร้อมและไม่มีโควตาใน cache เรียก `/usage` ก่อน · `agy --json-schema` รับ path ไฟล์ได้เอง (ตาม `--help`) · yolo/cyolo เดิมก็ไม่ตรวจชื่อ |
| 12 | `-m <ตระกูล>` ไม่มี effort ตอนไม่มีรายชื่อรุ่น · ตัวจำลองโควตาหมดยังเรียก `models` | รับ | ตระกูลไม่มี effort ใช้ effort ตามความยาก · จำลองแล้วไม่แตะ CLI |
| 13 | `--leader` ไม่อยู่ในรายชื่อที่ตรวจ · `pick_leader` ถือ 0% เป็น 50% | รับ 2 ข้อนี้ | เพิ่ม `--leader` ในรายชื่อตรวจ · แก้ `or 50` · ผู้สืบทอด gyolo อัตโนมัติไม่ทำ (ตั้งใจให้ Claude/Codex) |
| 14 | `--set x.check=true` เป็นสตริง · resume ไม่คำนวณ pool ใหม่ | รับข้อแรก | `check` รับ `true/1` · cast `check_difficulty`/`judge_difficulty` · pool ตอน resume เป็นพฤติกรรมเดิม ไม่แตะ |
| 15 | `check.json` เขียนไม่ atomic · reset เป็น None · `%` ทศนิยม · ไฟล์เป็น CRLF | รับ 3 ข้อแรก ปฏิเสธข้อสุดท้าย | lock + `os.replace` · `-` แทน None · parse ทศนิยม · ตรวจแล้วทุกไฟล์เป็น LF (ข้อนี้ผิด) |

## 4. รันซ้ำหลังแก้ตาม review (โค้ดสุดท้าย)

กราฟหลักรันใหม่ด้วยโค้ดสุดท้าย (run id `f-*`): relay3, relay3g, relay_old, failover ฝั่งเดียวกัน/ข้ามฝั่ง/เดิม, budget, ภาพ+ตรวจ (red PASS รอบ 1 · sign FAIL→PASS รอบ 2 · ACCEPT ทั้งคู่), review+debate+best_of, `{{file:node}}`, board, resume, `lead --demo` (ครบ 3 เหตุการณ์), sides_only (gemini 0 แถว), dag-planner (doctor/dag/plan สมมติ/export), unit_gemini และ `stats_check` (277 แถว ตรงกันทั้ง 3 ตาราง ไม่มีแถวขาดฟิลด์) — ผลตรงกับรอบแรกทุกข้อ · yolo1 ใน ledger = 0 แถว
ไม่ได้รันซ้ำหลังแก้: host lines (Git Bash/PowerShell), ผู้ใช้จริง (R19), หัวหน้า gyolo (N16), check/quota ของ gyolo.py ทั้งชุด, การวัดรุ่น

## สรุปจำนวน

- Regression 22 รายการ: PASS 19 · PASS บางส่วน 2 (R16b ไม่เกิดเชิงรุกเพราะชุดบัญชี, R19 รันแบบเดียว) · ไม่ได้ทดสอบ 1 (R1 ไม่ได้แก้ไขโฟลเดอร์ shared)
- ใหม่ 20 รายการ: PASS 19 · ยืนยันข้อจำกัด 1 (N18 gyolo สร้างภาพไม่ได้)
- **FAIL: 0** (บั๊กที่เจอระหว่างทาง แก้แล้วและรันซ้ำผ่าน: อ่าน models_cache ของ Codex ระหว่างถูกเขียน, การนับ input ของ agy, และข้อที่รับจาก review)

## หมายเหตุ

- ก. หัวหน้าที่เป็น Codex (และ gyolo) ไม่มี stream tokens ระหว่างรอบ งบหัวหน้า (`--lead-token-budget`) จึงตรวจได้หลังจบรอบเท่านั้น ถ้าหัวหน้า Codex ทำงานเสร็จในรอบเดียวจะไม่เกิดการสลับเชิงรุก — เป็นพฤติกรรมเดิมของโค้ดเก่า (ไม่ได้เปลี่ยน) การสาธิตครบ 3 เหตุการณ์ต้องมีบัญชี Claude ที่พร้อมอย่างน้อย 2 บัญชี
- ข. บั๊กที่พบและแก้ระหว่างทดสอบ: (1) รันขนานหลาย run แล้ว `models_cache.json` ของ Codex ถูกเขียนทับขณะอ่าน → `codex_models` ได้รายการว่าง → model `None` → `TypeError` (โค้ดเดิมก็เป็น) แก้: อ่านซ้ำ 3 ครั้ง, ใช้ cache ของบัญชี Codex อื่นแทน, และถ้ายังไม่มีรุ่นจะไม่ส่ง `-m` (ให้ Codex ใช้ค่าเริ่มต้น) (2) `input_tokens` ของ agy ไม่รวม cache read (เห็นชัดจากรอบที่ cache 47k > input 23k) ตอนแรกสคริปต์ลบ cache ออกเหมือน Codex จึงแก้ให้นับแบบ Claude (3) รายชื่อรุ่น Gemini ของบัญชีหนึ่งใช้แทนอีกบัญชีได้ (บัญชีที่ไม่ล็อกอินไม่ต้องเรียก `models` ซ้ำ)
- ค. haiku 5.5 ระดับ low ตอบรูปแบบ `3*3 = 9` แทนตัวเลขล้วน 3 ครั้งจากหลายสิบครั้ง (`expect` จับได้ตามออกแบบ) ไม่ได้เปลี่ยนตัวตรวจ `expect`
- ง. gyolo1 และ gyolo2 แสดงโควตาเท่ากันทุกครั้งและเวลารีเซ็ตเดียวกัน — น่าจะล็อกอินด้วยบัญชี Google เดียวกัน (ไม่ได้ตรวจอีเมลบัญชี) ถ้าเป็นเช่นนั้น การกระจายงานไป 2 บัญชีไม่ได้เพิ่มโควตา

## 5. งานเพิ่ม: gyolo สร้างภาพได้ (2026-11-23)

สิ่งที่เปลี่ยน: `gyolo.py image` (ใหม่) · `ma_common.call_gemini_image` · agent-team: node `image` ให้ฝั่ง gyolo สร้างได้ (`any` = Codex ก่อน, gyolo เมื่อไม่มี Codex ที่ใช้ได้ · `gyolo` = Gemini สร้าง ล้มแล้วย้ายไป Codex · `gyolo1` เจาะจง = ล้มพร้อมเหตุผล) · เอกสาร 3 สกิล

| # | รายการ | ผล | หลักฐาน | เวลา |
|---|---|---|---|---|
| G1 | `gyolo.py image` ของจริง (gyolo2 และ gyolo1) | ล้มชัดเจนตามที่ออกแบบ | agy เรียก subagent `image-generator` แล้วตอบ `IMAGE_FAILED: transport error (Unavailable, HTTP 503): No capacity available for model gemini-3.1-flash-image on the server` → `status: image_unavailable`, `png_ok: false`, exit 1, ไม่มีไฟล์ · แถว ledger status `image_unavailable` · agy เองรายงาน `status: SUCCESS` (ข้อผิดพลาดอยู่ในข้อความคำตอบ) | 25s / ~25s |
| G2 | ตัวประมวลผลผลลัพธ์ภาพ (ผล agy จำลอง ไม่มีการเรียกโมเดล) | PASS 5/5 | `unit_gimage.py`: 503 → image_unavailable · ไฟล์ที่ path → ok · agy บอก path อื่น → คัดลอกมา ok · ไฟล์ใหม่ในโฟลเดอร์บัญชี → คัดลอก ok · อ้างว่าสำเร็จแต่ไม่มีไฟล์ → bad_output | <1s |
| G3 | node ภาพ `account: gyolo` (ไม่เจาะจง) → ย้ายไป Codex | PASS | `g2-side3`: gyolo2 → `image_unavailable` (503) → `worker_switch gyolo2 → cyolo2` พร้อมข้อความเซิร์ฟเวอร์ → cyolo2 ได้ PNG (signature ตรวจแล้ว) · ครั้งแรก `g2-side` (gyolo1→cyolo1) ก็ผ่าน | 72s |
| G4 | node ภาพเจาะจง `gyolo1` | PASS | `g2-pinned`: failed `บัญชี gyolo1 ที่ผู้ใช้ระบุล้ม (image_unavailable) ไม่ย้ายอัตโนมัติ: IMAGE_FAILED: … HTTP 503 …` ไม่มีการย้าย ledger ของ run มีแค่ gyolo1 | 36s |
| G5 | node ภาพแบบเดิม (`account` ไม่ระบุ) + งาน Claude ไม่มี `--workers` | PASS | `g2-old2`: บัญชีที่อนุญาต/ตรวจ = yolo2–5, cyolo1–5 · img → cyolo1 PNG · ledger ของ run = cyolo1, yolo2 (gemini 0) · รันซ้ำทับ path เดิมได้เหมือนโค้ดเก่า | 50s |
| G6 | ภาพ + ตรวจ ที่ขอให้ Gemini สร้าง | PASS | `g2-check2`: `star#g1` gyolo1 503 → ย้ายไป cyolo1 → ผู้ตรวจ gyolo2 (ไม่ใช่ผู้สร้าง) PASS → yolo2 ACCEPT · ไฟล์ `star.r1.png` `star.r1.check.md` `star.judge.md` | 101s |
| G7 | stats check | PASS | 340 แถว ตรงกันทั้ง 3 ตาราง ไม่มีแถวขาดฟิลด์ · ledger กลางถูกสร้างใหม่ตอน 22:17 และมีงานของ run อื่นปนอยู่ (แถว yolo1 75 แถวมาจาก run อื่น เช่น `bench-*`; run `g2-*` ของงานนี้มี yolo1 0 แถว) | <1s |

ระหว่างทดสอบพบว่าการตรวจ "ไฟล์ต้องถูกเขียนระหว่างการเรียก" ที่เพิ่มใน `call_on` (จาก code review ข้อ 7) ทำให้กราฟเดิมที่รันซ้ำทับ `path` เดิมล้ม (Codex เห็นไฟล์เดิมแล้วไม่สร้างใหม่) จึงถอยกลับเป็นพฤติกรรมเดิม และย้ายการกันภาพเก่าไปที่ flow ภาพ+ตรวจแทน (ลบไฟล์ของรอบก่อนสร้าง) · `gyolo.py image` ยังตรวจว่าไฟล์ถูกเขียนระหว่างการเรียก

ยังยืนยันไม่ได้เพราะ 503: ทางสำเร็จจริงของ Gemini (agy บันทึกไฟล์ที่ path ที่สั่งเองหรือไว้ที่อื่น, ต้องคัดลอกหรือไม่, ขนาด/เวลา), ไม่ได้วาดด้วยโค้ดแทนจริงหรือไม่, และ node ภาพที่ Gemini สร้างสำเร็จแล้วส่งต่อให้ผู้ตรวจ

## 6. งานเพิ่ม: ทางสำเร็จของ gyolo สร้างภาพ (2026-11-24)

เซิร์ฟเวอร์สร้างภาพของ Gemini กลับมาใช้ได้ จึงทดสอบทางสำเร็จที่ค้างจากข้อ 5 โดยให้ `gyoloN` เป็นผู้สร้างภาพทุกข้อ ทดสอบบนสำเนาที่ `/workspace/skill-test` ก่อนติดตั้ง

สิ่งที่เปลี่ยน: `gyolo.py image --ref` (แก้ภาพจากภาพเดิม) · `ma_common.call_gemini_image(refs=...)` · agent-team: node ภาพที่ไม่ระบุผู้สร้างมี gyolo เป็นตัวสำรองของ Codex · ภาพ + ตรวจ: ผู้ตรวจมาจากคนละค่ายกับผู้สร้างของรอบนั้นก่อน และผู้สร้างที่เป็น gyolo ได้ภาพรอบก่อนเป็นภาพตั้งต้นในรอบที่ 2 ขึ้นไป · `check`: คำสั่ง CLI ที่เปิดไม่ขึ้นรายงานเป็น "ผิดพลาด" พร้อมข้อความ ไม่ใช่ "ไม่ได้ล็อกอิน" · `run --resume`: การจำลองโควตาหมดมีผลเฉพาะคำสั่งที่ใส่ `--simulate-limit` · สคริปต์หาโฟลเดอร์บัญชีจากตำแหน่งที่ตัวเองติดตั้ง จึงใช้ได้เมื่อ `gyoloN` เป็นผู้เรียกสกิล

| # | รายการ | ผล | หลักฐาน | เวลา |
|---|---|---|---|---|
| I1 | `gyolo.py image` (gyolo1) แอปเปิลแดงบนโต๊ะขาว | PASS | agy บันทึก PNG ที่ `--out` เอง · 1024×1024 · ภาพถ่ายสมจริงตรงคำอธิบาย | 76.8s |
| I2 | `gyolo.py image` (gyolo2) ป้ายไม้ตัวหนังสือไทย 2 บรรทัด แนวนอน 16:9 | PASS | 1376×768 · "ดอยหมอก" และ "เปิด 7:00–17:00" สะกดถูกทุกตัว | 74.9s |
| I3 | `gyolo.py image --ref` (gyolo1) เปลี่ยนแอปเปิลของ I1 เป็นสีเขียว และเพิ่มแก้วน้ำ | PASS | แอปเปิลรูปทรงและก้านเดิม ฉากเดิม สีเปลี่ยนเป็นเขียว มีแก้วน้ำด้านขวา | 72.4s |
| I4 | node ภาพ `"account": "gyolo"` | PASS | `cup` → gyolo1 `gemini-3.8-flash-medium` · PNG 1200×896 ตรวจ signature แล้ว | 42.6s |
| I5 | ภาพ + ตรวจ ที่ให้ Gemini สร้าง (ผู้ตรวจไม่ระบุ) | PASS | `sign#g1` gyolo1 50.5s → ผู้ตรวจ cyolo1 (คนละค่ายกับผู้สร้าง) PASS 11.4s → yolo2 ACCEPT 6.5s | 68.4s |
| I6 | ภาพที่ไม่ผ่านรอบแรก (gyolo1 สร้าง · gyolo2 ตรวจ · yolo ตัดสิน) | PASS | รอบ 1 FAIL: ผ้ากันเปื้อนสีน้ำตาล ไม่มีป้าย → รอบ 2 gyolo1 ได้ภาพรอบ 1 เป็นภาพตั้งต้น: คน ท่า และฉากเดิม ผ้ากันเปื้อนเป็นสีเขียว มีป้าย "ดอยหมอก" → PASS → yolo2 ACCEPT | 277.9s |
| I7 | แผนของ node ภาพที่ไม่ระบุผู้สร้าง (`--dry-run` ไม่เรียกโมเดลสร้างภาพ) | PASS | ผู้สร้างตามแผนเป็น cyolo ทั้ง 2 งาน · gyolo อยู่ใน pool เป็นตัวสำรอง · ไม่มีบัญชี Claude ถูกดึงเข้ามาเป็นผู้สร้าง | - |
| I8 | `check` เมื่อคำสั่ง CLI เปิดไม่ขึ้น (คำสั่งจำลองที่ตอบ `claude native binary not installed`) | PASS | สถานะ `error` รายละเอียด "คำสั่ง … ทำงานไม่ได้: …" (ก่อนแก้รายงานเป็น "ไม่ได้ล็อกอิน") | - |
| I9 | รันต่อหลังจำลองโควตาหมด: งานเจาะจง `gyolo1` + งานที่รอผล รอบแรกใส่ `--simulate-limit gyolo1` แล้ว `run --resume` โดยไม่ใส่ | PASS | รอบแรก: งานแรก failed (ไม่ย้าย) งานที่สอง blocked · รันต่อ: ทั้ง 2 งาน ok โดยไม่ต้องแก้ไฟล์สถานะ (ก่อนแก้ การจำลองติดไปกับการรันต่อ) | 9s |
| I10 | เรียกสกิลเมื่อ `HOME` เป็นโฟลเดอร์ของบัญชี `gyolo1` (แบบที่ `gyoloN` ตั้งให้ agent) | PASS | `team.py check` พบ 15 บัญชี พร้อมใช้ 7 (ก่อนแก้ ไม่พบบัญชีใดเลย เพราะหาใต้ `~/ai-accounts`) · `MA_BASE` ยังใช้กำหนดเองได้ | - |

ข้อสังเกต

- เวลาสร้างภาพของ Gemini อยู่ที่ 43–92 วินาทีในรอบแรก รอบแก้ไขที่ใช้ภาพตั้งต้นใช้ 72–148 วินาที
- ขนาดภาพขึ้นกับคำอธิบาย: ไม่ระบุได้ 1024×1024 หรือ 1200×896 ระบุแนวนอน 16:9 ได้ 1376×768
- ภาพของ I5 มีตัวหนังสือ "Doi Mok Coffee" บนตัวร้านเพิ่มมาเอง ผู้ตรวจให้ผ่านเพราะเกณฑ์ไม่ได้ห้ามตัวหนังสืออื่น ถ้าไม่ต้องการ ต้องเขียนไว้ในเกณฑ์
- ไม่ได้ทดสอบซ้ำในรอบนี้: ทางที่ Codex เป็นผู้สร้างภาพ (โค้ดส่วนนั้นส่งคำสั่งแบบเดิม) และทางที่เซิร์ฟเวอร์ภาพของ Gemini ตอบ 503 แล้วย้ายไป Codex (ทดสอบไว้ในข้อ 5: G3, G4, G6)
