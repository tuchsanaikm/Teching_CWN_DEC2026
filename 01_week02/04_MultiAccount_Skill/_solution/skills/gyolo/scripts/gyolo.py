#!/usr/bin/env python3
"""gyolo.py - Antigravity CLI accounts (gyolo1..N, binary agy): one-shot calls, image viewing,
readiness, quota, models, stats.

  python3 gyolo.py run "prompt" [-a gyolo2|gyolo] [-d 1..6 | -m MODEL -e EFFORT] [--image a.png] [--json]
  python3 gyolo.py image "description" --out /abs/path.png [-a gyolo1] [--ref old.png]   (image-generator subagent)
  python3 gyolo.py check [gyolo1 ...]     `gyoloN models` (signed in?) + real minimal call
  python3 gyolo.py quota [gyolo1 ...]     /usage (no model call), remaining % converted to used %
  python3 gyolo.py models [-a gyolo1]     `gyoloN models` + the 3-CLI difficulty table
  python3 gyolo.py stats [--run ID] [--account A]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import ma_common as mc  # noqa: E402


def pick_account(spec):
    """'gyolo3' -> itself; 'gyolo' / None -> ready account with the lowest known usage."""
    if spec and spec != "gyolo":
        if mc.cli_of(spec) != "gemini":
            sys.exit("บัญชี %s ไม่ใช่ Antigravity (gyoloN)" % spec)
        return spec
    accs = mc.list_accounts("gyolo")
    cached = mc.cached_check()
    missing = [a for a in accs if a not in cached]
    if missing:
        for r in mc.check_accounts(missing):
            cached[r["account"]] = r
    ready = [a for a in accs if cached.get(a, {}).get("status") == "ready"]
    if not ready:
        sys.exit("ไม่มีบัญชี Antigravity ที่พร้อม (รัน: gyolo.py check)")
    qc = mc.quota_cache_load()
    if len(ready) > 1:
        for a in ready:
            if mc.quota_used_pct(qc.get(a)) is None:   # no cached data yet: /usage (no model call)
                qc[a] = mc.gemini_quota(a)

    def used(a):
        v = mc.quota_used_pct(qc.get(a))
        return v if v is not None else 50
    ready.sort(key=used)
    return ready[0]


def cmd_run(a):
    prompt = sys.stdin.read() if a.prompt == "-" else a.prompt
    acc = pick_account(a.account)
    res = mc.call_gemini(acc, prompt, a.model, a.effort, cwd=a.cwd, timeout=a.timeout, images=a.image,
                         json_schema=a.schema, add_dirs=a.add_dir, node=a.node or "gyolo.run", run_id=a.run_id,
                         difficulty=a.difficulty)
    mc.print_result(res, a.json)
    return 0 if res["ok"] else 1


def cmd_image(a):
    acc = pick_account(a.account)
    out = "/" + os.path.normpath(os.path.abspath(a.out)).lstrip("/")
    prompt = "สร้างภาพ (image generation) ตามคำอธิบายนี้: %s" % a.description
    res = mc.call_gemini_image(acc, prompt, out, a.model, timeout=a.timeout, node="gyolo.image", refs=a.ref)
    mc.print_result(res, a.json)
    if not a.json:
        print("PNG: %s (%s)" % (out, "ตรวจ signature + เขียนระหว่างการเรียก ผ่าน" if res["png_ok"] else
                                "ไม่ผ่าน: %s" % res["status"]), file=sys.stderr)
    return 0 if res["ok"] else 1


def cmd_check(a):
    res = mc.check_accounts(a.accounts or mc.list_accounts("gyolo"))
    print(json.dumps(res, ensure_ascii=False, indent=1) if a.json else mc.check_table(res))
    return 0


def cmd_quota(a):
    txt, data = mc.quota_table(a.accounts or mc.list_accounts("gyolo"))
    print(json.dumps(data, ensure_ascii=False, indent=1) if a.json else txt)
    return 0


def cmd_models(a):
    models, as_of = mc.gemini_models(a.account, refresh=True)
    if not models:
        print("อ่านรายชื่อรุ่นไม่ได้ (ไม่มีบัญชี gyolo ที่ล็อกอิน) · ตารางด้านล่างเป็นค่าที่สกิลตั้งไว้")
    else:
        print("จาก `gyolo models` (ข้อมูล %s) · effort อยู่ในชื่อรุ่น (-low/-medium/-high/-xhigh)\n" %
              (as_of or "-")[:19].replace("T", " "))
        print(mc.table(["id", "ชื่อ"], [[m["id"], m["name"]] for m in models]))
    print("\n" + mc.table(["difficulty", "Antigravity รุ่น"],
                          [[d, mc.gemini_resolve(None, None, a.account, d)[0]] for d in sorted(mc.GEMINI_DIFFICULTY)]))
    print("\nตารางความยากของ 3 CLI:\n" + mc.difficulty_table())
    print("\nบัญชี: " + ", ".join(mc.list_accounts("gyolo")))
    return 0


def cmd_stats(a):
    rows = [r for r in mc.read_ledger() if r.get("cli") == "gemini"]
    if a.run:
        rows = [r for r in rows if r.get("run_id") == a.run]
    if a.account:
        rows = [r for r in rows if r.get("account") == a.account]
    if not rows:
        print("ยังไม่มีสถิติของ Antigravity ใน %s" % mc.GLOBAL_LEDGER)
        return 0
    print(mc.stats_tables(rows))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Antigravity (agy) multi-account helper")
    sp = ap.add_subparsers(dest="cmd")
    r = sp.add_parser("run", help="one non-interactive call")
    r.add_argument("prompt", help='prompt text, or "-" to read stdin')
    r.add_argument("-a", "--account", help="gyoloN, or 'gyolo' = ready account with most quota")
    r.add_argument("-d", "--difficulty", type=int, default=2, choices=range(1, 7))
    r.add_argument("-m", "--model", help="model id or family from `models` (e.g. gemini-4-hydrogen-high)")
    r.add_argument("-e", "--effort", choices=mc.GEMINI_EFFORTS, help="replaces the effort part of the model id")
    r.add_argument("--cwd", help="working directory of the agent (default /tmp)")
    r.add_argument("--timeout", type=int, default=900)
    r.add_argument("--image", nargs="+", help="image files the agent should look at (absolute paths)")
    r.add_argument("--schema", help="JSON schema string or file -> structured answer")
    r.add_argument("--add-dir", nargs="+")
    r.add_argument("--node")
    r.add_argument("--run-id")
    r.add_argument("--json", action="store_true")
    im = sp.add_parser("image", help="generate or edit a PNG with agy's image tool (fails clearly when unavailable)")
    im.add_argument("description")
    im.add_argument("--out", required=True, help="absolute .png path")
    im.add_argument("--ref", nargs="+", help="existing image(s) to start from: edit / keep the same subject")
    im.add_argument("-a", "--account")
    im.add_argument("-m", "--model", help="model that drives the image subagent (default difficulty 2)")
    im.add_argument("--timeout", type=int, default=600)
    im.add_argument("--json", action="store_true")
    for name in ("check", "quota"):
        c = sp.add_parser(name)
        c.add_argument("accounts", nargs="*")
        c.add_argument("--json", action="store_true")
    m = sp.add_parser("models")
    m.add_argument("-a", "--account")
    s = sp.add_parser("stats")
    s.add_argument("--run")
    s.add_argument("--account")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 0
    return {"run": cmd_run, "image": cmd_image, "check": cmd_check, "quota": cmd_quota, "models": cmd_models,
            "stats": cmd_stats}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
