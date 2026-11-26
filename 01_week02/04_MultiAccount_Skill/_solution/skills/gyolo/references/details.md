# gyolo — รายละเอียด (Antigravity CLI `agy` 1.5.15)

## โครงสร้างบัญชี

- บัญชี: `/root/ai-accounts/.Gemini/gyoloN` = `HOME` ของ process agy (wrapper ตั้งให้เฉพาะ process นี้) · ไบนารีเดียว `/opt/antigravity/bin/agy` ปิด auto-update (`AGY_CLI_DISABLE_AUTO_UPDATE=true`)
- wrapper ใส่ `--dangerously-skip-permissions` · สกิลอ่านจาก `~/.gemini/config/skills/<สกิล>` (symlink รายสกิลไป `/root/ai-accounts/.Gemini/shared/skills/<สกิล>` สร้างใหม่ทุกครั้งที่เปิด wrapper) · MCP จาก `~/.gemini/config/mcp_config.json`
- ห้ามอ่านไฟล์ token/credential ในโฟลเดอร์บัญชี · ตรวจล็อกอินด้วย `gyoloN models` เท่านั้น

## สคริปต์เรียกอย่างไร

`gyolo.py run` → `gyoloN -p <prompt> --model <id> --output-format json --print-timeout <timeout>s [--add-dir D] [--json-schema S]` โดยปิด stdin และ cwd = `--cwd` (ค่าเริ่มต้น `/tmp`)

ผล (บรรทัด JSON สุดท้ายของ stdout):

| ฟิลด์ | ความหมาย |
|---|---|
| `status` | `SUCCESS` หรือ `ERROR` |
| `response` | คำตอบ (ข้อความ) |
| `error`, `finished_reason` | เมื่อล้ม (`print_timeout`, `error`) |
| `conversation_id` | id ของรอบ (→ `session_id`) |
| `duration_seconds`, `num_turns` | เวลา/จำนวน turn |
| `usage.input_tokens` | input **ไม่รวม** cache read (เหมือน Claude) |
| `usage.cache_read_tokens` | → ledger `cached_input_tokens` |
| `usage.output_tokens` | output **รวม** thinking แล้ว |
| `usage.thinking_tokens` | → ledger `reasoning_tokens` |

ledger: `cli: gemini` · `cache_write_tokens` = 0 · `cost_usd` = null (agy ไม่รายงานราคา) · `model` = id เต็ม · `effort` = ส่วนท้ายของ id

## ข้อผิดพลาด (วัดจริง)

| กรณี | อาการจาก agy | สคริปต์รายงาน |
|---|---|---|
| ไม่ได้ล็อกอิน (`-p`) | stderr: `Authentication required. Please visit the URL…` แล้ว **รอ 60 วินาที** → JSON `status: ERROR`, `error: authentication failed or timed out`, exit 1 | หยุด process ทันทีที่เห็นข้อความ (≈1 วินาที) ไม่เก็บลิงก์ → `not_logged_in` |
| ไม่ได้ล็อกอิน (`models`) | `Error: Please sign in to view available models…` exit 1 (≈4 วินาที) | `check` → ไม่ได้ล็อกอิน |
| timeout | stderr `[agy] print timeout…` + `AGY_ERROR: {"status":"DEADLINE_EXCEEDED","reason":"print_timeout"}` · JSON `finished_reason: print_timeout` · exit 3 | `timeout` |
| รุ่นไม่มี | `error: invalid model selection (--model "x" …)` + รายชื่อรุ่น · exit 1 | `error` (สคริปต์เลือกรุ่นจากรายชื่อจริงก่อนส่ง จึงไม่ค่อยเกิด) |
| โควตาหมด | (ไม่ได้เกิดจริงตอนทดสอบ) ไบนารีมี `RESOURCE_EXHAUSTED` / `QUOTA_EXHAUSTED` / `You have exhausted your quota on this model.` · changelog: weekly quota error หยุด turn ทันที · บรรทัด `AGY_ERROR` บอก status | `limit` (ทดสอบตัวจำแนกด้วยผลจำลอง) |
| ล็อกอินแล้วแต่ใช้ไม่ได้ | `AGY_ERROR` status `UNAUTHENTICATED` หรือ error อื่นหลัง `models` ผ่าน | `check` → ล็อกอินแล้วแต่ใช้ไม่ได้ (`unusable`) |

