#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Multi-account CLI skill script — self-contained, Python standard library only.
# Runs inside the `multi-account` container; when started on the host it copies itself
# into the container and re-runs there via `docker exec` (images/outputs are shuttled).
# Never reads credential files, never logs in, never prints e-mail addresses.
import argparse
import concurrent.futures as cf
import datetime as dt
import glob
import hashlib
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid

CONTAINER = os.environ.get("AI_SKILL_CONTAINER", "multi-account")
BASE = os.environ.get("AI_ACCOUNTS_BASE", "/root/ai-accounts").rstrip("/")
LOG_PATH = os.environ.get("AI_SKILL_LOG", BASE + "/.skill-usage/usage.jsonl")
WORK = os.environ.get("AI_SKILL_WORK", "/tmp/ai-skills")
QUOTA_CACHE_SECS = 120
MODELS_CACHE_SECS = 6 * 3600
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SECRET_RE = re.compile(r"(?i)(bearer\s+|token[\"'=: ]+|api[_-]?key[\"'=: ]+|sk-)[A-Za-z0-9._\-]{8,}")
RETRYABLE = {"not_logged_in", "auth_error", "rate_limited"}
EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_NO_ACCOUNT = 0, 1, 2, 3


# ----------------------------------------------------------------- helpers
def now():
    return dt.datetime.now().astimezone()


def iso(t=None):
    return (t or now()).isoformat(timespec="seconds")


def epoch_iso(sec):
    try:
        return dt.datetime.fromtimestamp(float(sec)).astimezone().isoformat(timespec="seconds")
    except Exception:
        return None


def eprint(*a):
    print(*a, file=sys.stderr, flush=True)


def scrub(s, n=300):
    s = EMAIL_RE.sub("<email>", str(s or ""))
    s = SECRET_RE.sub(r"\1<redacted>", s)
    s = re.sub(r"https?://\S+", "<url>", s)
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n] + "..."


def fingerprint(value):
    """Short one-way id so duplicate logins can be spotted without showing the e-mail."""
    if not value:
        return None
    return hashlib.sha256(str(value).strip().lower().encode()).hexdigest()[:8]


ACCOUNT_CMD_RE = re.compile(r"^(c|g)?yolo\d+$")


def audit(cmd):
    """If AI_SKILL_AUDIT is set, record which account wrapper was invoked (never the prompt)."""
    path = os.environ.get("AI_SKILL_AUDIT")
    if not path or not cmd or not ACCOUNT_CMD_RE.match(os.path.basename(str(cmd[0]))):
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{iso()}\t{os.path.basename(str(cmd[0]))}\t{cmd[1] if len(cmd) > 1 else ''}\n")
    except OSError:
        pass


