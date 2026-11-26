# login-guide — ล็อกอินทีละบัญชีใน JupyterLab Terminal

ล็อกอินด้วยตัวเองเท่านั้น ข้อมูลล็อกอินเก็บใน volume `ai-accounts` (`/root/ai-accounts`) ไม่อยู่ใน image

## 0) เปิด container

```bash
docker run -d --name multi-account --privileged \
  -p 8888:8888 -v ai-accounts:/root/ai-accounts multi-account:1.0
```

เปิด <http://localhost:8888/lab> → **File ▸ New ▸ Terminal**
(หรือ `docker exec -it multi-account bash` ก็ใช้คำสั่งเดียวกันได้)

installer รันเองตอน start แล้ว ถ้าต้องการรันซ้ำ: `install-ai-accounts` (ไม่ทับของเดิม)

## 1) Claude Code — `yolo1` … `yolo5`

```bash
yolo1            # ครั้งแรกจะพาเข้าหน้าล็อกอิน (หรือพิมพ์ /login ในเซสชัน)
```

1. เลือกวิธีล็อกอิน → เปิด URL ที่ขึ้นในเบราว์เซอร์ของคุณ → ได้โค้ดมา → วางกลับใน terminal
2. ในเซสชันพิมพ์ `/mcp` ต้องเห็น `playwright` (MCP ส่วนกลาง)
3. ถาม `run shared-check` ต้องได้ `SHARED_SKILL_OK-claude-…`
4. `/exit` แล้วทำซ้ำกับ `yolo2` … `yolo5` (แต่ละบัญชีใช้คนละ account ได้)

ตรวจสถานะ: `yolo1 auth status`

## 2) Codex CLI — `cyolo1` … `cyolo5`

```bash
cyolo1 login --device-auth   # แสดง URL + โค้ด → เปิดในเบราว์เซอร์แล้วยืนยัน
cyolo1 login status
cyolo1 mcp list              # ต้องเห็น playwright
cyolo1                       # เปิดใช้งาน แล้วลอง: run shared-check → SHARED_SKILL_OK-codex-…
```

credential เป็นไฟล์ `auth.json` ใน `/root/ai-accounts/.Codex/cyoloN/` (แยกต่อบัญชี) ทำซ้ำกับ `cyolo2` … `cyolo5`

## 3) Antigravity CLI — `gyolo1` … `gyolo5`

```bash
gyolo1 models    # ยังไม่ล็อกอิน = "Please sign in"
gyolo1           # เปิดแบบไม่มีอาร์กิวเมนต์ → ทำตามขั้นตอน sign in (เปิด URL ในเบราว์เซอร์)
gyolo1 models    # ล็อกอินแล้วจะแสดงรายชื่อโมเดล
gyolo1 mcp list  # ต้องเห็น playwright
```

token เป็นไฟล์ใต้ `/root/ai-accounts/.Gemini/gyoloN/` (container ไม่มี keyring) ทำซ้ำกับ `gyolo2` … `gyolo5`

## ข้อควรระวัง

- เปิดหลายบัญชีพร้อมกันได้ (คนละ terminal) เพราะ config root แยกกัน
- อย่าคัดลอก/ symlink ไฟล์ล็อกอินระหว่างบัญชี และอย่าใส่ credential ไว้ใน `shared/`
- ลบ container ได้ ข้อมูลล็อกอินยังอยู่ใน volume `ai-accounts` — อย่าลบ volume นี้
