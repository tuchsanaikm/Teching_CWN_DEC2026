#!/usr/bin/env python3
"""poster-team v0 — หัวข้ออีเวนต์ → ข้อความโปสเตอร์ + ภาพ (ตรวจข้ามค่าย) + หน้าเว็บ 1 หน้า
สร้าง graph.json จากแผนต้นแบบ แล้วส่งให้ agent-team (team.py) รัน · ไม่แก้ไฟล์ของ agent-team
"""
import argparse, json, os, subprocess, sys

TEAM = os.environ.get("AGENT_TEAM_PY",
                      "/root/ai-accounts/.Claude/shared/skills/agent-team/scripts/team.py")
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "graph.template.json")


def build(topic, out, diff, details):
    with open(TEMPLATE, encoding="utf-8") as f:
        raw = f.read()
    extra = f" รายละเอียดที่ผู้ใช้ให้ (ต้องใช้ตามนี้ ห้ามเปลี่ยน): {details}" if details else \
        " ผู้ใช้ไม่ได้ให้วันเวลา/สถานที่ ให้กำหนดเองอย่างสมเหตุสมผล"
    for k, v in {"TOPIC": topic, "OUT": out, "DETAILS": extra}.items():
        raw = raw.replace("{" + k + "}", json.dumps(v, ensure_ascii=False)[1:-1])
    g = json.loads(raw)
    for n in g["nodes"]:
        n["difficulty"] = diff
    return g


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("topic", nargs="?", help="หัวข้องานอีเวนต์")
    ap.add_argument("--topic-file", help="อ่านหัวข้อจากไฟล์ UTF-8 (กันปัญหาภาษาไทยใน shell)")
    ap.add_argument("--out", required=True, help="โฟลเดอร์ผลลัพธ์ (absolute ใน container)")
    ap.add_argument("--difficulty", type=int, default=2, choices=range(1, 7))
    ap.add_argument("--details", default="", help="วันเวลา/สถานที่จริง (ถ้ามี)")
    ap.add_argument("--workers", default="", help="ส่งต่อให้ team.py --workers")
    ap.add_argument("--graph-only", action="store_true", help="เขียน graph.json แล้วหยุด")
    ap.add_argument("--dry-run", action="store_true", help="team.py --dry-run")
    a = ap.parse_args()
    topic = open(a.topic_file, encoding="utf-8").read().strip() if a.topic_file else a.topic
    if not topic:
        ap.error("ต้องระบุหัวข้อ")
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    gpath = os.path.join(out, "graph.json")
    with open(gpath, "w", encoding="utf-8") as f:
        json.dump(build(topic, out, a.difficulty, a.details), f, ensure_ascii=False, indent=1)
    print(f"graph: {gpath}")
    if a.graph_only:
        return 0
    cmd = [sys.executable, TEAM, "run", gpath]
    if a.workers:
        cmd += ["--workers", a.workers]
    if a.dry_run:
        cmd.append("--dry-run")
    with open(os.path.join(out, "run.log"), "w", encoding="utf-8") as log:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
        for line in p.stdout:
            sys.stdout.write(line); log.write(line)
        rc = p.wait()
    files = [x for x in ("text.md", "art.png", "index.html") if os.path.exists(os.path.join(out, x))]
    print(f"\nผลงานใน {out}: {', '.join(files) or '(ไม่มี)'}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
