# Pure LAB 6 AI Serving Stack (`ai/serving/`)

โฟลเดอร์นี้บรรจุสแต็กฝั่ง AI แบบ **Pure NGINX LAB 6** สำหรับเครื่อง **`2× RTX 4090`** (ไม่มีโบรกเกอร์คิวภายนอก):

| ไฟล์ | หน้าที่ |
|---|---|
| `server.py` | FastAPI + Ultralytics YOLO11s พร้อม Single-Thread Dynamic Micro-batching (`MODE=micro`, `MAX_BATCH=16`, `MAX_WAIT_MS=15`) และ Bearer Auth |
| `nginx.conf` | ประตูรับงานพอร์ต `8080` ตั้งค่า `least_conn`, `proxy_next_upstream` (Failover ON), `client_max_body_size 20m` และ Header `X-Upstream` |
| `cluster.sh` | สคริปต์สั่งเปิด/ปิด/สลับโหมดทั้งคลัสเตอร์ (`up --gpus 2 --per-gpu 4 --mode micro --lb lc --failover on`) |
| `loadgen.py` | เครื่องมือยิงโหลดแบบ closed-loop วัดความจุ (ผู้ใช้พร้อมกัน), RPS, p95 และทดสอบ Failover |

## คำสั่งเปิดใช้งานชุดที่ชนะการวัดผล (88 ผู้ใช้พร้อมกัน · 444.55 RPS · 0% Failover Error)

```bash
export API_KEY="<your-api-key>"
export MODEL_PATH="/workspace/best.pt"
bash cluster.sh up --gpus 2 --per-gpu 4 --mode micro --lb lc --failover on
```
