# พรอมต์ของบท 01 · Docker + VS Code (หน้ารวม)

รวมพรอมต์และคำสั่งทั้งหมดของบทนี้ตามลำดับ คัดลอกไปวางได้ทันที คำอธิบาย ภาพ และผลจริงอยู่ใน [README.md](README.md)

**ก่อนเริ่ม:** Docker Desktop ขึ้น **Engine running**

## ขั้นที่ 3 · สร้าง container devtools

วางที่: Claude Code Desktop → **New session** → วางพรอมต์ → Enter

```text
ช่วยเตรียม container ชื่อ devtools ในเครื่องผม จาก image tuchsanai/devtools:2569_1

- ถ้ายังไม่มี ให้สร้างใหม่แบบ privileged (เพราะข้างในต้องใช้ Docker ได้)
  เปิด port 2222 → 22 สำหรับ SSH และ 8885 → 8888 สำหรับ JupyterLab ถ้า port ไหนชน ให้ใช้เลขว่างถัดไป
- ถ้ามีอยู่แล้ว ให้ใช้ตัวเดิม (ถ้าปิดอยู่ให้เปิด) ห้ามลบของเดิม

จากนั้นเข้าไปทำงานข้างใน container
1. ติดตั้ง Claude Code และ Codex ถ้ายังไม่มี และทำให้พิมพ์ claude ได้เลย
2. บอกว่าข้างในเป็น Linux อะไร มี Python, Node.js, Git, Claude Code และ Codex เวอร์ชันไหน
3. สร้างไฟล์ /workspace/hello.py ให้พิมพ์ว่า Hello from devtools แล้วลองรันให้ดู

สรุปผลเป็นตารางสั้น ๆ พร้อมบอก port ที่ใช้จริง
```

## ขั้นที่ 4 · อีกวิธี: สร้างใหม่จาก Claude Code ใน VS Code (ลบ devtools ตัวเดิมก่อน)

วางที่: Claude Code ใน VS Code → **New session** → วางพรอมต์ → ส่ง (ใช้แทนขั้นที่ 3)

```text
เตรียม container `devtools`:

1. ถ้ามี container `devtools` อยู่แล้ว ให้ลบด้วย `docker rm -f devtools`
2. ตรวจ port <SSH_PORT>=2222 และ <JUPYTER_PORT>=8885 ถ้าชน ให้ใช้ port ว่างถัดไป
3. รัน:

docker run -dit --name devtools --privileged \
  -p <SSH_PORT>:22 -p <JUPYTER_PORT>:8888 \
  tuchsanai/devtools:2569_1

docker exec -it devtools bash -c \
'curl -fsSL https://claude.ai/install.sh | bash && npm install -g @openai/codex'


4. ตรวจด้วย `claude --version` และ `codex --version` แล้วสรุป port ที่ใช้
```

## ขั้นที่ 6 · ตรวจเครื่องมือหลังเข้า container

วางที่: Terminal ใน container (VS Code Attach หรือ JupyterLab)

```bash
whoami
claude --version
codex --version
```
