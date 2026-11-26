# สรุปงาน LAB 6 ขั้นที่ 1: NGINX เป็นประตูเดียวของระบบ

NGINX 1.27.5 รันเป็น container ด้วย udocker จาก image `nginx:1.27` แล้ว และระบบแบบที่ 1 (GPU 1 ใบ · server 1 ตัว · โหมดทีละรูป) เปิดอยู่ ผ่านการทดสอบจากนอกเครื่องครบ 7 ข้อ บนเครื่องเช่าไม่ได้ติดตั้ง NGINX ลงเครื่อง

**เครื่องยังเปิดอยู่และคิดเงินต่อ** — instance `<id>` ป้าย `vapp-lab6-nginx` สถานะ running RTX 3090 2 ใบ ราคา $0.3578/ชม. ผมไม่ได้ destroy

## ไฟล์ตั้งค่า `code/nginx.conf` ทีละส่วน

| ส่วน | ตั้งค่าอะไร | เหตุผล |
|---|---|---|
| 1. process | `user root` · `worker_processes 4` · `worker_rlimit_nofile 16384` · ไฟล์ pid และ error log อยู่ใน `/var/log/nginx` | udocker ไม่มี user namespace จึงให้ worker เป็นผู้ใช้เดียวกับ master · ไม่ใช้ `auto` เพราะจะได้ 64 worker ขณะที่โควตา CPU มีราว 25 core · โฟลเดอร์ log เชื่อมกับ `logs/nginx` บนเครื่อง ทำให้ `cluster.sh` อ่าน pid ได้ |
| `events` | `worker_connections 4096` | คำขอที่ส่งต่อ 1 รายการใช้ 2 connection (ฝั่งผู้ใช้และฝั่ง server) |
| 2. log | รูปแบบ `lb` บันทึกสถานะ ขนาดคำขอ เวลารวม server ที่ตอบ และเวลาของ server | ใช้ดูว่าคำขอไปตัวไหน · ไม่บันทึก header `Authorization` จึงไม่มี key ใน log |
| 3. ขนาดไฟล์ | `client_max_body_size 20m` · `client_body_buffer_size 2m` | เพดานเท่ากับของ server · รูปทั่วไปอยู่ใน RAM ไม่ต้องเขียนไฟล์ชั่วคราว |
| 4. `upstream detect_servers` | รายชื่อ `server 127.0.0.1:81xx/82xx` ระหว่างบรรทัด `BEGIN SERVERS` กับ `END SERVERS` · `zone 64k` · `keepalive 64` | ไม่ใส่คำสั่งเลือกวิธีแจกงาน จึงเป็น Round Robin · `zone` ทำให้ worker ทั้ง 4 ใช้ลำดับวนชุดเดียวกัน · `cluster.sh` แก้เฉพาะรายชื่อ server ช่วงนี้ |
| 5. `server` พอร์ต 8080 | `/lb/health` · `/health` · `/v1/` · ที่เหลือ | `/lb/health` NGINX ตอบเอง · `/health` ส่งต่อให้ server · `/v1/` ถ้าไม่มี header `Authorization` NGINX ตอบ 401 ทันที ถ้ามีก็ส่งต่อให้ server ตรวจ key (NGINX ไม่รู้ค่า key) · path อื่นตอบ 404 |
| ใน `/v1/` | `proxy_http_version 1.1` · `proxy_request_buffering on` · timeout 2s/30s/60s · `proxy_next_upstream error timeout` · header `X-Upstream` | รับไฟล์ครบก่อนแล้วส่งให้ server ทีเดียว · ถ้า server ต่อไม่ติดให้ลองตัวถัดไป · `X-Upstream` บอกว่า server ตัวไหนตอบ |

ตอนลองเปิด 4 server ครั้งแรกยังไม่มี `zone` ลำดับการแจกไม่วนตรง เพราะ worker แต่ละตัวนับรอบของตัวเอง หลังเพิ่ม `zone` ได้ลำดับ 8101 → 8201 → 8102 → 8202 วนครบ 3 รอบ

## เส้นทางของคำขอ 1 รายการ

```
ผู้ใช้ (นอกเครื่อง)
   │  POST /v1/detect  + รูป + Authorization: Bearer <key>
   ▼
203.0.113.10:‹port›          พอร์ตสาธารณะของ Vast.ai
   │  (map เข้า container ของเครื่องเช่า)
   ▼
NGINX :8080                    container nginx:1.27 ใน udocker (โหมด F3)
   │  1. ไม่มี header Authorization ─────► ตอบ 401 เอง (ไม่ถึง server)
   │  2. รับไฟล์รูปจนครบ (ไม่เกิน 20 MB)
   │  3. เลือก server แบบ Round Robin
   ▼
server 127.0.0.1:8101          uvicorn + FastAPI (รับเฉพาะภายในเครื่อง)
   │  4. ตรวจ key ─ ผิด ─────────────────► 401
   │  5. แปลงไฟล์เป็นภาพ แล้วเข้าคิว
   ▼
inference worker (1 thread)    หยิบ 1 รูปต่อการเรียกโมเดล (โหมด single)
   ▼
YOLO บน GPU 0                  ~48.5 ms
   │
   ▼  ผล JSON ย้อนกลับทางเดิม: worker → server → NGINX (+X-Upstream) → ผู้ใช้
```

