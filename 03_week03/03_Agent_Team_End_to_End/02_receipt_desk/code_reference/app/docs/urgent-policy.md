# นโยบายการจัดคิวงานด่วน เพดานกันระบบล้น (HTTP 429) และการพักใบที่อ่านไม่ได้ · ReceiptDesk (NGINX + 2× vLLM Architecture)

เอกสารนี้สรุปผลการตัดสินใจออกแบบระบบจัดคิวฝั่งแอปพลิเคชัน (**PostgreSQL จัดลำดับงานเร่งด่วน + Async Dispatcher**) ที่ทำงานร่วมกับคลัสเตอร์ **NGINX + 2× vLLM (`2× RTX 4090` · 2× vLLM Replicas หลัง NGINX `least_conn`)** โดยไม่ต้องใช้ บริการตัวกลางภายนอก

## 1. การจัดลำดับคิวและการแซงคิวงานด่วน (BR-08 · BR-09 · BR-10)

| หัวข้อ | การออกแบบในระบบจริง | ตอบ Requirement |
|---|---|---|
| แหล่งเก็บคิว (Source of Truth) | ตาราง `batches` และ `receipts` ใน **PostgreSQL 16** (คอลัมน์ `priority`, `urgent_set_at`, `status`, `attempts`, `dispatch_state`) | NFR-05 (งานไม่หายแม้รีสตาร์ทเครื่อง GPU) |
| สิทธิ์ตั้งงานด่วน | เฉพาะบทบาท **หัวหน้าทีม (`lead`)** เท่านั้น | FR-18 · NFR-03 |
| ขนาดชุดงานด่วน | ไม่เกิน **10 ใบต่อชุด** (`BR-08`) | BR-08 |
| โควตางานด่วนรายวัน | ไม่เกิน **5 งานต่อวันปฏิทินไทย (`Asia/Bangkok`)** (`BR-09`) | BR-09 |
| การหยิบงานแบบไม่ให้คิวปกติอด (4:1) | Async Dispatcher ดึงงานจาก PostgreSQL ด้วย `FOR UPDATE SKIP LOCKED` เรียงตาม `priority DESC, urgent_set_at ASC, accepted_at ASC` และจำกัดการหยิบใบด่วนติดกันไม่เกิน **4 ใบ** ก่อนสลับหยิบใบปกติ **1 ใบ** (`BR-10`) เมื่อมีใบปกติรออยู่ | BR-10 · NFR-02 · NFR-03 |
| การกระจายโหลดไป GPU | ส่งคำขอ HTTP/JSON (Vision OCR) พร้อมกันหลายใบไปยัง **NGINX `least_conn` (:8080)** ซึ่งกระจายไปยัง **vLLM GPU 0 (:8001)** และ **vLLM GPU 1 (:8002)** ที่มี **Continuous Batching (`--max-num-seqs 256`)** | NFR-02 · NFR-03 · NFR-10 |

## 2. เพดานกันระบบล้น (HTTP 429) เมื่อคิวงานปกติเต็ม (BR-11 · BR-12)

1. นับจำนวนใบงานปกติที่อยู่ในสถานะ `queued` หรือ `processing` จากตาราง `receipts` ใน PostgreSQL
2. หาก `pending_normal + new_batch_size > 400` เว็บจะปฏิเสธทั้งชุดทันทีด้วย HTTP `429 Too Many Requests` (`error: "queue_full"`)
3. คำนวณนาทีที่ให้ลองใหม่จากจำนวนใบที่ค้างอยู่และจำนวน GPU Replicas ที่พร้อมทำงาน (`system_state.workers_alive`) และส่งกลับทั้ง header `Retry-After` และฟิลด์ `retryAfterMinutes`
4. **งานด่วนไม่ถูกบล็อกด้วยเพดาน 400 ใบของงานปกติ** เพื่อรับประกันว่างานด่วนของหัวหน้าทีมเข้าถึง vLLM ได้ทันทีภายใน SLO 5 นาที

## 3. การจัดการใบที่อ่านไม่สำเร็จ (BR-07 · Retry Limit 3 ครั้ง)

1. ทุกครั้งที่ Dispatcher ส่งรูปไปให้ vLLM อ่าน จะเพิ่ม `attempts` ใน PostgreSQL (`1 → 2 → 3`)
2. หาก vLLM ตอบ `{"unreadable": true}` หรือเกิดข้อผิดพลาดซ้ำในครั้งที่ 1–2 ระบบคืนสถานะเป็น `queued` เพื่อลองใหม่
3. เมื่อล้มเหลวครบ **3 ครั้ง** (`attempts = 3`) ระบบเปลี่ยนสถานะใน PostgreSQL เป็น **`unreadable`** พร้อมบันทึก `unreadable_reason` และหยุดส่งกลับไปที่ GPU โดยอัตโนมัติ (ไม่มีการวนซ้ำไม่รู้จบ)
4. ใบในสถานะ `unreadable` จะปรากฏในหน้า **`/unreadable` ("อ่านไม่ได้ ให้คนพิมพ์เอง")** พร้อมรูปต้นฉบับที่เก็บอยู่ใน volume `uploads` ของฝั่งเว็บ ให้พนักงานบัญชีเปิดพิมพ์ 5 ช่องเองและกดยืนยันได้ทันที

## 4. ความทนทานเมื่อ GPU Replica ล่ม (NFR-06)

- **NGINX Passive Health Check** (`max_fails=1 fail_timeout=30s` + `proxy_next_upstream error timeout http_502 http_503 http_504`): เมื่อ vLLM Replica ตัวใดตัวหนึ่งดับ NGINX ตัดออกทันทีและส่งคำขอทั้งหมดไปยัง Replica ที่เหลือ
- **PostgreSQL Outbox & State Machine**: รูปต้นฉบับและสถานะของใบเสร็จทุกใบถูกเก็บบนเครื่องสำนักงานตลอดเวลา แม้ลบเครื่อง GPU บน Vast.ai ทิ้ง ข้อมูลบัญชีและใบเสร็จก็ไม่สูญหาย
