# agent-team — รายละเอียด

## ไฟล์ใน run directory (`/workspace/.agent-team/<run_id>/`)

| ไฟล์ | ใช้ทำอะไร |
|---|---|
| `graph.json` | งานทั้งหมดและความสัมพันธ์ (`lead` ต่อท้ายงานที่หัวหน้า dispatch) |
| `board.md` | กระดานความรู้กลาง ต่อท้ายเท่านั้น `- [เวลา · ผู้เขียน] ข้อความ` |
| `msgs/<จาก>__<ถึง>.md` | ข้อความส่งต่องาน (ระบบเขียนให้ทุกเส้น depends_on และทุกการย้ายงาน) · `msgs/<node>__progress.md` = ความคืบหน้าของงานยาว (ผู้รับงานต่ออ่านก่อน) |
| `out/<node>.md` | ผลของงาน (เก็บไว้แม้ผิดรูปแบบ) · review: `out/<id>.rN.work.md` `out/<id>.rN.review.md` · debate/best_of: `out/<id>.A.md` ... `out/<id>.judge.md` · ภาพ+ตรวจ: `out/<id>.rN.png` `out/<id>.rN.check.md` `out/<id>.judge.md` |
| `ledger.jsonl` | สถิติทุกครั้งที่เรียก + เหตุการณ์ (`event`: `worker_switch` `worker_stop` `lead_switch`) |
| `state.json` | สถานะงานแต่ละชิ้น (`status planned account value error`), บัญชี (`check stopped stop_reason unusable quota role`), หัวหน้าปัจจุบัน, `lead_history`, `switches`, `events` |
| `handoff.md` | checkpoint ของหัวหน้าแต่ละคน + สถานะอัตโนมัติที่ผู้ควบคุมเขียนทุกครั้งที่สลับหัวหน้า |
| `approve/<node>` | ไฟล์อนุมัติของ human gate (`team.py approve`) |
| `final/` | ที่วางผลรวม · `logs/` = log ของลูกทีมที่หัวหน้า dispatch |

สถานะงาน: `pending` → `waiting_approval` → `running` → `ok` | `failed` | `bad_output` | `blocked`

## ledger กลาง `/workspace/.agent-team/ledger.jsonl`

ทุกการเรียกผ่านสคริปต์ของสกิล (yolo.py / cyolo.py / gyolo.py / team.py) เพิ่ม 1 แถว (และในแถว ledger ของ run ถ้ามี):
`ts_start ts_end run_id node account cli model effort duration_s input_tokens cached_input_tokens cache_write_tokens output_tokens reasoning_tokens cost_usd status error prompt_chars result_chars real_model` · ไม่เก็บข้อความ prompt หรือ secret
- `node` ของงานย่อย: `<id>#w1` `<id>#r1` (review) · `<id>#A` `<id>#judge` (debate/best_of) · `<id>#g1` `<id>#c1` `<id>#judge` (ภาพ+ตรวจ: สร้าง/ตรวจ/ตัดสิน) · `lead#<episode>` (หัวหน้า) · `check` (ตรวจความพร้อม)
- `cli`: `claude` · `codex` · `gemini` (gyoloN: thinking → `reasoning_tokens`, cache read → `cached_input_tokens`, `cost_usd` ว่าง)
- tokens ที่นับกับงบ = input (ไม่รวม cache read) + cache_write + output · Codex: input − cached_input (input ของ Codex รวม cache read แล้ว) · Gemini: input ไม่รวม cache read อยู่แล้ว (เหมือน Claude)

## ความยาก → รุ่น (3 CLI)

| d | Claude | Codex | Antigravity |
|---|---|---|---|
| 1 | haiku/low | gpt-6.2-sol/low | gemini-3.8-flash-low |
| 2 | sonnet/medium | gpt-6.2-sol/medium | gemini-3.8-flash-medium |
| 3 | opus/high | gpt-6.2-sol/high | gemini-4-hydrogen-medium |
| 4 | opus/xhigh | gpt-6.2-astra/xhigh | gemini-4-hydrogen-high |
| 5 | opus/max | gpt-6.2-astra/max | gemini-4-argon-high |
| 6 | fable/high | gpt-6.2-astra/ultra (ลดเป็นระดับสูงสุดที่รุ่นรองรับ) | gemini-4-carbon-high |

