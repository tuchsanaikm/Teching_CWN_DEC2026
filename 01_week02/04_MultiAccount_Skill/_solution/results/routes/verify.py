import json, os, re, sys, hashlib

run_id = sys.argv[1]
RUN = f"/workspace/.agent-team/{run_id}"
BASE = "/workspace/routes"
meta = json.load(open(BASE + "/routes.json"))
SIGN_NUMBER = meta["sign_number"]
NAMES = {"y": "Claude", "c": "Codex", "g": "Antigravity"}

def out(node):
    p = f"{RUN}/out/{node}.md"
    return open(p, encoding="utf-8").read().strip() if os.path.exists(p) else None

state = json.load(open(f"{RUN}/state.json"))
nstate = state.get("nodes", {})

dur = {}
for line in open(f"{RUN}/ledger.jsonl"):
    try:
        e = json.loads(line)
    except Exception:
        continue
    n = e.get("node")
    if n and e.get("duration_s") is not None and not e.get("event"):
        dur[n] = dur.get(n, 0) + float(e["duration_s"])

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None

sign_sha = sha(BASE + "/sign.png")
rows, details = [], []
for r in meta["routes"]:
    rid, d = r["route"], r["dir"]
    res = {}
    # 1) short value
    s, v = out(f"{rid}_num_s"), out(f"{rid}_num_r")
    ok, why = False, ""
    try:
        si, vi = int(s), int(v)
        ok = 1000 <= si <= 9999 and vi == si + 1
        why = f"{si}+1={si+1}, ผู้รับตอบ {vi}"
    except Exception:
        why = f"ส่ง={s!r} รับ={v!r}"
    res["num"] = (ok, dur.get(f"{rid}_num_s", 0) + dur.get(f"{rid}_num_r", 0), why)
    # 2) long document: open the file ourselves
    fp = f"{d}/long.txt"
    ok, why = False, ""
    if os.path.exists(fp):
        raw = open(fp, encoding="utf-8", errors="replace").read()
        nl = raw.count("\n")
        lines = raw.splitlines()
        hits = [(i + 1, l) for i, l in enumerate(lines) if "SECRET" in l]
        m = re.fullmatch(r"SECRET: ([A-Z0-9]{8})", hits[0][1].strip()) if len(hits) == 1 else None
        true_secret = m.group(1) if m else None
        rv = out(f"{rid}_long_r") or ""
        try:
            j = json.loads(re.search(r"\{.*\}", rv, re.S).group(0))
            got_s, got_n = str(j.get("secret", "")).strip(), int(j.get("lines"))
        except Exception:
            got_s, got_n = None, None
        ok = bool(true_secret) and got_s == true_secret and got_n in (nl, len(lines))
        pos = hits[0][0] if len(hits) == 1 else None
        why = (f"ไฟล์จริง {len(lines)} บรรทัด (wc -l={nl}), SECRET {len(hits)} บรรทัด ที่บรรทัด {pos} = {true_secret}; "
               f"ผู้รับตอบ secret={got_s} lines={got_n}")
    else:
        why = "ไม่พบไฟล์ long.txt"
    res["long"] = (ok, dur.get(f"{rid}_long_s", 0) + dur.get(f"{rid}_long_r", 0), why)
    # 3) image: copy must be byte-identical, receiver must read the number
    ip = f"{d}/sign.png"
    cp_ok = sha(ip) is not None and sha(ip) == sign_sha
    v = out(f"{rid}_img_r")
    ok = cp_ok and (v or "").strip() == SIGN_NUMBER
    why = f"สำเนาตรงต้นฉบับ={cp_ok}, ผู้รับตอบ {v!r} (เฉลย {SIGN_NUMBER})"
    res["img"] = (ok, dur.get(f"{rid}_img_s", 0) + dur.get(f"{rid}_img_r", 0), why)
    r["res"] = res
    r["status"] = {k: nstate.get(k, {}).get("status") for k in
                   [f"{rid}_{t}_{x}" for t in ("num", "long", "img") for x in ("s", "r")]}