## โควตา

`gyoloN -p "/usage" --output-format json` (≈4 วินาที ไม่ใช้ tokens) → `command.data.groups[]` แต่ละกลุ่มมี `buckets[]`: `window` (`5h`/`weekly`), `remaining_fraction`, `reset_time` (UTC) · `response` มีบรรทัด TAB `กลุ่ม<TAB>Weekly Limit Remaining<TAB>98%<TAB>เวลา` (ใช้เป็นทางสำรอง)
- กลุ่ม `Gemini Models` (Gemini 4 ทุกตระกูล + 3.8 Flash + Orchestrator) และ `Claude and GPT models` (Claude Opus/Sonnet 5.5, GPT-OSS ที่เรียกผ่าน agy) แยกโควตากัน
- สคริปต์แปลง **% ที่เหลือ → % ที่ใช้**: `session_pct` = 5 ชม., `week_pct` = สัปดาห์ ของกลุ่ม Gemini · กลุ่มอื่นอยู่ที่ `week_other` และ `groups` · เวลาของข้อมูล = ตอนเรียก (ข้อมูลสด)
- ข้อความของ agy: โควตาถูกใช้ตามราคาของ tokens (รุ่นถูก/งานสั้นใช้โควตาน้อยกว่า)

## รุ่นและการจัดอันดับ (วัด 2026-11-23 บน gyolo1/gyolo2)

`gyoloN models` → บรรทัด `id<TAB>ชื่อ` หลังบรรทัด `Fetching available models...` · effort อยู่ในชื่อ: `gemini-4-{neon,hydrogen}-{low,medium,high,xhigh}` · `gemini-4-{carbon,argon}-{low,medium,high}` · `gemini-3.8-flash-{low,medium,high}` · `gemini-pro-orchestrator[-neon|-argon]` · `claude-opus-5-5-*` `claude-sonnet-5-5-*` `gpt-oss-120b-medium`

| ชุดทดสอบ (ห้ามใช้เครื่องมือ) | flash | neon | carbon | argon | hydrogen |
|---|---|---|---|---|---|
| ง่าย 1 ข้อ · low | ถูก 6.8 s | ถูก 5.0 s | ถูก 9.3 s | ถูก 6.2 s | ถูก **3.0 s** |
| กลาง 4 ข้อ · low | 4/4 · 41 s · 5.8k thinking | 4/4 · 31 s · 3.9k | **2/4 · 0 thinking** | **1/4 · 0 thinking** | 4/4 · **10 s** · 2.4k |
| ยาก 4 ข้อ · high | — | 4/4 · 147 s · 18.7k | 4/4 · 413 s · 36.6k | 4/4 · 178 s · 15.4k | 4/4 · **67 s** · 14.8k |
| ยาก 5 ข้อ · medium | 5/5 · 130 s · 16.6k | 5/5 · 83 s · 11.2k | 5/5 · 170 s · 14.0k | 5/5 · **45 s · 3.1k** | 5/5 · 48 s · 9.4k |

ข้อสรุป: ความถูกต้องแยกตระกูล Gemini 4 ไม่ออก (ระดับ medium/high ถูกครบทุกตัว) จึงจัดอันดับจาก (1) พฤติกรรมที่ low: Carbon/Argon ไม่คิดเลยและตอบผิด ใช้เฉพาะ medium ขึ้นไป (2) ความเร็ว/tokens: Hydrogen เร็วที่สุดเกือบทุกชุด (3) changelog ของ agy: Orchestrator ใช้ **Carbon (High) วางแผน** และ **Hydrogen (High) ลงมือทำ** · ตัวตรวจคำสั่งของ Auto mode ใช้ Hydrogen · Neon/Carbon/Argon มี Orchestrator ของตัวเอง (ตระกูลระดับวางแผน)
→ เบา = Gemini 3.8 Flash · มาตรฐาน (ตัวทำงาน) = Gemini 4 Hydrogen · แรงสุด (ตัววางแผน) = Gemini 4 Carbon · Argon = ระดับวางแผนที่ประหยัด tokens ที่สุดในชุดยาก

| d | รุ่น |
|---|---|
| 1 | gemini-3.8-flash-low |
| 2 | gemini-3.8-flash-medium |
| 3 | gemini-4-hydrogen-medium |
| 4 | gemini-4-hydrogen-high |
| 5 | gemini-4-argon-high |
| 6 | gemini-4-carbon-high |