- Codex อ่านจาก `models_cache.json` เสมอ: ไม่มี slug ที่ต้องการ → รุ่นค่าเริ่มต้นของ cache · งาน `kind: vision` บน Codex ใช้ `gpt-6.1-terra` ถ้ามี · สร้างภาพใช้รุ่นค่าเริ่มต้น effort low (เหมือนเดิม)
- Antigravity อ่านจาก `gyoloN models` (cache 1 วันที่ `.cache/gemini_models.json`): ไม่มี id → ตระกูลเดียวกัน effort ใกล้สุด → ตระกูลสำรอง
- fable: ราคาตามรายการราว 2 เท่าของ opus และมีบรรทัดโควตา `Current week (Fable)` แยก (`week_other.Fable`)
- `model`/`effort` ของ node ใช้เฉพาะ CLI ที่รู้จักชื่อนั้น (`opus` → Claude, `gemini-*` → Antigravity, อื่น ๆ → Codex) ฝั่งอื่นใช้ตามความยาก

## การเลือกบัญชี

1. `account` เจาะจง → ใช้บัญชีนั้นเท่านั้น ถ้าไม่พร้อม/หยุดรับงาน/ล้ม → งานล้มพร้อมเหตุผล ไม่ย้ายเงียบ
2. ฝั่ง (`yolo`/`cyolo`/`gyolo`) หรือ `any` → คะแนน = % โควตาที่ใช้ (ไม่รู้ = 50) + 15 × งานที่วางแผน/รันอยู่ + tokens ใน run/20000 เลือกต่ำสุด · `any` ใช้ router ตาม `kind` ก่อน
3. router ของ `any`: `image` (สร้างภาพ) → cyolo ก่อน ใช้ gyolo เมื่อไม่มีบัญชี Codex ที่ใช้ได้เหลืออยู่ · `vision`/`image_check`/`look` (ดู/ตรวจภาพ) → gyolo → cyolo → yolo · `code`/`review` → cyolo ก่อน · `doc`/`long` → yolo ก่อน · อื่น ๆ → คะแนนต่ำสุด (โควตาเหลือมากสุด) จาก 3 ฝั่ง
4. ล้มเพราะโควตา/ล็อกอิน (`limit` `auth_expired` `not_logged_in`) → ย้ายไปบัญชีฝั่งเดียวกันก่อน แล้วค่อยฝั่งอื่นตาม router (เฉพาะ `any`) · งานที่ระบุฝั่งย้ายได้แค่ในฝั่ง · งานเจาะจงบัญชีหยุดและรายงาน
5. รายชื่อบัญชีที่ใช้ได้ = `--workers` ถ้ามี · ถ้าทุก node ระบุบัญชีเจาะจง = เฉพาะบัญชีในกราฟ · ไม่เช่นนั้น = ทุกบัญชีของฝั่งที่กราฟใช้ (`any` = 3 ฝั่ง) · กราฟที่ใช้แค่ yolo/cyolo ไม่ตรวจและไม่เรียก gyolo เลย
6. แผน (`planned`) ทำตอนรับงาน · บัญชีหยุดรับงาน → งานในคิวที่วางแผนไว้ย้ายทันที (`worker_switch`) · งานที่กำลังรันปล่อยให้จบ

## ภาพ + ตรวจข้าม CLI (`type: image` + `criteria` หรือ `check: true`)

ฟิลด์: `account` (ผู้สร้าง ค่าเริ่มต้น any → cyolo) · `criteria` · `checker` (ค่าเริ่มต้น `any` = ค่ายอื่นที่ไม่ใช่ค่ายของผู้สร้าง ตาม router ดูภาพ) · `judge` (ค่าเริ่มต้น `yolo`) · `max_rounds` (3) · `check_difficulty` (1) · `judge_difficulty` (2) · `path`

