# Lab 5 · model parallel · 3 nodes — สรุปการเตรียมเครื่อง (2026-11-22)

| Node | ป้าย | instance | เครื่อง (machine) | ที่ตั้ง | GPU | $/ชม. |
|---|---|---|---|---|---|---|
| 1 | vapp-lab5-3mp-1 | <id> | 146898 | Argentina | 2x RTX 3090 | 0.3900 |
| 2 | vapp-lab5-3mp-2 | <id> | 153725 | Chile | 2x RTX 3090 | 0.4433 |
| 3 | vapp-lab5-3mp-3 | <id> | 31034 | Chile | 2x RTX 3090 | 0.4967 |

Image: vastai/pytorch:2.8.0-cuda-12.8.1-py312-24.04 (torch 2.8.0+cu128, CUDA 12.8) · disk 60 GB
Node 1 เปิด container port 9000 -> public 203.0.113.10:<ext_port>

## เน็ตระหว่าง Node (TCP ผ่าน port ของ Node 1, วัด 2 รอบ รอบละ 10 วินาทีต่อทิศ)

| เส้นทาง | ต่อได้ | RTT เฉลี่ย (ms) | Node N -> Node 1 (Mbit/s) | Node 1 -> Node N (Mbit/s) |
|---|---|---|---|---|
| Node 2 -> Node 1 | ได้ | 34.2 / 35.6 | 644 / 210 | 262 / 619 |
| Node 3 -> Node 1 | ได้ | 28.8 / 29.4 | 82 / 306 | 198 / 148 |

## โมเดลและ Dataset (เหมือนกันทั้ง 3 Node)

- Qwen/Qwen3-8B 16.4 GB ที่ /workspace/lab5/models/Qwen3-8B
- b-mc2/sql-create-context ทั้งหมด 78,577 แถว · shuffle seed 0
- train.jsonl 4,000 แถว sha256 3909c13e48e0… · test.jsonl 200 แถว sha256 dc94781a397b… (ตรงกันทั้ง 3 Node)