## พฤติกรรมอื่นที่วัดแล้ว

- cwd: agent ทำงานในโฟลเดอร์ที่ process เริ่ม (`pwd` ตอบ path ของ `--cwd`) · อ่านไฟล์นอก cwd ได้
- พร้อมกัน: บัญชีเดียวรัน `-p` 3 ตัวพร้อมกันได้ (8 วินาทีรวม ทุกตัวถูก) · gyolo1 + gyolo2 ขนานกันได้
- ดูภาพ: ใส่ absolute path ใน prompt แล้ว agy เปิดไฟล์เอง (`gemini-3.8-flash-low` อ่านข้อความบนป้ายในภาพถูก ~15 วินาที)
- สร้างภาพ: ดูหัวข้อถัดไป

## สร้างภาพ (`gyolo.py image`, node `image` ฝั่ง gyolo)

- ความสามารถมีจริง: agy เรียก subagent `image-generator` (เครื่องมือ `generate_image`, รุ่น `gemini-3.1-flash-image`) · ถ้าถามโดยไม่บอกให้ใช้เครื่องมือ บางครั้งตอบ CANNOT
- 2026-11-24 สร้างสำเร็จทุกครั้งที่ลอง (gyolo1 และ gyolo2): agy บันทึก PNG ที่ path ที่สั่งเอง · 43–77 วินาทีต่อภาพ · 1024×1024 เป็นค่าเริ่มต้น ขอ "แนวนอน 16:9" ได้ 1376×768 · ตัวหนังสือไทย 2 บรรทัดบนป้ายสะกดถูก · คำตอบมีบรรทัดแจ้งว่ารอ subagent ตามด้วย path ของไฟล์
- แก้ภาพเดิม (`--ref`): ใส่ absolute path ของภาพตั้งต้นใน prompt แล้ว agy ส่งให้เครื่องมือภาพเป็นภาพอ้างอิง · ทดสอบ: แอปเปิลแดง → สั่งเปลี่ยนเป็นสีเขียวและเพิ่มแก้วน้ำ ได้แอปเปิลรูปทรงและก้านเดิม ฉากเดิม (72 วินาที)
- 2026-11-23 ลอง 6 ครั้ง (hydrogen-high, hydrogen-medium, flash-medium, gyolo1/gyolo2 และบนเครื่อง host) ได้ `image failed to generate: transport error (Unavailable, HTTP 503): No capacity available for model gemini-3.1-flash-image on the server` ทุกครั้ง โดย agy ยังตอบ `status: SUCCESS` (ข้อผิดพลาดอยู่ในข้อความคำตอบ ไม่ใช่ exit code) สคริปต์จึงตัดสินจากไฟล์ PNG ไม่ใช่จากสถานะ
- สคริปต์: prompt + กติกา (ใช้เครื่องมือภาพเท่านั้น ห้ามวาดด้วยโค้ด บันทึกที่ path ล้มให้ตอบ `IMAGE_FAILED: <ข้อความ>`) · รุ่นที่ควบคุม subagent = difficulty 2 (`gemini-3.8-flash-medium`) · สำเร็จเมื่อมี PNG (signature) ที่ path และเขียนหลังเริ่มเรียก · ไม่เช่นนั้นหาไฟล์ .png ใหม่จาก path ที่ระบุในคำตอบหรือในโฟลเดอร์บัญชี (ดูแค่ชื่อไฟล์ .png) แล้วคัดลอก · คำตอบมี `IMAGE_FAILED` / `No capacity` / `HTTP 503` / `UNAVAILABLE` / `image failed to generate` → `image_unavailable` · ไม่มีไฟล์แต่ไม่มีข้อความผิดพลาด → `bad_output`
- ตรวจไม่ได้ 100% จากคำตอบว่า agy ไม่ได้วาดด้วยโค้ด: กติกาใน prompt ห้ามไว้ และภาพที่ได้จากการทดสอบเป็นภาพถ่ายสมจริง
- ledger: 1 แถวต่อการเรียก `status` เป็น `ok` / `image_unavailable` / `bad_output` / สถานะปกติอื่น
- `--effort` ของ agy มีแต่สกิลใช้ effort ในชื่อรุ่นแทน (ตรงกับ `models`)
