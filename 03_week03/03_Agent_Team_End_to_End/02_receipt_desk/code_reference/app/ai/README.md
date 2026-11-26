# ReceiptDesk · AI Serving & LoRA Training (NGINX + 2× vLLM Architecture)

โฟลเดอร์นี้เก็บส่วนฝั่ง AI ของระบบ ReceiptDesk ที่ทำงานด้วยสถาปัตยกรรม **NGINX + 2× vLLM** บนเครื่อง `1 โหนด × 2× RTX 4090` (เชื่อมต่อตรงผ่าน HTTP/SSE):

- **`nginx/nginx.conf`** — NGINX 1.27 Reverse Proxy & Load Balancer (`least_conn`, `proxy_buffering off`, Bearer API Key Auth, `X-Replica: gpu0/gpu1`, Passive Failover `max_fails=1 fail_timeout=30s`) ส่งงานตรงไปยัง vLLM 2 Replicas (`127.0.0.1:8001` บน GPU 0 และ `127.0.0.1:8002` บน GPU 1) ด้วย Continuous Batching (`--max-num-seqs 256`)
- **`train/`** — โค้ด Training LoRA (`train_lora.py`, `receipt_common.py`, `evaluate.py`) สำหรับ fine-tune โมเดล `Qwen/Qwen3-VL-2B-Instruct` ด้วย CORD-v2 (1 GPU vs 2 GPUs Data Parallelism) และวัดผล M1–M6 ตาม Acceptance Gate

สคริปต์ควบคุมคลัสเตอร์บน Vast.ai และ benchmark AI Serving อยู่ที่ [`../../lb/`](../../lb/).
