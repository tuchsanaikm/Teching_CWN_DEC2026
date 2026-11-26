import json, os

BASE = "/workspace/routes"
SIGN = BASE + "/sign.png"
SIGN_NUMBER = "482"
SEND = {"yolo": "yolo1", "cyolo": "cyolo1", "gyolo": "gyolo1"}
RECV = {"yolo": "yolo2", "cyolo": "cyolo2", "gyolo": "gyolo2"}
SHORT = {"yolo": "y", "cyolo": "c", "gyolo": "g"}

nodes = [{
    "id": "sign", "type": "image", "account": "cyolo1", "difficulty": 1, "path": SIGN,
    "prompt": ("A simple rectangular sign board with a bright yellow background and a thick black border. "
               "In the center, the number " + SIGN_NUMBER + " is written in very large, bold, black digits. "
               "No other text, letters or numbers anywhere in the image. Flat, clean, high contrast."),
}]
routes = []
for s in SEND:
    for r in RECV:
        rid = SHORT[s] + SHORT[r]
        sa, ra = SEND[s], RECV[r]
        d = f"{BASE}/{rid}"
        os.makedirs(d, exist_ok=True)
        routes.append({"route": rid, "sender": sa, "receiver": ra, "dir": d})
        common = {"difficulty": 1, "cwd": d, "board": False}
        # 1) short value
        nodes.append({**common, "id": f"{rid}_num_s", "account": sa, "expect": "int",
                      "prompt": "คิดเลขจำนวนเต็ม 4 หลัก (ระหว่าง 1000 ถึง 9998) ขึ้นมาเอง 1 จำนวน ตอบเฉพาะตัวเลขนั้นเท่านั้น ไม่มีข้อความอื่น"})
        nodes.append({**common, "id": f"{rid}_num_r", "account": ra, "expect": "int",
                      "depends_on": [f"{rid}_num_s"],
                      "prompt": "ผู้ส่งให้ตัวเลขนี้มา: {{" + rid + "_num_s}} ให้นำตัวเลขนี้บวก 1 แล้วตอบเฉพาะผลลัพธ์เป็นตัวเลขเท่านั้น ไม่มีข้อความอื่น"})
        # 2) long document
        doc = f"{d}/long.txt"
        nodes.append({**common, "id": f"{rid}_long_s", "account": sa, "expect": "contains:long.txt",
                      "prompt": (f"สร้างไฟล์ข้อความ {doc} (ใช้สคริปต์ เช่น python ช่วยเขียนได้) เป็นเอกสารยาว "
                                 "โดยเลือกจำนวนบรรทัดเองแบบสุ่มระหว่าง 1950 ถึง 2050 บรรทัด ทุกบรรทัดลงท้ายด้วย newline "
                                 "แต่ละบรรทัดเป็นประโยคภาษาไทยหรืออังกฤษทั่วไปที่ไม่ว่าง "
                                 "ให้มีบรรทัดรหัสลับเพียง 1 บรรทัด อยู่ใกล้กึ่งกลางไฟล์ (ห่างจากบรรทัดกลางไม่เกิน 50 บรรทัด) "
                                 "รูปแบบบรรทัดนั้นคือ 'SECRET: ' ตามด้วยรหัสสุ่ม 8 ตัวอักษร (A-Z และ 0-9) ที่คุณคิดเอง "
                                 "บรรทัดอื่นห้ามมีคำว่า SECRET "
                                 f"เมื่อเสร็จให้ตอบเฉพาะ absolute path ของไฟล์ ({doc}) บรรทัดเดียว ห้ามบอกรหัสลับหรือจำนวนบรรทัด")})
        nodes.append({**common, "id": f"{rid}_long_r", "account": ra, "expect": "json",
                      "depends_on": [f"{rid}_long_s"],
                      "prompt": ("ผู้ส่งส่งไฟล์เอกสารยาวมาที่ path: {{" + rid + "_long_s}} "
                                 "อ่านไฟล์นั้น (ใช้เครื่องมือได้ เช่น wc -l และ grep) หาบรรทัดรหัสลับที่ขึ้นต้นด้วย 'SECRET: ' และนับจำนวนบรรทัดทั้งหมดของไฟล์ "
                                 "ตอบเป็น JSON บรรทัดเดียวเท่านั้น รูปแบบ {\"secret\": \"<รหัส 8 ตัวหลัง SECRET: >\", \"lines\": <จำนวนบรรทัด>} ไม่มีข้อความอื่น")})
        # 3) image relay
        img = f"{d}/sign.png"
        nodes.append({**common, "id": f"{rid}_img_s", "account": sa, "expect": "contains:sign.png",
                      "depends_on": ["sign"],
                      "prompt": (f"คัดลอกไฟล์ภาพ {SIGN} ไปที่ {img} แบบไบต์ต่อไบต์ (เช่น cp) ห้ามแก้ไขไฟล์ และไม่ต้องเปิดดูภาพ "
                                 f"เมื่อเสร็จให้ตอบเฉพาะ absolute path ปลายทาง ({img}) บรรทัดเดียว")})
        nodes.append({**common, "id": f"{rid}_img_r", "account": ra, "expect": "int", "kind": "vision",
                      "depends_on": [f"{rid}_img_s"],
                      "prompt": ("ผู้ส่งส่งไฟล์ภาพป้ายมาที่ path: {{" + rid + "_img_s}} "
                                 "เปิดดูภาพนั้น บนป้ายมีตัวเลข 3 หลัก ตอบเฉพาะตัวเลขนั้นเท่านั้น ไม่มีข้อความอื่น")})

graph = {"goal": "ทดสอบการส่งข้อมูล 9 เส้นทาง (3 ค่าย x 3 ค่าย) x 3 แบบ: ค่าสั้น ข้อความยาว ภาพ", "nodes": nodes}
json.dump(graph, open(BASE + "/graph.json", "w"), ensure_ascii=False, indent=1)
json.dump({"sign_number": SIGN_NUMBER, "routes": routes}, open(BASE + "/routes.json", "w"), indent=1)
print(len(nodes), "nodes")