## `code/cluster.sh`

| คำสั่ง | ทำอะไร |
|---|---|
| `cluster.sh up --gpus 1\|2 --per-gpu N --mode single\|micro` | ปิดระบบเดิม → เขียนรายชื่อ server ลง `nginx.conf` → เปิด server ทุกตัวพร้อมกัน → รอจน `/health` ตอบ 200 ครบทุกตัว → เปิด NGINX → ตรวจว่าเข้าถึงทุก server ผ่านพอร์ต 8080 → จึงพิมพ์ `READY` |
| `cluster.sh status` | แสดงรูปแบบที่เปิดอยู่ สถานะ server แต่ละตัว NGINX พอร์ตที่เปิดฟัง และหน่วยความจำ GPU |
| `cluster.sh down` | ปิด NGINX ก่อน แล้วปิด server ทุกตัว |

- **พอร์ต server:** GPU0 ใช้ 8101, 8102, … และ GPU1 ใช้ 8201, 8202, … ทุกตัวผูกกับ `127.0.0.1`
- **API key:** สุ่มเมื่อยังไม่มีไฟล์ `api_key.env` (สิทธิ์ 600) ครั้งต่อไปใช้ค่าเดิม เปิดใหม่ 3 ครั้งแล้ว hash ของไฟล์เท่าเดิม ส่วนทางสุ่มครั้งแรกทดสอบแยกในโฟลเดอร์ชั่วคราว เพราะบนเครื่องมี key อยู่ก่อนแล้ว
- **ลองรูปแบบอื่นด้วย:** 2 GPU × 2 server ทั้งโหมด micro และ single พร้อมใน 9–11 วินาที · `--gpus 3` ถูกปฏิเสธ · รูปแบบที่ 1 พร้อมใน 7 วินาที
- **ที่เพิ่มเอง:** ตั้ง `OMP_NUM_THREADS=4` ต่อ server เพื่อไม่ให้แต่ละ process เปิด thread ตาม 64 core ของเครื่อง

## ผลทดสอบจากนอกเครื่อง (รูปแบบที่ 1 ผ่านพอร์ตสาธารณะ ‹port› → 8080)

| # | ทดสอบ | คาดหวัง | ผล | ผู้ตอบ | เวลาฝั่งผู้ใช้ |
|---|---|---|---|---|---|
| 1 | `GET /lb/health` | 200 | 200 ✅ | NGINX | 609 ms |
| 2 | `GET /health` | 200 | 200 ✅ | server `gpu0-8101` (single, cuda:0) | 574 ms |
| 3 | ส่ง `sample-1.jpg` (48,766 bytes) พร้อม key | 200 | 200 ✅ | server `gpu0-8101` | 1,226 ms |
| 4 | ส่งรูปแบบไม่มี key | 401 | 401 ✅ | NGINX (ไม่ถึง server) | 596 ms |
| 5 | ส่งรูปพร้อม key ผิด | 401 | 401 ✅ | server | 1,178 ms |
| 6 | path อื่น | 404 | 404 ✅ | NGINX | 588 ms |
| 7 | ต่อพอร์ต server 8101 ตรงจากนอกเครื่อง | เข้าไม่ได้ | timeout ✅ | – | – |

- **ข้อ 3:** ได้ batch 1 รูป เวลาโมเดล 48.5 ms พบ 18 วัตถุ (Person 6 · Hardhat 5 · NO-Safety Vest 5 · Safety Vest 1 · NO-Hardhat 1)
- **เวลาฝั่งผู้ใช้:** ส่วนใหญ่เป็นเครือข่ายระหว่างที่นี่กับเครื่องเช่าในแคนาดา log ของ NGINX บันทึกเวลาที่ server ใช้ในข้อ 3 เพียง 0.064 วินาที
- **ข้อ 7:** `status` ยืนยันอีกทางว่าเปิดฟังแค่ `0.0.0.0:8080` กับ `127.0.0.1:8101`

## ไฟล์ใน `lab6_microbatch_lb/1_nginx`

- `code/nginx.conf`
- `code/cluster.sh`
- `code/test_lb.py`
- `results/lb_test.json`
- `results/cluster_status.txt`
- `results/nginx_access.log`
- `results/server_8101.log`

ค่า key ไม่ปรากฏในรายงาน ในไฟล์ผล หรือใน log