1. รอบ N: ผู้สร้างสร้าง `out/<id>.rN.png` (ตรวจ PNG signature) · ledger `<id>#gN`
2. ผู้ตรวจเปิดไฟล์ภาพตาม path ตอบบรรทัดแรก `PASS`/`FAIL` + คำแนะนำ → `out/<id>.rN.check.md` · ledger `<id>#cN`
3. FAIL → ข้อความคำแนะนำของผู้ตรวจถูกต่อท้ายคำอธิบายเดิมเป็นคำสั่งของรอบ N+1 (ผู้สร้างที่เป็น gyolo ได้ภาพรอบ N เป็นภาพตั้งต้นด้วย) · PASS หรือครบ `max_rounds` → ข้อ 4
4. ผู้ตัดสินดูภาพสุดท้าย + ประวัติการตรวจ ตอบ JSON `{"decision":"ACCEPT|REJECT","reason","corrected_prompt"}` → `out/<id>.judge.md` · ledger `<id>#judge`
5. ACCEPT → คัดลอกภาพสุดท้ายไป `path` · node `ok` · `{{id}}` = path · REJECT → `bad_output` พร้อมเหตุผล (prompt ที่แก้แล้วอยู่ใน `state.json` → `judge.corrected_prompt` ใช้กับ `run --resume --set <id>.prompt=...`)

node `image` ที่ไม่มี `criteria`/`check` ทำงานเหมือนเดิมทุกอย่าง

## ผู้สร้างภาพ (Codex / Gemini)

- `account` ไม่ระบุหรือ `any` → Codex ก่อน · pool ของ node ภาพมีฝั่ง cyolo และ gyolo (ไม่ดึง Claude) · ใช้ gyolo เมื่อไม่มี Codex ที่ใช้ได้เหลืออยู่
- `"account": "gyolo"` → Gemini สร้างผ่าน subagent `image-generator` ของ agy (pool เพิ่มฝั่ง cyolo ไว้สำรอง) · ทดสอบ 2026-11-24: สำเร็จ 43–51 วินาทีต่อภาพ · ล้มด้วย `image_unavailable` (HTTP 503 no capacity) → ย้ายไป Codex ทันที บันทึก `worker_switch` พร้อมข้อความจากเซิร์ฟเวอร์ · บัญชี gyolo ยังรับงานอื่นต่อได้ (ไม่ถูกทำเครื่องหมายว่าใช้ไม่ได้)
- `"account": "gyolo1"` (เจาะจง) → ล้มพร้อมเหตุผล ไม่ย้าย
- ภาพ + ตรวจ: ผู้ตรวจมาจากคนละค่ายกับผู้สร้างของรอบนั้นก่อน (cyolo สร้าง → gyolo → yolo · gyolo สร้าง → cyolo → yolo) ไม่มีค่ายอื่นใน pool จึงใช้บัญชีอื่นของค่ายเดียวกัน · `checker` ที่ระบุเองใช้ตามที่ระบุ
- รอบที่ 2 ขึ้นไป: ผู้สร้างที่เป็น gyolo ได้ภาพของรอบก่อนเป็นภาพตั้งต้น (แก้เฉพาะจุดที่ผู้ตรวจสั่ง คน ท่า และฉากคงเดิม) · ผู้สร้างที่เป็น Codex ได้คำแนะนำเป็นข้อความอย่างเดียวเหมือนเดิม
- 2026-11-23 เซิร์ฟเวอร์ภาพของ Gemini ตอบ HTTP 503 no capacity ทุกครั้ง · 2026-11-24 กลับมาใช้ได้ และทดสอบทางสำเร็จครบแล้ว (ดู `gyolo/references/details.md`)

## ส่งข้อมูลข้าม CLI