def sh(cmd, input_text=None, timeout=60, cwd=None):
    t0 = time.time()
    audit(cmd)
    try:
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd,
                             start_new_session=True)
    except FileNotFoundError as e:
        return {"rc": 127, "out": "", "err": str(e), "timed_out": False, "secs": 0.0}
    timed_out = False
    try:
        out, err = p.communicate(input=input_text.encode("utf-8") if input_text is not None else None,
                                 timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except Exception:
            p.kill()
        out, err = p.communicate()
    return {"rc": p.returncode, "out": out.decode("utf-8", "replace"), "err": err.decode("utf-8", "replace"),
            "timed_out": timed_out, "secs": round(time.time() - t0, 2)}


def json_lines(text):
    for line in (text or "").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                yield json.loads(line)
            except ValueError:
                pass


def image_kind(path):
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except OSError:
        return None
    if head.startswith(b"\x89PNG"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def classify(text):
    t = (text or "").lower()
    if any(k in t for k in ("not logged in", "please run /login", "please sign in", "sign in to",
                            "authentication failed or timed out", "no credentials")):
        return "not_logged_in"
    if any(k in t for k in ("401", "unauthorized", "token expired", "expired token", "invalid_grant",
                            "refresh token", "authentication")):
        return "auth_error"
    if any(k in t for k in ("rate limit", "rate_limit", "usage limit", "429", "quota", "exhausted",
                            "limit reached", "out of credits", "hit your limit")):
        return "rate_limited"
    if any(k in t for k in ("503", "no capacity", "overloaded", "unavailable")):
        return "capacity"
    if "model" in t and any(k in t for k in ("not supported", "not recognized", "issue with the selected model",
                                            "does not exist", "invalid model", "unknown model")):
        return "bad_model"
    if "timed out" in t or "timeout" in t:
        return "timeout"
    return "cli_error"


def table(rows, cols):
    if not rows:
        return "(none)"
    w = {c: max(len(c), *(len(str(r.get(c, "") if r.get(c) is not None else "-")) for r in rows)) for c in cols}
    def fmt(r):
        return "  ".join(str(r.get(c) if r.get(c) is not None else "-").ljust(w[c]) for c in cols).rstrip()
    head = "  ".join(c.ljust(w[c]) for c in cols).rstrip()
    return "\n".join([head, "  ".join("-" * w[c] for c in cols)] + [fmt(r) for r in rows])


def read_cache(name, max_age):
    p = os.path.join(WORK, "cache", name)
    try:
        if time.time() - os.path.getmtime(p) <= max_age:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    except (OSError, ValueError):
        pass
    return None


def write_cache(name, data):
    try:
        os.makedirs(os.path.join(WORK, "cache"), exist_ok=True)
        with open(os.path.join(WORK, "cache", name), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


def log_usage(rec):
    """Central usage log: one JSON line per call. Never contains prompt, answer or secrets."""
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            try:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_EX)
            except Exception:
                pass
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError as e:
        eprint(f"[warn] could not write usage log {LOG_PATH}: {e}")


# ----------------------------------------------------------------- vendor base
class Vendor:
    key = prefix = label = ""
    can_generate_images = False
    can_read_images = True
    DIFF = {}            # difficulty -> [(model, effort), ...] in fallback order
    CHECK_MODEL = (None, None)
    IMAGE_MODEL = (None, None)
    login_hint = ""

    # ---- accounts
    def accounts(self):
        """Accounts this run may touch. AI_SKILL_ACCOUNTS="yolo2,cyolo1" restricts every command
        (check, quota, models, auto choice) to those names; other accounts are never invoked."""
        allowed = os.environ.get("AI_SKILL_ACCOUNTS")
        found = self.all_accounts()
        if allowed is None:
            return found
        names = {x.strip() for x in allowed.split(",") if x.strip()}
        return [a for a in found if a in names or self.prefix in names]

    def all_accounts(self):
        found = set()
        for d in os.environ.get("PATH", "").split(os.pathsep):
            for p in glob.glob(os.path.join(d, self.prefix + "[0-9]*")):
                n = os.path.basename(p)
                if re.fullmatch(re.escape(self.prefix) + r"\d+", n) and os.access(p, os.X_OK):
                    found.add(n)
        return sorted(found, key=lambda n: int(n[len(self.prefix):]))

    def norm_account(self, a):
        if a in (None, "", "auto"):
            return "auto"
        a = str(a).strip()
        if a.isdigit():
            a = self.prefix + a
        if a not in self.accounts():
            why = "not in AI_SKILL_ACCOUNTS" if a in self.all_accounts() else "unknown account"
            raise SystemExit(f"{why} '{a}'. allowed: {', '.join(self.accounts()) or '(none)'}")
        return a

    # ---- to implement per vendor
    def probe_login(self, acct):          # -> {logged_in: bool|None, plan, ident, detail}
        raise NotImplementedError

    def quota(self, acct):                # -> {ok, windows:[{name,used_pct,resets_at}], as_of, source, note}
        raise NotImplementedError

    def list_models(self, acct):          # -> [{"id","name","efforts"}]
        raise NotImplementedError

    def relevant_used(self, q, model):    # -> float|None
        vals = [w["used_pct"] for w in q.get("windows", []) if w.get("used_pct") is not None]
        return max(vals) if vals else None

    def build_run(self, acct, model, effort, prompt, images, cwd, timeout, ctx):
        raise NotImplementedError

    def parse_run(self, proc, ctx):       # -> dict(ok, answer, model_used, tokens, error)
        raise NotImplementedError

    def image_gen(self, acct, model, effort, prompt, out, cwd, timeout):
        return {"ok": False, "error_kind": "unsupported",
                "error": f"{self.label} cannot generate images. Use the cyolo skill (Codex) instead."}

    # ---- models / difficulty
    def models_cached(self, acct=None, refresh=False):
        data = None if refresh else read_cache(f"{self.key}-models.json", MODELS_CACHE_SECS)
        if data:
            return data
        accts = [acct] if acct else self.accounts()
        for a in accts:
            if acct is None and self.probe_login(a).get("logged_in") is False:
                continue
            try:
                ms = self.list_models(a)
            except Exception:
                ms = None
            if ms:
                data = {"account": a, "as_of": iso(), "models": ms}
                write_cache(f"{self.key}-models.json", data)
                return data
        return None

    def resolve(self, difficulty, model, effort, avail_ids=None):
        if model:
            return model, effort
        cands = self.DIFF[difficulty]
        for m, e in cands:
            if avail_ids is None or m in avail_ids:
                return m, (effort or e)
        m, e = cands[0]
        return m, (effort or e)

    # ---- execution + logging
    def execute(self, acct, model, effort, prompt, images=(), cwd=None, timeout=600, kind="run",
                difficulty=None, ctx=None):
        res = self.call(acct, model, effort, prompt, images, cwd, timeout, ctx)
        self.log(res, kind, difficulty)
        return res

    def call(self, acct, model, effort, prompt, images=(), cwd=None, timeout=600, ctx=None):
        """One CLI invocation, verified, NOT logged (callers log once)."""
        ctx = ctx if ctx is not None else {}
        cwd = cwd or os.getcwd()
        if prompt.lstrip().startswith("/"):
            prompt = "Task: " + prompt      # a leading '/' would be treated as a slash command
        cmd, stdin_text = self.build_run(acct, model, effort, prompt, list(images), cwd, timeout, ctx)
        proc = sh(cmd, stdin_text, timeout=timeout + 30, cwd=cwd)
        res = self.parse_run(proc, ctx)
        res.setdefault("tokens", {})
        if proc["timed_out"]:
            res.update(ok=False, error_kind="timeout", error=f"no result within {timeout}s")
        if res.get("ok") and not (res.get("answer") or "").strip():
            res.update(ok=False, error_kind="empty_answer", error="CLI exited without an answer")
        if not res.get("ok") and not res.get("error_kind"):
            res["error_kind"] = classify(res.get("error"))
        res.update(account=acct, model=model, effort=effort, secs=proc["secs"], exit_code=proc["rc"])
        res["model_used"] = res.get("model_used") or model
        return res

    def log(self, res, kind, difficulty):
        t = res.get("tokens") or {}
        log_usage({
            "ts": iso(), "vendor": self.key, "account": res.get("account"), "kind": kind,
            "model": res.get("model_used") or res.get("model"), "effort": res.get("effort"),
            "difficulty": difficulty, "ok": bool(res.get("ok")),
            "error_kind": None if res.get("ok") else res.get("error_kind"),
            "secs": res.get("secs"), "tokens_in": t.get("in"), "tokens_out": t.get("out"),
            "tokens_cached": t.get("cached"), "tokens_reasoning": t.get("reasoning"), "tokens_total": t.get("total"),
        })

    # ---- account choice
    def quota_cached(self, acct):
        cache = read_cache(f"{self.key}-quota.json", QUOTA_CACHE_SECS) or {}
        if acct in cache:
            return cache[acct]
        q = self.quota(acct)
        cache = read_cache(f"{self.key}-quota.json", 10 ** 9) or {}
        cache[acct] = q
        write_cache(f"{self.key}-quota.json", cache)
        return q

    def rank_accounts(self, model):
        accts = self.accounts()
        with cf.ThreadPoolExecutor(max_workers=len(accts) or 1) as ex:
            logins = dict(zip(accts, ex.map(self.probe_login, accts)))
        usable = [a for a in accts if logins[a].get("logged_in") is not False]
        with cf.ThreadPoolExecutor(max_workers=len(usable) or 1) as ex:
            quotas = dict(zip(usable, ex.map(self.quota_cached, usable)))
        ranked = []
        for i, a in enumerate(usable):
            q = quotas[a]
            used = self.relevant_used(q, model) if q.get("ok") else None
            ranked.append((used is None, used if used is not None else 0, i, a, used))
        ranked.sort()
        return [(a, used) for *_, a, used in ranked], logins


# ----------------------------------------------------------------- CLI spec
def opt(*flags, path=None, **kw):
    return {"flags": flags, "kw": kw, "path": path}


def spec():
    run_like = [
        opt("-a", "--account", default="auto", help="account name/number, or auto (most quota left)"),
        opt("-m", "--model", help="explicit model (overrides --difficulty)"),
        opt("-e", "--effort", help="explicit reasoning effort"),
        opt("-f", "--prompt-file", help="read prompt from file ('-' = stdin)", path="prompt"),
        opt("--cwd", help="working directory inside the container"),
        opt("--json", action="store_true", help="print full JSON result"),
        opt("--prompt-stdin", action="store_true", help=argparse.SUPPRESS),
    ]
    return {
        "check": [opt("--json", action="store_true")],
        "quota": [opt("--json", action="store_true")],
        "models": [opt("-a", "--account", default=None), opt("--refresh", action="store_true"),
                   opt("--json", action="store_true")],
        "run": run_like + [
            opt("-d", "--difficulty", type=int, choices=range(1, 7), default=2, help="1 (trivial) .. 6 (hardest)"),
            opt("-i", "--image", action="append", default=[], help="image file to attach (repeatable)", path="in"),
            opt("--timeout", type=int, default=600, help="seconds"),
        ],
        "image": run_like + [
            opt("-o", "--out", required=True, help="output image path", path="out"),
            opt("--timeout", type=int, default=420, help="seconds"),
        ],
        "stats": [opt("--all", action="store_true", help="all vendors, not only this one"),
                  opt("--since", type=float, help="only the last N hours"),
                  opt("--account"), opt("--json", action="store_true")],
    }


HELP = {
    "check": "real test call on every account -> ready / not_logged_in / logged_in_unusable",
    "quota": "percent used per account (live), with the time of the data",
    "models": "models available now + difficulty -> model table",
    "run": "run one non-interactive task (answer on stdout, meta on stderr)",
    "image": "generate an image file",
    "stats": "summarise the central usage log",
}


def build_parser(v):
    p = argparse.ArgumentParser(prog=f"{v.key}.py", description=f"{v.label} accounts {v.prefix}N in container {CONTAINER}")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, opts in spec().items():
        sp = sub.add_parser(name, help=HELP[name], description=HELP[name])
        for o in opts:
            sp.add_argument(*o["flags"], **o["kw"])
        if name in ("run", "image"):
            sp.add_argument("prompt", nargs="*", help="prompt text (or use -f / stdin)")
    return p


def dest_of(o):
    return o["kw"].get("dest") or o["flags"][-1].lstrip("-").replace("-", "_")


def read_prompt(ns):
    if ns.prompt_stdin or ns.prompt_file == "-":
        text = sys.stdin.buffer.read().decode("utf-8", "replace")
    elif ns.prompt_file:
        with open(ns.prompt_file, encoding="utf-8") as f:
            text = f.read()
    elif ns.prompt:
        text = " ".join(ns.prompt)
    elif not sys.stdin.isatty():
        text = sys.stdin.buffer.read().decode("utf-8", "replace")
    else:
        text = ""
    if not text.strip():
        raise SystemExit("empty prompt: give it as arguments, with -f FILE, or on stdin")
    return text


# ----------------------------------------------------------------- host -> container proxy
def proxy(v, ns):
    docker = shutil.which("docker")
    if not docker:
        eprint(f"no {v.prefix}N wrappers here and no docker CLI: run this inside container {CONTAINER}")
        return EXIT_USAGE
    def d(*args, **kw):
        return subprocess.run([docker, *args], capture_output=True, **kw)
    tag = uuid.uuid4().hex[:8]
    mk = d("exec", CONTAINER, "mkdir", "-p", f"{WORK}/bin", f"{WORK}/in", f"{WORK}/out", f"{WORK}/work")
    if mk.returncode:
        eprint(f"cannot reach container {CONTAINER}: {mk.stderr.decode(errors='replace').strip()}")
        return EXIT_USAGE
    remote_script = f"{WORK}/bin/{v.key}.py"
    cp = d("cp", os.path.abspath(__file__), f"{CONTAINER}:{remote_script}")
    if cp.returncode:
        eprint("docker cp failed:", cp.stderr.decode(errors="replace").strip())
        return EXIT_USAGE

    cmd = ns.cmd
    argv, stdin_bytes, out_map, cleanup = [cmd], None, {}, []
    if cmd in ("run", "image"):
        stdin_bytes = read_prompt(ns).encode("utf-8")
    for o in spec()[cmd]:
        dest, flag = dest_of(o), o["flags"][-1]
        val = getattr(ns, dest, None)
        if dest in ("prompt_file", "prompt_stdin"):
            continue
        if o["path"] == "in":
            for local in val or []:
                if not os.path.isfile(local):
                    eprint(f"image not found: {local}")
                    return EXIT_USAGE
                remote = f"{WORK}/in/{tag}-{os.path.basename(local)}"
                r = d("cp", os.path.abspath(local), f"{CONTAINER}:{remote}")
                if r.returncode:
                    eprint("docker cp failed:", r.stderr.decode(errors="replace").strip())
                    return EXIT_USAGE
                argv.append(f"{flag}={remote}")
                cleanup.append(remote)
            continue
        if o["path"] == "out" and val:
            remote = f"{WORK}/out/{tag}-{os.path.basename(val)}"
            out_map[remote] = os.path.abspath(val)
            argv.append(f"{flag}={remote}")
            continue
        action = o["kw"].get("action")
        if action == "store_true":
            if val:
                argv.append(flag)
        elif val is not None and val != o["kw"].get("default"):
            argv.append(f"{flag}={val}")
    if stdin_bytes is not None:
        argv.append("--prompt-stdin")
    fwd = []
    for k in ("AI_SKILL_ACCOUNTS", "AI_SKILL_AUDIT"):
        if os.environ.get(k) is not None:
            fwd += ["-e", f"{k}={os.environ[k]}"]
    exec_cmd = ["exec"] + (["-i"] if stdin_bytes is not None else []) + fwd + [
        "-e", "PYTHONIOENCODING=utf-8", "-e", "AI_SKILL_VIA_HOST=1", "-w", f"{WORK}/work",
        CONTAINER, "python3", remote_script] + argv
    r = subprocess.run([docker] + exec_cmd, input=stdin_bytes, capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace")
    if r.returncode == 0:
        for remote, local in out_map.items():
            os.makedirs(os.path.dirname(local) or ".", exist_ok=True)
            c = d("cp", f"{CONTAINER}:{remote}", local)
            if c.returncode:
                eprint("could not copy result back:", c.stderr.decode(errors="replace").strip())
                r = subprocess.CompletedProcess(r.args, EXIT_FAIL)
            cleanup.append(remote)
    for remote, local in out_map.items():
        out = out.replace(remote, local)
        err = err.replace(remote, local)
        out = out.replace(json.dumps(remote)[1:-1], json.dumps(local)[1:-1])
    if cleanup:
        d("exec", CONTAINER, "rm", "-f", *cleanup)
    sys.stdout.write(out)
    sys.stderr.write(err)
    return r.returncode


# ----------------------------------------------------------------- commands
def cmd_check(v, ns):
    accts = v.accounts()
    cm, ce = v.CHECK_MODEL

    def one(a):
        t0 = time.time()
        login = v.probe_login(a)
        row = {"account": a, "plan": login.get("plan"), "id": login.get("ident")}
        if login.get("logged_in") is False:
            row.update(status="not_logged_in", detail=login.get("detail") or "not logged in")
        else:
            r = v.execute(a, cm, ce, "Reply with just: OK", cwd=WORK + "/work" if os.path.isdir(WORK + "/work") else "/tmp",
                          timeout=90, kind="check")
            if r.get("ok") and "OK" in (r.get("answer") or "").upper():
                row.update(status="ready", detail=f"test call ok ({r.get('model_used') or cm})")
            elif r.get("error_kind") == "not_logged_in":
                row.update(status="not_logged_in", detail=scrub(r.get("error"), 120))
            else:
                probe = f" | login probe: {scrub(login.get('detail'), 60)}" if login.get("logged_in") is None else ""
                row.update(status="logged_in_unusable",
                           detail=f"{r.get('error_kind')}: {scrub(r.get('error'), 110)}{probe}")
        row["secs"] = round(time.time() - t0, 1)
        return row

    os.makedirs(WORK + "/work", exist_ok=True)
    with cf.ThreadPoolExecutor(max_workers=len(accts) or 1) as ex:
        rows = list(ex.map(one, accts))
    seen = {}
    for r in rows:
        if r.get("id"):
            if r["id"] in seen:
                r["detail"] += f" (same login as {seen[r['id']]})"
            else:
                seen[r["id"]] = r["account"]
    if ns.json:
        print(json.dumps({"vendor": v.key, "checked_at": iso(), "accounts": rows}, ensure_ascii=False, indent=1))
    else:
        print(f"{v.label} readiness (real call per account) at {iso()}")
        print(table(rows, ["account", "status", "plan", "id", "secs", "detail"]))
        nl = [r["account"] for r in rows if r["status"] == "not_logged_in"]
        if nl:
            print(f"\nnot logged in: {', '.join(nl)} -> the owner must log in interactively, e.g. "
                  f"`docker exec -it {CONTAINER} {nl[0]}` {v.login_hint}")
    return EXIT_OK if any(r["status"] == "ready" for r in rows) else EXIT_NO_ACCOUNT


def cmd_quota(v, ns):
    accts = v.accounts()

    def one(a):
        login = v.probe_login(a)
        if login.get("logged_in") is False:
            return a, {"ok": False, "as_of": iso(), "note": "no data: not logged in", "windows": []}
        q = v.quota(a)
        return a, q

    with cf.ThreadPoolExecutor(max_workers=len(accts) or 1) as ex:
        res = dict(ex.map(one, accts))
    write_cache(f"{v.key}-quota.json", {a: q for a, q in res.items() if q.get("ok")})
    sigs = {}
    for a, q in res.items():
        if q.get("ok") and q.get("windows"):
            sig = json.dumps([(w["name"], w["used_pct"], w.get("resets_at")) for w in q["windows"]])
            if sig in sigs:
                q["note"] = (q.get("note") + "; " if q.get("note") else "") + f"identical numbers to {sigs[sig]} (probably the same account)"
            else:
                sigs[sig] = a
    if ns.json:
        print(json.dumps({"vendor": v.key, "accounts": res}, ensure_ascii=False, indent=1))
        return EXIT_OK
    rows = []
    for a in accts:
        q = res[a]
        if not q.get("ok") or not q.get("windows"):
            rows.append({"account": a, "window": "-", "used": "no data", "resets": None,
                         "data_time": q.get("as_of"), "note": q.get("note") or "no data"})
            continue
        for i, w in enumerate(q["windows"]):
            rows.append({"account": a if i == 0 else "", "window": w["name"],
                         "used": f"{w['used_pct']:g}%", "resets": w.get("resets_at"),
                         "data_time": q.get("as_of") if i == 0 else "",
                         "note": (q.get("note") or q.get("source")) if i == 0 else ""})
    print(f"{v.label} quota (percent USED; 'no data' = not available, never guessed)")
    print(table(rows, ["account", "window", "used", "resets", "data_time", "note"]))
    return EXIT_OK


def cmd_models(v, ns):
    acct = v.norm_account(ns.account) if ns.account else None
    data = v.models_cached(None if acct == "auto" else acct, refresh=ns.refresh or bool(acct))
    avail = {m["id"] for m in data["models"]} if data else None
    rows = []
    for d in range(1, 7):
        m, e = v.resolve(d, None, None, avail)
        rows.append({"difficulty": d, "model": m, "effort": e or "(in name)",
                     "available": "?" if avail is None else ("yes" if m in avail else "NO"),
                     "preferred": v.DIFF[d][0][0]})
    if ns.json:
        print(json.dumps({"vendor": v.key, "source": data and {k: data[k] for k in ("account", "as_of")},
                          "models": data and data["models"], "difficulty": rows}, ensure_ascii=False, indent=1))
        return EXIT_OK
    if data:
        print(f"{v.label} models available (from {data['account']} at {data['as_of']}):")
        print(table(data["models"], ["id", "name", "efforts"]))
    else:
        print(f"{v.label}: could not list models (no logged-in account answered).")
    print("\ndifficulty -> model (used by `run -d N`):")
    print(table(rows, ["difficulty", "model", "effort", "available", "preferred"]))
    return EXIT_OK


def meta_line(r):
    t = r.get("tokens") or {}
    tok = f"in {t.get('in', '-')} out {t.get('out', '-')}" + (f" cached {t['cached']}" if t.get("cached") else "")
    state = "ok" if r.get("ok") else f"FAILED {r.get('error_kind')}"
    return (f"[{r.get('account')} · {r.get('model_used') or r.get('model')}"
            f"{'/' + r['effort'] if r.get('effort') else ''} · {r.get('secs')}s · tokens {tok} · {state}]")


def _prepare_images(v, ns):
    imgs = []
    for p in getattr(ns, "image", None) or []:
        ap = os.path.abspath(p)
        if not os.path.isfile(ap):
            raise SystemExit(f"image not found: {p}")
        if not image_kind(ap):
            raise SystemExit(f"not a PNG/JPEG/GIF/WEBP image: {p}")
        imgs.append(ap)
    if imgs and not v.can_read_images:
        raise SystemExit(f"{v.label} cannot read images")
    return imgs


def _accounts_for(v, ns, model):
    acct = v.norm_account(ns.account)
    if acct != "auto":
        if v.probe_login(acct).get("logged_in") is False:   # fail fast (no 30 s retries / 60 s OAuth wait)
            eprint(f"{acct} is not logged in. Only the owner can fix this: `docker exec -it {CONTAINER} {acct}` "
                   f"{v.login_hint}. Do not log in for them; use another account or `-a auto`.")
            return [], True
        return [acct], True
    ranked, logins = v.rank_accounts(model)
    if not ranked:
        eprint(f"no logged-in {v.label} account. run `{v.key}.py check`.")
        return [], False
    desc = ", ".join(f"{a} {'?' if u is None else f'{u:g}%'}" for a, u in ranked)
    eprint(f"[auto] candidates by quota used for {model}: {desc}")
    return [a for a, _ in ranked], False


def cmd_run(v, ns):
    prompt = read_prompt(ns)
    imgs = _prepare_images(v, ns)
    avail = None
    if not ns.model:
        data = v.models_cached(None if v.norm_account(ns.account) == "auto" else v.norm_account(ns.account))
        avail = {m["id"] for m in data["models"]} if data else None
    model, effort = v.resolve(ns.difficulty, ns.model, ns.effort, avail)
    accts, explicit = _accounts_for(v, ns, model)
    if not accts:
        return EXIT_NO_ACCOUNT
    cwd = ns.cwd or os.getcwd()
    r = None
    for a in accts:
        r = v.execute(a, model, effort, prompt, imgs, cwd=cwd, timeout=ns.timeout,
                      kind="image-read" if imgs else "run", difficulty=None if ns.model else ns.difficulty)
        if not _may_try_next(r, explicit):
            break
        eprint(f"[auto] {a} failed ({r.get('error_kind')}, no tokens spent); trying next account")
    return _emit(r, ns)


def _may_try_next(r, explicit):
    """Auto mode moves on only for account problems that cost nothing; never repeat paid work."""
    t = r.get("tokens") or {}
    spent = (t.get("in") or 0) + (t.get("out") or 0)
    return not r.get("ok") and not explicit and r.get("error_kind") in RETRYABLE and spent == 0


def _emit(r, ns):
    if ns.json:
        out = {k: r.get(k) for k in ("ok", "account", "model", "model_used", "effort", "answer", "file", "tokens",
                                     "secs", "error_kind", "error", "exit_code")}
        out["error"] = scrub(out.get("error"), 600) if out.get("error") else None
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        if r.get("ok"):
            print(r.get("file") or (r.get("answer") or "").strip())
        else:
            eprint(f"ERROR ({r.get('error_kind')}): {scrub(r.get('error'), 600)}")
        eprint(meta_line(r))
    return EXIT_OK if r.get("ok") else EXIT_FAIL


def cmd_image(v, ns):
    if not v.can_generate_images:
        eprint(f"{v.label} cannot generate images. Use the cyolo skill (Codex CLI) for image generation.")
        return EXIT_USAGE
    prompt = read_prompt(ns)
    out = os.path.abspath(ns.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    model = ns.model or v.IMAGE_MODEL[0]
    effort = ns.effort if ns.model else (ns.effort or v.IMAGE_MODEL[1])
    accts, explicit = _accounts_for(v, ns, model)
    if not accts:
        return EXIT_NO_ACCOUNT
    cwd = ns.cwd or os.getcwd()
    r = None
    for a in accts:
        if os.path.exists(out):
            os.remove(out)
        r = v.image_gen(a, model, effort, prompt, out, cwd, ns.timeout)
        r.update(account=a, model=model, effort=effort)
        if r.get("ok"):
            kind = image_kind(out)
            if not kind:
                r.update(ok=False, error_kind="no_image", error=f"no valid image file at {out}")
            else:
                r["file"] = out
        v.log(r, "image-gen", None)
        if not _may_try_next(r, explicit):
            break
        eprint(f"[auto] {a} failed ({r.get('error_kind')}, no tokens spent); trying next account")
    return _emit(r, ns)


def cmd_stats(v, ns):
    recs = []
    try:
        with open(LOG_PATH, encoding="utf-8") as f:
            for rec in json_lines(f.read()):
                recs.append(rec)
    except OSError:
        pass
    cutoff = now() - dt.timedelta(hours=ns.since) if ns.since else None
    sel = []
    for r in recs:
        if not ns.all and r.get("vendor") != v.key:
            continue
        if ns.account and r.get("account") != v.norm_account(ns.account):
            continue
        if cutoff:
            try:
                if dt.datetime.fromisoformat(r["ts"]) < cutoff:
                    continue
            except (KeyError, ValueError):
                continue
        sel.append(r)
    groups = {}
    for r in sel:
        k = (r.get("vendor"), r.get("account"), r.get("model"))
        g = groups.setdefault(k, {"vendor": k[0], "account": k[1], "model": k[2], "calls": 0, "ok": 0, "fail": 0,
                                  "tokens_in": 0, "tokens_out": 0, "secs": 0.0, "last": "", "fail_kinds": {}})
        g["calls"] += 1
        g["ok" if r.get("ok") else "fail"] += 1
        if not r.get("ok"):
            fk = r.get("error_kind") or "?"
            g["fail_kinds"][fk] = g["fail_kinds"].get(fk, 0) + 1
        g["tokens_in"] += r.get("tokens_in") or 0
        g["tokens_out"] += r.get("tokens_out") or 0
        g["secs"] += r.get("secs") or 0
        g["last"] = max(g["last"], r.get("ts") or "")
    rows = []
    for g in sorted(groups.values(), key=lambda g: (g["vendor"] or "", g["account"] or "", g["model"] or "")):
        g["avg_s"] = round(g["secs"] / g["calls"], 1) if g["calls"] else 0
        g["fail_kinds"] = ", ".join(f"{k}x{n}" for k, n in g["fail_kinds"].items()) or ""
        g.pop("secs")
        rows.append(g)
    if ns.json:
        print(json.dumps({"log": LOG_PATH, "records": len(sel), "groups": rows}, ensure_ascii=False, indent=1))
        return EXIT_OK
    scope = "all vendors" if ns.all else v.key
    print(f"usage log {LOG_PATH} — {len(sel)} calls ({scope}{', last %gh' % ns.since if ns.since else ''})")
    print(table(rows, ["vendor", "account", "model", "calls", "ok", "fail", "tokens_in", "tokens_out", "avg_s",
                       "last", "fail_kinds"]))
    if rows:
        tot = {"calls": sum(r["calls"] for r in rows), "ok": sum(r["ok"] for r in rows),
               "tokens_in": sum(r["tokens_in"] for r in rows), "tokens_out": sum(r["tokens_out"] for r in rows)}
        print(f"\ntotal: {tot['calls']} calls, {tot['ok']} ok, {tot['calls'] - tot['ok']} failed, "
              f"tokens in {tot['tokens_in']} out {tot['tokens_out']}")
    return EXIT_OK


def main(v):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ns = build_parser(v).parse_args()
    if not v.all_accounts():          # no wrappers on PATH -> we are on the host: go through docker
        return proxy(v, ns)
    if not v.accounts():
        eprint(f"AI_SKILL_ACCOUNTS allows no {v.prefix}N account here; nothing was called.")
        return EXIT_NO_ACCOUNT
    return {"check": cmd_check, "quota": cmd_quota, "models": cmd_models, "run": cmd_run,
            "image": cmd_image, "stats": cmd_stats}[ns.cmd](v, ns)

# ===================================================================== Antigravity CLI adapter
class Antigravity(Vendor):
    key = prefix = "gyolo"
    label = "Antigravity CLI"
    can_generate_images = True        # via image-generator subagent; result is verified, see image_gen
    can_read_images = True
    # model names already contain the thinking level -> effort None
    DIFF = {
        1: [("gemini-3.8-flash-low", None)],
        2: [("gemini-3.8-flash-medium", None)],
        3: [("gemini-3.8-flash-high", None)],
        4: [("gemini-4-carbon-medium", None), ("gemini-4-neon-medium", None)],
        5: [("gemini-4-neon-high", None), ("gemini-4-carbon-high", None)],
        6: [("gemini-4-neon-xhigh", None), ("gemini-4-hydrogen-xhigh", None), ("gemini-4-neon-high", None)],
    }
    CHECK_MODEL = ("gemini-3.8-flash-low", None)
    IMAGE_MODEL = ("gemini-4-carbon-low", None)   # flash-low sometimes "cannot find" generate_image
    login_hint = "and complete the Google sign-in"
    FAKE_RE = re.compile(r"(?i)python|\bPIL\b|zlib|struct\.pack|magick|\bconvert\b|base64|printf|>\s*\S+\.(png|jpe?g|webp|gif)")

    def __init__(self):
        self._models = {}

    def probe_login(self, a):
        # `models` fails fast when logged out; a real -p call would instead hang 60 s in an OAuth prompt.
        p = sh([a, "models"], timeout=45, cwd="/tmp")
        text = p["out"] + p["err"]
        if "sign in" in text.lower():
            return {"logged_in": False, "detail": "not logged in"}
        if p["rc"] != 0 or p["timed_out"]:
            return {"logged_in": None, "detail": scrub(text[-200:], 120)}
        ms = []
        for line in p["out"].splitlines():
            parts = line.split("\t")
            if len(parts) == 2 and parts[0].strip():
                eff = re.search(r"\((Low|Medium|High|XHigh|Max)\)\s*$", parts[1], re.I)
                ms.append({"id": parts[0].strip(), "name": parts[1].strip(), "efforts": eff.group(1) if eff else "-"})
        self._models[a] = ms
        return {"logged_in": True, "plan": None, "ident": None, "detail": f"{len(ms)} models"}

    def list_models(self, a):
        if a not in self._models:
            self.probe_login(a)
        return self._models.get(a) or None

    def quota(self, a):
        p = sh([a, "-p", "/usage", "--print-timeout", "40s"], timeout=60, cwd="/tmp")   # free: no model call
        as_of = iso()
        ws = []
        for line in p["out"].splitlines():
            parts = [x.strip() for x in line.split("\t")]
            if len(parts) != 4:
                continue
            group, label, val, reset = parts
            m = re.match(r"([\d.]+)%", val)
            if not m:
                continue
            pct = float(m.group(1))
            used = round(100 - pct, 1) if "remaining" in label.lower() else pct
            g = "gemini" if "gemini" in group.lower() else "claude+gpt"
            w = "7d" if "week" in label.lower() else ("5h" if "five hour" in label.lower() else label)
            ws.append({"name": f"{g} {w}", "used_pct": used, "resets_at": reset})
        if not ws:
            return {"ok": False, "as_of": as_of, "windows": [],
                    "note": "no data: " + (scrub((p["out"] + p["err"])[-200:], 100) or "empty /usage")}
        return {"ok": True, "as_of": as_of, "source": "live /usage (shown as remaining, converted to used)", "windows": ws}

    def relevant_used(self, q, model):
        grp = "gemini" if (model or "").startswith("gemini") else "claude+gpt"
        vals = [w["used_pct"] for w in q.get("windows", []) if w["name"].startswith(grp)]
        return max(vals) if vals else None

    def build_run(self, a, model, effort, prompt, images, cwd, timeout, ctx):
        if images:
            prompt = ("Image file(s) to examine (absolute paths) - open each one with your file viewing tool:\n"
                      + "\n".join(images) + "\n\n" + prompt)
        cmd = [a, "-p", prompt, "--model", model, "--output-format", "stream-json",
               "--print-timeout", f"{int(timeout)}s", "--disable-slash-commands"]
        if effort:
            cmd += ["--effort", effort]
        for d in sorted({os.path.dirname(i) for i in images}):
            cmd += ["--add-dir", d]
        return cmd, None      # stdin = /dev/null so a lost login can never wait for a pasted OAuth code

    def parse_run(self, proc, ctx):
        result = init = None
        steps = []
        for ev in json_lines(proc["out"]):
            e = ev.get("event")
            if e == "init":
                init = ev.get("init") or {}
            elif e == "result":
                result = ev.get("result") or {}
            elif e == "step_update":
                su = ev.get("step_update") or {}
                if su.get("state") == "DONE" and su.get("tool_name"):
                    steps.append({"tool": su["tool_name"], "params": (su.get("tool_info") or {}).get("parameters")})
        ctx["steps"] = steps
        if result is None:
            return {"ok": False, "error": proc["err"][-300:] or f"exit {proc['rc']} without result"}
        u = result.get("usage") or {}
        cached = u.get("cache_read_tokens") or 0
        tin, tout = (u.get("input_tokens") or 0) + cached, u.get("output_tokens") or 0
        ok = proc["rc"] == 0 and result.get("status") == "SUCCESS"
        return {"ok": ok, "answer": result.get("response") if ok else None,
                "error": None if ok else (result.get("error") or result.get("finished_reason") or "status " + str(result.get("status"))),
                "model_used": (init or {}).get("model"), "conversation_id": result.get("conversation_id"),
                "tokens": {"in": tin, "out": tout, "cached": cached, "reasoning": u.get("thinking_tokens"),
                           "total": tin + tout}}

    def image_gen(self, a, model, effort, prompt, out, cwd, timeout):
        t0 = time.time() - 2
        ask = ("Invoke the image-generator subagent and have it call the generate_image tool (the real image model) "
               f"to create this image:\n{prompt}\n\nRules: drawing or writing image files with code, python, "
               "ImageMagick or shell is forbidden. After generate_image succeeds, copy the generated image file to "
               f"{out} with one cp command. If generate_image fails, reply exactly GENERATE_IMAGE_FAILED followed "
               "by the error.")
        ctx = {}
        r = self.call(a, model, effort, ask, [], cwd, timeout, ctx)
        if not r.get("ok"):
            return r
        answer = r.get("answer") or ""
        # agy says SUCCESS even when the image model failed, or when it faked the picture with code.
        if "GENERATE_IMAGE_FAILED" in answer:
            r.update(ok=False, error_kind=classify(answer) if classify(answer) != "cli_error" else "tool_failed",
                     error=answer.strip())
            return r
        faked = [s for s in ctx.get("steps", []) if s["tool"] == "run_command"
                 and self.FAKE_RE.search(json.dumps(s.get("params")))]
        if faked:
            if os.path.exists(out):
                os.remove(out)
            r.update(ok=False, error_kind="fake_image",
                     error="agent drew the picture with code instead of the image model; result rejected")
            return r
        if not os.path.exists(out):
            home = f"{BASE}/.Gemini/{a}/.gemini"
            new = [p for p in glob.glob(f"{home}/**/*", recursive=True)
                   if os.path.isfile(p) and os.path.getmtime(p) >= t0 and image_kind(p)]
            if new:
                shutil.copyfile(max(new, key=os.path.getmtime), out)
        if not image_kind(out):
            r.update(ok=False, error_kind="no_image", error="no image file was produced. Answer: " + scrub(answer, 200))
            return r
        r["file"] = out
        return r


if __name__ == "__main__":
    sys.exit(main(Antigravity()))
