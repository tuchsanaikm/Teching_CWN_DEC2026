# พรอมต์ของบท 03 · Agent Team End to End (หน้ารวม)

พรอมต์ของแต่ละหัวข้ออยู่ใน `PROMPTS.md` ของหัวข้อนั้น เรียงตามระยะ A → D (Requirement · Planning · Build/Train/Deploy บน `2× RTX 4090` หลัง NGINX `least_conn` · Verification ด้วย Playwright ครบทุก Test Case พร้อมไฟล์ `.gif` และ Bug Hunt)

**ก่อนเริ่ม:**
- container `multi-account` รันอยู่ มีสกิล `dag-planner` · `agent-team` · `yolo` · `cyolo` · `gyolo` · `vastai` และใช้บัญชีที่อนุญาต **`yolo2, yolo3, cyolo1, gyolo1`**
- คัดลอกไฟล์ `.env` (`VAST_API_KEY`, `HF_TOKEN`, `ROBOFLOW_API_KEY`) มาไว้ในโฟลเดอร์ของหัวข้อ
- เกณฑ์เช่าเครื่อง GPU: **`1 โหนด × 2× RTX 4090`** ความเร็วเน็ตขาลง **≥ 1,200 Mbps** และค่าดาวน์โหลด (`inet_down_cost`) ต่ำ
- เปิด Claude Code ที่โฟลเดอร์ของหัวข้อนั้น

> ⚠️ **เสียเงินจริง** — ทุกหัวข้อจบด้วยพรอมต์ **ลบเครื่อง** ห้ามข้าม แล้วดูหน้า [Instances](https://cloud.vast.ai/instances/) ว่าว่าง

| หัวข้อ | ระบบและสถาปัตยกรรม | พรอมต์ | สไลด์ | หลักฐาน Test Cases (`.gif`) |
|---|---|---|---|---|
| **1 · SiteSafe Inspect** | YOLO11s · `2× RTX 4090` · 8× FastAPI Micro-batching (`4/GPU`) + NGINX `least_conn` + Failover · Next.js 15 + Tailwind + PostgreSQL · Playwright 27/27 | [01_sitesafe_inspect/PROMPTS.md](01_sitesafe_inspect/PROMPTS.md) *(10 ขั้น)* | [SiteSafe_Inspect_Slides.html](01_sitesafe_inspect/SiteSafe_Inspect_Slides.html) *(61 หน้า)* | [01_sitesafe_inspect/test/index.html](01_sitesafe_inspect/test/index.html) *(27 `.gif`)* |
| **2 · ReceiptDesk** | Qwen3-VL-2B + LoRA · `2× RTX 4090` · 2× vLLM Data Parallelism (`1/GPU`, Continuous Batching) + SSE Streaming + NGINX `least_conn` + Failover · Next.js 16 + Tailwind v4 + PostgreSQL 16 · Playwright 28/28 | [02_receipt_desk/PROMPTS.md](02_receipt_desk/PROMPTS.md) *(15 ขั้น)* | [ReceiptDesk_Slides.html](02_receipt_desk/ReceiptDesk_Slides.html) *(71 หน้า)* | [02_receipt_desk/test/index.html](02_receipt_desk/test/index.html) *(28 `.gif`)* |