ทุก CLI ได้ absolute path ในโจทย์: `{{file:id}}` → `out/<id>.md`, `board.md`, `msgs/` · gyolo อ่านไฟล์นอก cwd ได้ และสคริปต์เพิ่ม run folder ให้ด้วย `--add-dir` · ทดสอบแล้วทั้ง Claude → Gemini, Gemini → Codex, Gemini → Claude (board)

## โควตา

- Claude: `/usage` ตอนเริ่ม + `rate_limit_event` จากทุกการเรียก (five_hour = session, seven_day = week)
- Codex: `rate_limits` จาก rollout ล่าสุด (เวลาของข้อมูลอาจเก่า)
- Antigravity: `gyoloN -p /usage` (ไม่เรียกโมเดล) รายงาน % ที่เหลือ → แปลงเป็น % ที่ใช้ (5 ชม. = session, สัปดาห์ = week ของกลุ่ม Gemini · กลุ่ม Claude/GPT ใน agy อยู่ที่ `week_other`)
- สถานะใน `status`: พร้อม / ใกล้หมด (≥ เกณฑ์−20%) / หยุดรับงาน / ใช้ไม่ได้

## หัวหน้าทีม (lead)

ผู้ควบคุม (`team.py lead`) วนรอบ:
1. เลือกหัวหน้า: `--leader` หรือบัญชี Claude ที่พร้อมตัวแรก · ผู้สืบทอด: `--succession` ตามลำดับ หรืออัตโนมัติ (พร้อม → ฝั่งเดียวกันก่อน → โควตาเหลือมาก → ข้ามฝั่ง) · ผู้สืบทอดอัตโนมัติมาจาก Claude และ Codex เท่านั้น
   - gyolo เป็นหัวหน้าได้เมื่อระบุเอง (`--leader gyolo1` / `--succession gyolo1,...`): ทดสอบแล้ว gyolo1 (gemini-3.8-flash-medium) ใช้ `status/dispatch/wait/checkpoint/finish` ได้ครบ และสั่งงานใหม่เองเมื่องานล้ม แต่ช้ากว่า (≈260 วินาทีกับงาน 3 ข้อ) · agy ไม่ส่ง tokens ระหว่างรอบ งบหัวหน้าจึงตรวจได้หลังจบรอบเท่านั้น (เหมือนหัวหน้า Codex) · ยังไม่ได้ทดสอบการสลับหัวหน้าเข้า/ออกจาก gyolo
   - สลับเชิงรุกกลางรอบ (STOP หลัง dispatch) เกิดได้เฉพาะหัวหน้า Claude (มี stream tokens) · `--demo` ครบ 3 เหตุการณ์ต้องมีบัญชี Claude ที่พร้อมอย่างน้อย 2 บัญชี
2. รันหัวหน้าหนึ่ง episode ด้วย env `MA_TEAM_RUN`, `MA_TEAM_ROLE=leader` · นับ tokens สดจาก stream-json
3. คำสั่งของหัวหน้า (รู้ run จาก env):
   - `team.py dispatch --id X --difficulty N [--account any] [--depends a,b] [--expect number] [--type image --path /abs.png] --prompt "..."`
   - `team.py wait --ids a,b` (สูงสุด 300 วินาที/ครั้ง) · `team.py status`
   - `team.py checkpoint --done "..." --next "..." [--running "..."] [--decision "..."]`
   - `team.py finish --output /abs/final.md --summary "..."`
4. หลังทุก `dispatch` / `checkpoint` / `wait` ตรวจงบหัวหน้า (`--lead-token-budget`) ถ้าเกิน คำสั่งพิมพ์ `STOP` → หัวหน้า checkpoint แล้วผู้ควบคุมจบรอบ → สลับเชิงรุก
5. หัวหน้าล้ม (โควตา/ล็อกอิน/timeout/heartbeat > `--heartbeat-timeout`) หรือ `--simulate-crash` → ผู้ควบคุมเขียนสถานะอัตโนมัติลง `handoff.md` แล้วเริ่มหัวหน้าคนใหม่ → สลับเชิงรับ
6. ทุกการสลับบันทึกใน `state.json.lead_history`, `board.md`, ledger (`event: lead_switch`)