def cell(t):
    ok, sec, _ = t
    return f"{'✅ ถูก' if ok else '❌ ผิด'} ({sec:.1f} s)"

L = ["# สรุปการทดสอบส่งข้อมูลระหว่างบัญชี 9 เส้นทาง", "",
     f"- run: `{run_id}` (agent-team, ความยากทุกงาน = 1: Claude haiku/low · Codex gpt-6.2-sol/low · Antigravity gemini-3.8-flash-low)",
     "- ผู้ส่ง = บัญชีหมายเลข 1 (yolo1 / cyolo1 / gyolo1) · ผู้รับ = บัญชีหมายเลข 2 (yolo2 / cyolo2 / gyolo2) → ค่ายเดียวกันจึงเป็นการส่งข้ามบัญชีเสมอ",
     "- เวลา = เวลาผู้ส่ง + เวลาผู้รับ (duration_s จาก ledger ของ run) ไม่รวมเวลารอคิว",
     f"- ภาพป้ายสร้างครั้งเดียวโดย Codex (cyolo1) ที่ `/workspace/routes/sign.png` ตัวเลขเฉลย **{SIGN_NUMBER}** ใช้เวลา {dur.get('sign', 0):.1f} s (ไม่นับรวมในตาราง)",
     "- ตรวจคำตอบเองด้วยสคริปต์ `verify.py`: ค่าสั้นคำนวณ +1 ใหม่ · ข้อความยาวเปิดไฟล์จริงนับบรรทัดและหาบรรทัด SECRET · ภาพเทียบ SHA-256 ของสำเนากับต้นฉบับ และเปิดดูภาพต้นฉบับเองว่าเป็นเลขเฉลยจริง", "",
     "| เส้นทาง | ค่าสั้น | ข้อความยาว | ภาพ |", "|---|---|---|---|"]
allt, wrong = [], []
for r in meta["routes"]:
    rid, res = r["route"], r["res"]
    name = f"{r['sender']} ({NAMES[rid[0]]}) → {r['receiver']} ({NAMES[rid[1]]})"
    L.append(f"| {name} | {cell(res['num'])} | {cell(res['long'])} | {cell(res['img'])} |")
    tot = sum(v[1] for v in res.values())
    allt.append((tot, name, res))
    for k, lab in (("num", "ค่าสั้น"), ("long", "ข้อความยาว"), ("img", "ภาพ")):
        if not res[k][0]:
            wrong.append(f"{name} · {lab}: {res[k][2]}")
allt.sort(reverse=True)
tests = [(v[1], f"{n} · {lab}") for _, n, res in allt for k, lab in (("num", "ค่าสั้น"), ("long", "ข้อความยาว"), ("img", "ภาพ")) for v in [res[k]]]
tests.sort(reverse=True)
L += ["", "## เส้นทางที่ช้าที่สุด", "",
      f"- รวม 3 การทดสอบ: **{allt[0][1]}** = {allt[0][0]:.1f} s (เร็วสุด: {allt[-1][1]} = {allt[-1][0]:.1f} s)",
      f"- การทดสอบเดี่ยวที่ช้าที่สุด: **{tests[0][1]}** = {tests[0][0]:.1f} s", "",
      "| อันดับ | เส้นทาง | เวลารวม (s) |", "|---|---|---|"]
L += [f"| {i+1} | {n} | {t:.1f} |" for i, (t, n, _) in enumerate(allt)]
L += ["", "## เส้นทางที่ผิด", ""] + ([f"- {w}" for w in wrong] or ["- ไม่มี — ถูกต้องครบทั้ง 27 การทดสอบ"])
L += ["", "## รายละเอียดการตรวจ", ""]
for r in meta["routes"]:
    L.append(f"- **{r['sender']} → {r['receiver']}**")
    for k, lab in (("num", "ค่าสั้น"), ("long", "ข้อความยาว"), ("img", "ภาพ")):
        L.append(f"  - {lab}: {r['res'][k][2]}")
open(BASE + "/summary.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
print("\nNODE STATUS:", json.dumps({r["route"]: r["status"] for r in meta["routes"]}, ensure_ascii=False))