`--demo`: หัวหน้าคนที่ 1 ล้มหลัง dispatch ครั้งแรก · หัวหน้าคนที่ 2 มีงบ 1 token (STOP หลัง dispatch แรก) · การเรียกลูกทีมครั้งแรกจำลองโควตาหมด (ย้ายงาน) · ลูกทีมที่ทำงานแรกสำเร็จถูกตั้งงบ 1 (หยุดรับงาน) · ลูกทีมพร้อมกัน 1 งานต่อบัญชี · ไม่ใส่ `--goal` = งานตัวอย่างคำนวณ 4 ข้อแล้วรวมเป็นตาราง

## รายงาน run (`team.py report`)

อ่านอย่างเดียว ไม่เรียกโมเดล · run ที่ใช้ = `--run <id>` → env `MA_TEAM_RUN` → run ล่าสุด (เหมือน `status`) · เขียนทับไฟล์เดิมทุกครั้ง

| ส่วน | ที่มา |
|---|---|
| หัวรายงาน | `state.json`: run_id, mode, เวลาสร้าง, เวลางานจบล่าสุด, จำนวนงานตามสถานะ |
| เป้าหมาย | `goal` ของกราฟ (lead = `--goal`) |
| ตารางงาน | 1 แถวต่องาน: งาน · บัญชี (ทุกบัญชีที่ถูกเรียก รวมที่ย้ายงาน) · รุ่น/effort (`real_model` ถ้ามี) · สถานะ (+ข้อผิดพลาด) · เวลา s (`duration_s` ของการรันครั้งล่าสุด) · โทเค็น (`row_tokens` = เกณฑ์งบ รวมทุกครั้งที่เรียก รวมรอบที่ล้มก่อน resume) จาก `ledger.jsonl` ของ run · การเรียกที่ไม่ใช่งาน (หัวหน้า `lead#N`, `check`) เป็นแถว `(หัวหน้าทีม)` `(ตรวจความพร้อม)` · แถวรวมท้ายตาราง (เวลารวม = ผลบวก ไม่ใช่ wall time ของงานขนาน) |
| ผลของงานสุดท้าย | งานที่ไม่มีงานอื่นรอ (sink) ซึ่งจบล่าสุด · เนื้อหา `out/<id>.md` ใน code fence (ตัดที่ 6000 ตัวอักษร + path ฉบับเต็ม) · งานภาพแสดง path + `![]()` |
| ผลรวมจากหัวหน้าทีม | เฉพาะ lead ที่ `finish` แล้ว: ไฟล์ + สรุป |

## ตัวจำลองสำหรับทดสอบ (ไม่เผาโควตาจริง)

- `MA_SIMULATE_LIMIT=yolo1,cyolo2` (env) หรือ `--simulate-limit` → การเรียกบัญชีนั้นล้มทันทีเหมือนโควตาหมด (tokens 0) · การจำลองมีผลเฉพาะคำสั่งที่ใส่ไว้: `run --resume <id>` ที่ไม่ใส่ `--simulate-limit` จะรันจริง
- `--worker-token-budget yolo1=1` → yolo1 หยุดรับงานหลังงานแรก
- `--lead-token-budget 1` → หัวหน้าทุกคนเกินงบหลังคำสั่งแรก

## ข้อควรระวัง

- ห้าม `eval` หรือรันผลลัพธ์ของ agent เป็นคำสั่ง shell · ส่งข้อมูลยาวด้วย `{{file:id}}`
- `{{id}}` ที่ยาวเกิน 2000 ตัวอักษรถูกแทนด้วยข้อความให้อ่านไฟล์แทน
- human gate รอสูงสุด `--gate-timeout` (ค่าเริ่มต้น 1800 วินาที) แล้วหยุด รันต่อด้วย `--resume`
