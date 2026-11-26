#!/usr/bin/env python3
"""ma_common: shared helpers for the yolo / cyolo / gyolo / agent-team skills.

An identical copy lives in each skill's scripts/ folder so every skill works on
its own after a plain folder copy. Standard library only, Python 3.8+.

Never reads or forwards credential files (.credentials.json, .claude.json,
auth.json, Antigravity token files). Never stores prompt text in the ledger.
"""
import datetime as _dt
import fcntl
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time


def _find_base():
    """Folder that holds .Claude / .Codex / .Gemini. An agent CLI may run this script with HOME set to
    its own account folder (gyoloN does), so `~/ai-accounts` alone is not enough: look at where this
    file is installed first (<BASE>/.<Side>/shared/skills/<skill>/scripts)."""
    if os.environ.get("MA_BASE"):
        return os.environ["MA_BASE"]
    p = os.path.dirname(os.path.realpath(__file__))
    for _ in range(12):
        if os.path.basename(p) in (".Claude", ".Codex", ".Gemini"):
            return os.path.dirname(p)
        q = os.path.dirname(p)
        if q == p:
            break
        p = q
    for cand in (os.path.expanduser("~/ai-accounts"), "/root/ai-accounts"):
        if os.path.isdir(cand):
            return cand
    return os.path.expanduser("~/ai-accounts")


BASE = _find_base()
CLAUDE_ROOT = os.path.join(BASE, ".Claude")
CODEX_ROOT = os.path.join(BASE, ".Codex")
GEMINI_ROOT = os.path.join(BASE, ".Gemini")
TEAM_ROOT = os.environ.get("MA_TEAM_DIR", "/workspace/.agent-team")
GLOBAL_LEDGER = os.path.join(TEAM_ROOT, "ledger.jsonl")
CACHE_DIR = os.path.join(TEAM_ROOT, ".cache")

CLAUDE_MODELS = ["opus", "sonnet", "haiku", "fable"]
CLAUDE_EFFORTS = ["low", "medium", "high", "xhigh", "max"]
CODEX_EFFORT_ORDER = ["minimal", "low", "medium", "high", "xhigh", "max", "ultra"]

# difficulty -> (claude model, claude effort, codex effort)   (3-tuple kept for old callers)
DIFFICULTY = {
    1: ("haiku", "low", "low"),
    2: ("sonnet", "medium", "medium"),
    3: ("opus", "high", "high"),
    4: ("opus", "xhigh", "xhigh"),
    5: ("opus", "max", "max"),
    6: ("fable", "high", "ultra"),
}
# Codex model preference per difficulty (first slug listed in models_cache.json wins,
# otherwise the cache's default model). Image *viewing* prefers CODEX_VISION_PREF.
CODEX_MODEL_PREF = {1: ["gpt-6.2-sol"], 2: ["gpt-6.2-sol"], 3: ["gpt-6.2-sol"],
                    4: ["gpt-6.2-astra"], 5: ["gpt-6.2-astra"], 6: ["gpt-6.2-astra"]}
CODEX_VISION_PREF = ["gpt-6.1-terra"]
# Antigravity (gyoloN): model id per difficulty; the effort is part of the id.
# Fallback when an id is not in `gyoloN models`: same family, nearest lower effort, then
# the first family of GEMINI_FALLBACK that is listed.
GEMINI_DIFFICULTY = {
    1: "gemini-3.8-flash-low",
    2: "gemini-3.8-flash-medium",
    3: "gemini-4-hydrogen-medium",
    4: "gemini-4-hydrogen-high",
    5: "gemini-4-argon-high",
    6: "gemini-4-carbon-high",
}
GEMINI_EFFORTS = ["low", "medium", "high", "xhigh", "max"]
GEMINI_FALLBACK = ["gemini-4-hydrogen", "gemini-3.8-flash", "gemini-4-neon", "gemini-4-argon", "gemini-4-carbon"]

LEDGER_FIELDS = ["ts_start", "ts_end", "run_id", "node", "account", "cli", "model",
                 "effort", "duration_s", "input_tokens", "cached_input_tokens",
                 "cache_write_tokens", "output_tokens", "reasoning_tokens", "cost_usd",
                 "status", "error", "prompt_chars", "result_chars"]

_ledger_lock = threading.Lock()


# ----------------------------------------------------------------- basics
def now_iso():
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def fmt_ts(epoch):
    if not epoch:
        return "-"
    return _dt.datetime.fromtimestamp(float(epoch)).astimezone().strftime("%Y-%m-%d %H:%M")


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def cli_of(account):
    if re.fullmatch(r"yolo\d+", account or ""):
        return "claude"
    if re.fullmatch(r"cyolo\d+", account or ""):
        return "codex"
    if re.fullmatch(r"gyolo\d+", account or ""):
        return "gemini"
    return None


SIDES = ("yolo", "cyolo", "gyolo")


def side_of(account):
    c = cli_of(account)
    return {"claude": "yolo", "codex": "cyolo", "gemini": "gyolo"}.get(c)


def _num_key(name):
    m = re.search(r"(\d+)$", name)
    return int(m.group(1)) if m else 0


def list_accounts(side=None):
    """Accounts that have both an account folder and a wrapper command."""
    out = []
    for s, root in (("yolo", CLAUDE_ROOT), ("cyolo", CODEX_ROOT), ("gyolo", GEMINI_ROOT)):
        if side and side != s:
            continue
        names = []
        for d in glob.glob(os.path.join(root, s + "[0-9]*")):
            n = os.path.basename(d)
            if re.fullmatch(s + r"\d+", n) and os.path.isdir(d) and shutil.which(n):
                names.append(n)
        out += sorted(names, key=_num_key)
    return out


def table(headers, rows):
    """Plain markdown table (renders in a terminal and in Claude Code)."""
    rows = [["" if c is None else str(c) for c in r] for r in rows]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in r) + " |")
    return "\n".join(lines)


def short(text, n=160):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= n else text[: n - 1] + "…"


# ------------------------------------------------------------ simulation
def _env_list(name):
    return [x.strip() for x in os.environ.get(name, "").split(",") if x.strip()]


def simulated_limit(account):
    return account in _env_list("MA_SIMULATE_LIMIT")


# ----------------------------------------------------------------- ledger
def ledger_append(row, run_dir=None):
    """Append one row to the global ledger (and the run ledger when given)."""
    full = {k: row.get(k) for k in LEDGER_FIELDS}
    for k, v in row.items():
        if k not in full and k not in ("prompt", "result"):
            full[k] = v
    line = json.dumps(full, ensure_ascii=False) + "\n"
    targets = [GLOBAL_LEDGER]
    if run_dir:
        targets.append(os.path.join(run_dir, "ledger.jsonl"))
    with _ledger_lock:
        for path in targets:
            ensure_dir(os.path.dirname(path))
            with open(path, "a", encoding="utf-8") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.write(line)
                fcntl.flock(f, fcntl.LOCK_UN)


def read_ledger(path=None):
    path = path or GLOBAL_LEDGER
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    return rows


def row_tokens(r):
    """Tokens counted against budgets: everything except cache reads.

    Claude reports input_tokens without cache; Codex input_tokens already
    includes cached_input_tokens, so cached tokens are subtracted for Codex.
    """
    i = r.get("input_tokens") or 0
    if r.get("cli") == "codex":     # gemini (agy) input_tokens already excludes cache reads, like Claude
        i -= r.get("cached_input_tokens") or 0
    return max(i, 0) + (r.get("cache_write_tokens") or 0) + (r.get("output_tokens") or 0)


def stats_tables(rows, by=("account", "model", "run_id")):
    rows = [r for r in rows if r.get("event") is None]
    out = []
    names = {"account": "บัญชี", "model": "รุ่น", "run_id": "run"}
    for key in by:
        groups = {}
        for r in rows:
            k = r.get(key) or "-"
            if key == "model" and r.get("effort"):
                k = "%s/%s" % (k, r.get("effort"))
            groups.setdefault(k, []).append(r)
        body = []
        tot = dict(n=0, ok=0, fail=0, inp=0, cin=0, cw=0, out=0, rs=0, cost=0.0, dur=0.0)
        for k in sorted(groups):
            g = groups[k]
            n = len(g)
            ok = sum(1 for r in g if r.get("status") == "ok")
            vals = dict(
                inp=sum(r.get("input_tokens") or 0 for r in g),
                cin=sum(r.get("cached_input_tokens") or 0 for r in g),
                cw=sum(r.get("cache_write_tokens") or 0 for r in g),
                out=sum(r.get("output_tokens") or 0 for r in g),
                rs=sum(r.get("reasoning_tokens") or 0 for r in g),
                cost=sum(r.get("cost_usd") or 0 for r in g),
                dur=sum(r.get("duration_s") or 0 for r in g))
            body.append([k, n, ok, n - ok, vals["inp"], vals["cin"], vals["cw"], vals["out"],
                         vals["rs"], "%.4f" % vals["cost"], "%.1f" % vals["dur"],
                         "%.1f" % (vals["dur"] / n if n else 0)])
            tot["n"] += n
            tot["ok"] += ok
            tot["fail"] += n - ok
            for x in ("inp", "cin", "cw", "out", "rs", "cost", "dur"):
                tot[x] += vals[x]
        body.append(["**รวม**", tot["n"], tot["ok"], tot["fail"], tot["inp"], tot["cin"], tot["cw"],
                     tot["out"], tot["rs"], "%.4f" % tot["cost"], "%.1f" % tot["dur"],
                     "%.1f" % (tot["dur"] / tot["n"] if tot["n"] else 0)])
        out.append("### ตาม%s\n" % names.get(key, key) + table(
            [names.get(key, key), "ครั้ง", "สำเร็จ", "ล้ม", "input", "cached_in", "cache_write",
             "output", "reasoning", "cost_usd(ราคาตามรายการ)", "เวลารวม s", "เฉลี่ย s"], body))
    return "\n\n".join(out)


# ------------------------------------------------------------ error kinds
_LIMIT_RE = re.compile(r"usage limit|rate.?limit|limit reached|quota|too many requests|429|"
                       r"hit your limit|out of extra usage|exceeded|RESOURCE_EXHAUSTED|QUOTA_EXHAUSTED|"
                       r"exhausted your", re.I)
_EXPIRED_RE = re.compile(r"OAuth session expired|could not be refreshed|token.*expired|"
                         r"Failed to authenticate|invalid.*(token|credential)|refresh_token", re.I)
_NOLOGIN_RE = re.compile(r"Not logged in|Please run /login|401 Unauthorized|Missing bearer|"
                         r"login required|codex login|Please sign in|Authentication required|"
                         r"authentication failed or timed out", re.I)


def classify_error(text):
    t = text or ""
    if t.startswith("simulated"):
        return "limit"
    if _EXPIRED_RE.search(t):
        return "auth_expired"
    if _NOLOGIN_RE.search(t):
        return "not_logged_in"
    if _LIMIT_RE.search(t):
        return "limit"
    if "timeout" in t.lower():
        return "timeout"
    return "error"


SWITCHABLE = ("limit", "auth_expired", "not_logged_in")


# ------------------------------------------------------------ quota cache
def _quota_cache_path():
    return os.path.join(CACHE_DIR, "quota.json")


def quota_cache_load():
    try:
        with open(_quota_cache_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def quota_cache_put(account, info):
    ensure_dir(CACHE_DIR)
    path = _quota_cache_path()
    with open(path + ".lock", "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        data = quota_cache_load()
        data[account] = info
        tmp = path + ".tmp%d" % os.getpid()
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        fcntl.flock(lk, fcntl.LOCK_UN)


# ------------------------------------------------------------ Claude side
def _claude_rate_info(ev):
    info = ev.get("rate_limit_info") or {}
    w = info.get("unifiedWindows") or {}
    q = {"source": "stream rate_limit_event", "as_of": now_iso(), "status": info.get("status")}
    if "five_hour" in w:
        q["session_pct"] = round(100 * float(w["five_hour"].get("utilization") or 0))
        q["session_resets"] = fmt_ts(w["five_hour"].get("resetsAt"))
    if "seven_day" in w:
        q["week_pct"] = round(100 * float(w["seven_day"].get("utilization") or 0))
        q["week_resets"] = fmt_ts(w["seven_day"].get("resetsAt"))
    return q


def call_claude(account, prompt, model="sonnet", effort="medium", cwd=None, timeout=900,
                json_schema=None, extra_args=None, run_dir=None, run_id=None, node=None,
                on_event=None, proc_holder=None, ledger=True, simulate_limit=False, env=None, no_sim=False):
    """Run `yoloN -p` once (non-interactive) and return a result dict.

    Uses stream-json so tokens and rate-limit info are visible while running.
    exit code 0 does not mean success: is_error/result are checked.
    """
    t0 = time.time()
    ts_start = now_iso()
    res = dict(ok=False, account=account, cli="claude", model=model, effort=effort, result="",
               error="", status="error", real_model=None, usage={}, cost_usd=None,
               structured_output=None, session_id=None)
    if (simulated_limit(account) and not no_sim) or simulate_limit:
        time.sleep(0.05)
        res.update(error="simulated: usage limit reached (MA_SIMULATE_LIMIT)", status="limit")
    else:
        cmd = [account, "-p", prompt, "--model", model, "--effort", effort,
               "--output-format", "stream-json", "--verbose", "--no-session-persistence",
               "--strict-mcp-config"]
        if json_schema:
            cmd += ["--json-schema", json_schema if isinstance(json_schema, str) else json.dumps(json_schema)]
        if extra_args:
            cmd += list(extra_args)
        final = None
        live = {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0}
        try:
            p = subprocess.Popen(cmd, cwd=cwd or None, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                                 start_new_session=True)
            if proc_holder is not None:
                proc_holder.append(p)
            fired = []
            timer = threading.Timer(timeout, lambda: (fired.append(1), _kill(p)))
            timer.start()
            err_chunks = []
            et = threading.Thread(target=lambda: err_chunks.append(p.stderr.read()), daemon=True)
            et.start()
            for line in p.stdout:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                typ = ev.get("type")
                if typ == "assistant":
                    u = (ev.get("message") or {}).get("usage") or {}
                    live["input"] += u.get("input_tokens") or 0
                    live["cache_write"] += u.get("cache_creation_input_tokens") or 0
                    live["cache_read"] += u.get("cache_read_input_tokens") or 0
                    live["output"] += u.get("output_tokens") or 0
                    if on_event:
                        on_event("tokens", dict(live))
                elif typ == "rate_limit_event":
                    q = _claude_rate_info(ev)
                    q["account"] = account
                    quota_cache_put(account, q)
                    if on_event:
                        on_event("rate", q)
                elif typ == "result":
                    final = ev
            p.wait()
            timer.cancel()
            et.join(2)
            timed_out = bool(fired)
            if final is None:
                # killed / crashed: keep the tokens already reported by the stream
                res["usage"] = {"input_tokens": live["input"], "cache_creation_input_tokens": live["cache_write"],
                                "cache_read_input_tokens": live["cache_read"], "output_tokens": live["output"]}
                stderr = "".join(err_chunks)
                res["error"] = "timeout after %ss" % timeout if timed_out else \
                    short(stderr or "no result (exit %s)" % p.returncode, 300)
                res["status"] = classify_error(res["error"])
            else:
                res["result"] = final.get("result") or ""
                res["session_id"] = final.get("session_id")
                res["cost_usd"] = final.get("total_cost_usd")
                res["usage"] = final.get("usage") or {}
                mu = final.get("modelUsage") or {}
                res["real_model"] = ",".join(mu.keys()) or None
                res["structured_output"] = final.get("structured_output")
                if final.get("is_error") or final.get("subtype") not in (None, "success"):
                    res["error"] = short(res["result"] or final.get("subtype") or "is_error", 300)
                    res["status"] = classify_error(res["error"])
                else:
                    res["ok"] = True
                    res["status"] = "ok"
        except FileNotFoundError:
            res["error"] = "ไม่พบคำสั่ง %s" % account
    u = res["usage"] or {}
    res.update(ts_start=ts_start, ts_end=now_iso(), duration_s=round(time.time() - t0, 2),
               input_tokens=u.get("input_tokens") or 0,
               cached_input_tokens=u.get("cache_read_input_tokens") or 0,
               cache_write_tokens=u.get("cache_creation_input_tokens") or 0,
               output_tokens=u.get("output_tokens") or 0,
               reasoning_tokens=(u.get("output_tokens_details") or {}).get("thinking_tokens") or 0)
    if ledger:
        ledger_append(_ledger_row(res, prompt, run_id, node), run_dir)
    return res


def _kill(p):
    try:
        os.killpg(p.pid, 15)
    except OSError:
        return

    def hard():   # SIGKILL if the process group ignores SIGTERM
        if p.poll() is None:
            try:
                os.killpg(p.pid, 9)
            except OSError:
                pass
    t = threading.Timer(5, hard)
    t.daemon = True
    t.start()


def _ledger_row(res, prompt, run_id, node):
    return dict(ts_start=res["ts_start"], ts_end=res["ts_end"], run_id=run_id, node=node,
                account=res["account"], cli=res["cli"], model=res["model"], effort=res["effort"],
                duration_s=res["duration_s"], input_tokens=res["input_tokens"],
                cached_input_tokens=res["cached_input_tokens"],
                cache_write_tokens=res["cache_write_tokens"], output_tokens=res["output_tokens"],
                reasoning_tokens=res["reasoning_tokens"],
                cost_usd=res.get("cost_usd") if res["cli"] == "claude" else None,
                status=res["status"], error=short(res["error"], 200) if res["error"] else None,
                prompt_chars=len(prompt or ""), result_chars=len(res.get("result") or ""),
                real_model=res.get("real_model"))


_USAGE_RE = re.compile(r"Current (session|week \(([^)]*)\)):\s*(\d+)% used(?:\s*·\s*resets\s*(.+))?")


def claude_quota(account, timeout=60):
    """Built-in `/usage` (no model call). Returns parsed lines or no-data."""
    q = {"account": account, "as_of": now_iso(), "source": "/usage"}
    try:
        p = subprocess.run([account, "-p", "/usage"], stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=timeout, encoding="utf-8", errors="replace", cwd="/tmp")
        txt = p.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        q["note"] = "อ่านไม่ได้: %s" % short(e, 80)
        return q
    found = False
    for m in _USAGE_RE.finditer(txt):
        found = True
        if m.group(1) == "session":
            q["session_pct"] = int(m.group(3))
            q["session_resets"] = (m.group(4) or "").strip()
        elif m.group(2) == "all models":
            q["week_pct"] = int(m.group(3))
            q["week_resets"] = (m.group(4) or "").strip()
        else:
            q.setdefault("week_other", {})[m.group(2)] = int(m.group(3))
    if not found:
        q["note"] = "ไม่มีข้อมูลโควตา" + (" (ไม่ได้ล็อกอินด้วย subscription)" if "Total cost" in txt else
                                         ": " + short(txt, 60))
    elif "session_pct" not in q:
        q["note"] = "/usage ไม่มีบรรทัด Current session (ยังไม่มี session ที่เปิดอยู่)"
    quota_cache_put(account, q)
    return q


def claude_check(account, timeout=120):
    """Real minimal call. Returns ready / expired / not_logged_in / limit / error."""
    try:
        st = subprocess.run([account, "auth", "status"], capture_output=True, text=True, timeout=30,
                            stdin=subprocess.DEVNULL, cwd="/tmp")
        logged = '"loggedIn": true' in st.stdout
        if '"loggedIn"' not in st.stdout and st.returncode != 0:
            # the CLI itself does not start (e.g. a half-finished update): not a login problem
            return dict(account=account, status="error", as_of=now_iso(),
                        detail="คำสั่ง %s ทำงานไม่ได้: %s" % (account, short((st.stderr or st.stdout).strip(), 100)))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logged = None
    if logged is False:
        return dict(account=account, status="not_logged_in", detail="auth status: loggedIn false",
                    as_of=now_iso())
    r = call_claude(account, "ตอบ OK", "haiku", "low", cwd="/tmp", timeout=timeout, node="check", no_sim=True)
    if r["ok"]:
        return dict(account=account, status="ready", detail="ตอบ %s ใน %.1fs" % (short(r["result"], 20),
                                                                              r["duration_s"]),
                    as_of=now_iso())
    kind = r["status"]
    status = {"auth_expired": "expired", "not_logged_in": "not_logged_in", "limit": "limit"}.get(kind, "error")
    if status == "not_logged_in" and logged:
        status = "expired"
    return dict(account=account, status=status, detail=short(r["error"], 120), as_of=now_iso())


# ------------------------------------------------------------- Codex side
def codex_home(account):
    return os.path.join(CODEX_ROOT, account)


def codex_models(account=None):
    accs = [account] if account else list_accounts("cyolo")
    if account:   # same list on every account: fall back to another account's cache
        accs += [a for a in list_accounts("cyolo") if a != account]
    for a in accs:
        path = os.path.join(codex_home(a), "models_cache.json")
        data = None
        for _ in range(3):   # codex may be rewriting the file right now (seen under parallel runs)
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                break
            except OSError:
                break
            except ValueError:
                time.sleep(0.2)
        if not data:
            continue
        models = []
        for m in data.get("models", []):
            models.append(dict(slug=m.get("slug"), visibility=m.get("visibility"),
                               priority=m.get("priority", 999),
                               default=m.get("default_reasoning_level"),
                               efforts=[x.get("effort") for x in m.get("supported_reasoning_levels") or []]))
        models.sort(key=lambda m: m["priority"])
        return models, data.get("fetched_at")
    return [], None


def codex_default_model(account=None):
    models, _ = codex_models(account)
    for m in models:
        if m["visibility"] == "list":
            return m["slug"]
    return models[0]["slug"] if models else None


def codex_model_for(difficulty=2, account=None, vision=False):
    """Slug for a difficulty from CODEX_MODEL_PREF (vision -> CODEX_VISION_PREF first),
    only when models_cache.json lists it; otherwise the cache's default model."""
    models, _ = codex_models(account)
    listed = {m["slug"] for m in models}
    d = max(1, min(6, int(difficulty or 2)))
    for slug in (CODEX_VISION_PREF if vision else []) + CODEX_MODEL_PREF.get(d, []):
        if slug in listed:
            return slug
    return codex_default_model(account)


def codex_resolve(model, effort, account=None):
    """Return (model, effort, note). Lowers unsupported effort to the highest supported one."""
    models, _ = codex_models(account)
    model = model or codex_default_model(account)
    info = next((m for m in models if m["slug"] == model), None)
    if not info:
        return model, effort, "ไม่พบรุ่น %s ใน models_cache.json (ส่งไปตามที่ระบุ)" % model
    if effort in info["efforts"]:
        return model, effort, ""
    want = CODEX_EFFORT_ORDER.index(effort) if effort in CODEX_EFFORT_ORDER else 99
    ok = [e for e in info["efforts"] if e in CODEX_EFFORT_ORDER and CODEX_EFFORT_ORDER.index(e) <= want]
    new = ok[-1] if ok else (info["default"] or info["efforts"][0])
    return model, new, "ลด effort จาก %s เป็น %s (%s ไม่รองรับ)" % (effort, new, model)


def call_codex(account, prompt, model=None, effort="medium", cwd=None, timeout=900, ephemeral=True,
               images=None, output_schema=None, run_dir=None, run_id=None, node=None, on_event=None,
               proc_holder=None, ledger=True, simulate_limit=False, env=None, no_sim=False):
    t0 = time.time()
    ts_start = now_iso()
    model, effort, note = codex_resolve(model, effort, account)
    res = dict(ok=False, account=account, cli="codex", model=model, effort=effort, result="", error="",
               status="error", note=note, usage={}, real_model=model, thread_id=None, cost_usd=None)
    if (simulated_limit(account) and not no_sim) or simulate_limit:
        time.sleep(0.05)
        res.update(error="simulated: usage limit reached (MA_SIMULATE_LIMIT)", status="limit")
    else:
        fd, out_file = tempfile.mkstemp(prefix="cyolo-", suffix=".txt")
        os.close(fd)
        cmd = [account, "exec", "--skip-git-repo-check"] + (["-m", model] if model else []) + \
              ["-c", "model_reasoning_effort=%s" % effort, "--json", "-o", out_file]
        if ephemeral:
            cmd.append("--ephemeral")
        if cwd:
            cmd += ["-C", cwd]
        for im in images or []:
            cmd += ["-i", im]
        if output_schema:
            cmd += ["--output-schema", output_schema]
        cmd += ["--", prompt]
        errors = []
        failed = []
        usage = None
        try:
            p = subprocess.Popen(cmd, cwd=cwd or "/tmp", env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                                 start_new_session=True)
            if proc_holder is not None:
                proc_holder.append(p)
            fired_l = []
            timer = threading.Timer(timeout, lambda: (fired_l.append(1), _kill(p)))
            timer.start()
            for line in p.stdout:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                typ = ev.get("type")
                if typ == "thread.started":
                    res["thread_id"] = ev.get("thread_id")
                elif typ == "turn.completed":
                    usage = ev.get("usage") or {}
                    if on_event:
                        on_event("tokens", usage)
                elif typ == "turn.failed":
                    failed.append(1)
                    errors.append((ev.get("error") or {}).get("message") or "turn.failed")
                elif typ == "error":
                    errors.append(ev.get("message") or "error")
            p.wait()
            fired = bool(fired_l)
            timer.cancel()
            try:
                with open(out_file, encoding="utf-8", errors="replace") as f:
                    res["result"] = f.read().strip()
            except OSError:
                pass
            if usage is not None and not failed:
                res["ok"] = True
                res["status"] = "ok"
            else:
                if fired and usage is None:
                    res["error"] = "timeout after %ss" % timeout
                else:
                    res["error"] = short(errors[-1] if errors else "no turn.completed (exit %s)" % p.returncode, 300)
                res["status"] = classify_error(res["error"])
            res["usage"] = usage or {}
        except FileNotFoundError:
            res["error"] = "ไม่พบคำสั่ง %s" % account
        finally:
            try:
                os.unlink(out_file)
            except OSError:
                pass
    u = res["usage"] or {}
    res.update(ts_start=ts_start, ts_end=now_iso(), duration_s=round(time.time() - t0, 2),
               input_tokens=u.get("input_tokens") or 0, cached_input_tokens=u.get("cached_input_tokens") or 0,
               cache_write_tokens=u.get("cache_write_input_tokens") or 0,
               output_tokens=u.get("output_tokens") or 0, reasoning_tokens=u.get("reasoning_output_tokens") or 0)
    if ledger:
        ledger_append(_ledger_row(res, prompt, run_id, node), run_dir)
    return res


def codex_login_status(account):
    try:
        p = subprocess.run([account, "login", "status"], capture_output=True, text=True, timeout=30,
                           stdin=subprocess.DEVNULL, cwd="/tmp")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return None, short(e, 80)
    txt = (p.stdout + "\n" + p.stderr).strip()
    if "Logged in" in txt:
        return True, short(txt.splitlines()[-1], 60)
    if "Not logged in" in txt:
        return False, "Not logged in"
    return None, short(txt, 80)


def codex_check(account, timeout=180):
    logged, detail = codex_login_status(account)
    if logged is False:
        return dict(account=account, status="not_logged_in", detail=detail, as_of=now_iso())
    r = call_codex(account, "ตอบคำว่า OK เท่านั้น", None, "low", timeout=timeout, node="check", no_sim=True)
    if r["ok"] and r["result"]:
        return dict(account=account, status="ready", detail="ตอบ %s ใน %.1fs" % (short(r["result"], 20),
                                                                              r["duration_s"]),
                    as_of=now_iso())
    kind = r["status"]
    status = {"auth_expired": "expired", "not_logged_in": "expired", "limit": "limit"}.get(kind, "error")
    return dict(account=account, status=status, detail=short(r["error"], 120), as_of=now_iso())


def codex_quota(account):
    """rate_limits from the newest non-ephemeral rollout. Always reports data time."""
    q = {"account": account, "source": "sessions rollout"}
    files = glob.glob(os.path.join(codex_home(account), "sessions", "*", "*", "*", "*.jsonl"))
    files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    for f in files[:30]:
        last = None
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if '"token_count"' not in line or '"rate_limits"' not in line:
                        continue
                    try:
                        ev = json.loads(line)
                    except ValueError:
                        continue
                    rl = (ev.get("payload") or {}).get("rate_limits")
                    if rl and (rl.get("primary") or rl.get("secondary")):
                        last = (ev.get("timestamp"), rl)
        except OSError:
            continue
        if last:
            ts, rl = last
            try:
                as_of = _dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().isoformat(
                    timespec="seconds")
            except (ValueError, AttributeError):
                as_of = ts
            q["as_of"] = as_of
            for name in ("primary", "secondary"):
                w = rl.get(name)
                if w:
                    q[name] = dict(used_percent=w.get("used_percent"), window_minutes=w.get("window_minutes"),
                                   resets=fmt_ts(w.get("resets_at")))
            # map to the common fields: shortest window = "session", longest = "week"
            wins = [rl[n] for n in ("primary", "secondary") if rl.get(n)]
            wins.sort(key=lambda w: w.get("window_minutes") or 0)
            if wins:
                if (wins[0].get("window_minutes") or 0) < 10080:
                    q["session_pct"] = round(wins[0].get("used_percent") or 0)
                q["week_pct"] = round(wins[-1].get("used_percent") or 0)
            q["plan"] = rl.get("plan_type")
            return q
    q["as_of"] = None
    q["note"] = "ไม่มีข้อมูล (ยังไม่มี rollout ที่ไม่ใช่ ephemeral) ใช้ quota --refresh"
    return q


# ------------------------------------------------- Gemini side (Antigravity agy, gyoloN)
def gemini_home(account):
    return os.path.join(GEMINI_ROOT, account)


def _run_agy(cmd, cwd="/tmp", timeout=60, env=None, proc_holder=None):
    """Run one gyoloN command. agy on an account that is not signed in prints a sign-in URL on
    stderr and waits 60 s; we stop it at once and never keep the URL.
    Returns (returncode, stdout, stderr_without_urls, flags{auth, timeout})."""
    flags = {"auth": False, "timeout": False}
    p = subprocess.Popen(cmd, cwd=cwd or "/tmp", env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                         start_new_session=True)
    if proc_holder is not None:
        proc_holder.append(p)
    timer = threading.Timer(timeout, lambda: (flags.__setitem__("timeout", True), _kill(p)))
    timer.start()
    err = []

    def read_err():
        for line in p.stderr:
            if "Authentication required" in line or "Waiting for authentication" in line:
                if not flags["auth"]:
                    flags["auth"] = True
                    err.append("Authentication required (agy ขอ sign-in = ไม่ได้ล็อกอิน)\n")
                _kill(p)
                continue
            if "authorization code" in line or "accounts.google.com" in line:
                continue          # sign-in prompt: never keep the sign-in URL
            err.append(re.sub(r"https?://\S+", "[url]", line))   # keep AGY_ERROR lines, drop URLs only
    et = threading.Thread(target=read_err, daemon=True)
    et.start()
    out = p.stdout.read()
    p.wait()
    timer.cancel()
    et.join(2)
    return p.returncode, out, "".join(err), flags


def _last_json(text):
    for line in reversed((text or "").strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                continue
    return None


def _agy_error(stderr):
    """The structured `AGY_ERROR: {...}` line agy prints on stderr for failed runs."""
    for line in (stderr or "").splitlines():
        if line.startswith("AGY_ERROR:"):
            try:
                return json.loads(line[len("AGY_ERROR:"):].strip())
            except ValueError:
                return {"short_error": line[10:].strip()}
    return {}


def _gemini_models_cache():
    try:
        with open(os.path.join(CACHE_DIR, "gemini_models.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def gemini_login(account, timeout=60):
    """`gyoloN models`: exit 0 + id<TAB>name lines = signed in (also refreshes the models cache);
    "Please sign in" + exit 1 = not signed in. Returns (True|False|None, detail)."""
    try:
        rc, out, err, fl = _run_agy([account, "models"], timeout=timeout)
    except FileNotFoundError:
        return None, "ไม่พบคำสั่ง %s" % account
    txt = out + "\n" + err
    models = [ln.split("\t", 1) for ln in out.splitlines() if "\t" in ln]
    if rc == 0 and models:
        ensure_dir(CACHE_DIR)
        path = os.path.join(CACHE_DIR, "gemini_models.json")
        with open(path + ".lock", "a") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            data = _gemini_models_cache()
            data[account] = {"as_of": now_iso(), "models": [[m[0].strip(), m[1].strip()] for m in models]}
            tmp = path + ".tmp%d" % os.getpid()
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, path)
            fcntl.flock(lk, fcntl.LOCK_UN)
        return True, "models: %d รุ่น" % len(models)
    if "Please sign in" in txt or fl["auth"]:
        return False, "Not signed in (gyolo models: Please sign in)"
    if fl["timeout"]:
        return None, "models ไม่ตอบใน %ss" % timeout
    return None, short(err or out or "exit %s" % rc, 80)


def gemini_models(account=None, refresh=False, max_age_s=86400):
    """[{id, name}], as_of. Cached in .cache/gemini_models.json (`gyoloN models` takes ~4 s)."""
    accs = [account] if account else list_accounts("gyolo")
    data = _gemini_models_cache()
    if not refresh:
        for a in accs + [x for x in sorted(data) if x not in accs]:   # the list is the same on every account
            e = data.get(a)
            if not e:
                continue
            try:
                age = time.time() - _dt.datetime.fromisoformat(e["as_of"]).timestamp()
            except (ValueError, KeyError):
                continue
            if age <= max_age_s:
                return [dict(id=m[0], name=m[1]) for m in e["models"]], e["as_of"]
    if refresh or account:
        for a in accs:
            ok, _ = gemini_login(a)
            if ok:
                e = _gemini_models_cache().get(a) or {}
                return [dict(id=m[0], name=m[1]) for m in e.get("models", [])], e.get("as_of")
    # stale cache is better than nothing
    for a in accs + [x for x in sorted(data) if x not in accs]:
        e = data.get(a)
        if e:
            return [dict(id=m[0], name=m[1]) for m in e["models"]], e["as_of"]
    return [], None


def gemini_split(model_id):
    """'gemini-4-neon-high' -> ('gemini-4-neon', 'high'); no effort suffix -> (id, None)."""
    m = re.match(r"^(.*)-(%s)$" % "|".join(GEMINI_EFFORTS), model_id or "")
    return (m.group(1), m.group(2)) if m else (model_id, None)


def gemini_resolve(model=None, effort=None, account=None, difficulty=2):
    """Return (model_id, effort, note). `model` may be a full id or a family; `effort` replaces the
    id's effort suffix. Ids not in `gyoloN models` fall back: same family nearest lower effort ->
    nearest higher -> GEMINI_FALLBACK families -> first listed id."""
    d_id = GEMINI_DIFFICULTY[max(1, min(6, int(difficulty or 2)))]
    want = model or d_id
    fam, eff = gemini_split(want)
    if eff is None and not effort and re.match(r"gemini-(4-|3\.8-flash)", fam or ""):
        effort = gemini_split(d_id)[1]       # family given without effort: effort of the difficulty
    if effort:
        eff = "max" if effort == "ultra" else ("low" if effort == "minimal" else effort)
        if eff in GEMINI_EFFORTS:
            want = "%s-%s" % (fam, eff)
    models, _ = gemini_models(account)
    listed = [m["id"] for m in models]
    if not listed or want in listed:
        return want, gemini_split(want)[1] or "-", "" if listed else "ยังไม่มีรายชื่อรุ่น (ส่งไปตามที่ระบุ)"
    order = GEMINI_EFFORTS
    i = order.index(eff) if eff in order else 1
    tries = order[:i + 1][::-1] + order[i + 1:]
    for f in [fam] + [x for x in GEMINI_FALLBACK if x != fam]:
        for e in tries:
            if "%s-%s" % (f, e) in listed:
                new = "%s-%s" % (f, e)
                return new, e, "ไม่พบรุ่น %s ใน gyolo models ใช้ %s แทน" % (want, new)
        if f in listed:
            return f, "-", "ไม่พบรุ่น %s ใน gyolo models ใช้ %s แทน" % (want, f)
    return listed[0], gemini_split(listed[0])[1] or "-", "ไม่พบรุ่น %s ใช้รุ่นแรกที่มี %s" % (want, listed[0])


def call_gemini(account, prompt, model=None, effort=None, cwd=None, timeout=900, images=None, json_schema=None,
                add_dirs=None, run_dir=None, run_id=None, node=None, on_event=None, proc_holder=None, ledger=True,
                simulate_limit=False, env=None, no_sim=False, difficulty=2):
    """Run `gyoloN -p` once (agy print mode, --output-format json) and return a result dict.
    Images: agy has no attach flag; it opens image files given by absolute path in the prompt."""
    t0 = time.time()
    ts_start = now_iso()
    sim = (simulated_limit(account) and not no_sim) or simulate_limit
    model, effort, note = gemini_resolve(model, effort, None if sim else account, difficulty)
    res = dict(ok=False, account=account, cli="gemini", model=model, effort=effort, result="", error="",
               status="error", note=note, usage={}, real_model=model, session_id=None, cost_usd=None)
    if sim:
        time.sleep(0.05)
        res.update(error="simulated: usage limit reached (MA_SIMULATE_LIMIT)", status="limit")
    else:
        dirs = list(add_dirs or [])
        if images:
            ims = ["/" + os.path.normpath(os.path.abspath(x)).lstrip("/") for x in images]
            prompt = "%s\n\nไฟล์ภาพที่ต้องดู (เปิดไฟล์ภาพตาม absolute path นี้): %s" % (prompt, ", ".join(ims))
            dirs += sorted({os.path.dirname(x) for x in ims})
        cmd = [account, "-p", prompt, "--model", model, "--output-format", "json",
               "--print-timeout", "%ds" % int(timeout)]
        for d in dirs:
            cmd += ["--add-dir", d]
        if json_schema:   # agy accepts a schema string or a schema file path
            cmd += ["--json-schema", json_schema if isinstance(json_schema, str) else json.dumps(json_schema)]
        try:
            rc, out, err, fl = _run_agy(cmd, cwd=cwd or "/tmp", timeout=timeout + 30, env=env,
                                        proc_holder=proc_holder)
            final = _last_json(out)
            ae = _agy_error(err)
            if final:
                res["usage"] = final.get("usage") or {}
                res["session_id"] = final.get("conversation_id") or None
                res["result"] = (final.get("response") or "").strip()
            if fl["auth"]:
                res.update(error="ไม่ได้ล็อกอิน (agy ขอ sign-in)", status="not_logged_in")
            elif final and final.get("status") == "SUCCESS" and rc == 0:
                res.update(ok=True, status="ok")
            else:
                e = (final or {}).get("error") or ae.get("short_error") or short(err, 300) or \
                    "no result (exit %s)" % rc
                res["error"] = short(e, 300)
                reason = (final or {}).get("finished_reason") or ae.get("reason") or ""
                code = ae.get("status") or ""
                if reason == "print_timeout" or code == "DEADLINE_EXCEEDED" or fl["timeout"]:
                    res.update(status="timeout", error="timeout after %ss" % timeout)
                elif code in ("RESOURCE_EXHAUSTED",) or "QUOTA" in str(reason).upper():
                    res["status"] = "limit"
                elif code == "UNAUTHENTICATED":
                    res["status"] = "auth_expired"
                else:
                    res["status"] = classify_error(res["error"])
            if on_event:
                on_event("tokens", res["usage"])
        except FileNotFoundError:
            res["error"] = "ไม่พบคำสั่ง %s" % account
    u = res["usage"] or {}
    res.update(ts_start=ts_start, ts_end=now_iso(), duration_s=round(time.time() - t0, 2),
               input_tokens=u.get("input_tokens") or 0, cached_input_tokens=u.get("cache_read_tokens") or 0,
               cache_write_tokens=0, output_tokens=u.get("output_tokens") or 0,
               reasoning_tokens=u.get("thinking_tokens") or 0)
    if ledger:
        ledger_append(_ledger_row(res, prompt, run_id, node), run_dir)
    return res


# Antigravity generates images through its `image-generator` subagent (model gemini-3.1-flash-image).
# Observed 2026-11-24: agy saves the PNG at the path named in the prompt (1024x1024, ~80 s per image).
# The image server can be out of capacity (2026-11-23: HTTP 503 on every try) while the call still ends
# with SUCCESS, so the result is ok only when a PNG written during this call ends up at `out`
# (the target path, a .png path named in the answer, or a new .png under the account folder).
GEMINI_IMAGE_DIFFICULTY = 2
GEMINI_IMAGE_RULES = (
    "\n\nกติกา (สำคัญ): ใช้ความสามารถสร้างภาพของคุณ (subagent image-generator / เครื่องมือ generate_image) เท่านั้น "
    "ห้ามวาดภาพด้วยโค้ด (Python/PIL/SVG/HTML/canvas หรือโปรแกรมอื่น) "
    "บันทึกไฟล์ PNG ที่ %s (absolute path) แล้วตอบเฉพาะ path นั้น "
    "ถ้าสร้างภาพไม่สำเร็จ ห้ามสร้างแทนด้วยวิธีอื่น ให้ตอบบรรทัดเดียวว่า IMAGE_FAILED: <ข้อความผิดพลาดจริงจากเครื่องมือ>")
_IMG_FAIL_RE = re.compile(r"IMAGE_FAILED[^\n]*|[^\n]*(?:No capacity|HTTP 503|UNAVAILABLE|image failed to generate|"
                          r"image generation quota)[^\n]*", re.I)


def _new_pngs(account, t0, text, out):
    """Candidate PNG files written during the call: paths named in the answer, then files under the
    account's HOME (only file names are listed; no other file is opened)."""
    cands = []
    for p in re.findall(r"(/[^\s`'\"()\[\]<>]+\.png)", text or ""):
        if p != out and os.path.isfile(p):
            cands.append(p)
    home = gemini_home(account)
    for root, dirs, files in os.walk(home):
        if root[len(home):].count(os.sep) > 6:
            dirs[:] = []
            continue
        for f in files:
            if f.lower().endswith(".png"):
                cands.append(os.path.join(root, f))
    out_c = []
    for p in cands:
        try:
            if os.path.getmtime(p) >= t0 - 2 and is_png(p) and p not in out_c:
                out_c.append(p)
        except OSError:
            pass
    out_c.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return out_c


def call_gemini_image(account, prompt, out, model=None, cwd=None, timeout=600, run_dir=None, run_id=None,
                      node=None, simulate_limit=False, no_sim=False, env=None, proc_holder=None, refs=None):
    """Ask agy to generate a PNG at `out`. ok only when a PNG written during this call ends up at `out`.
    refs = existing image files to start from (edit / keep the same subject); they are named by absolute
    path in the prompt. Failures of the image tool (e.g. HTTP 503 no capacity) -> status
    `image_unavailable` with the message."""
    out = "/" + os.path.normpath(os.path.abspath(out)).lstrip("/")
    ensure_dir(os.path.dirname(out))
    t0 = time.time()
    dirs = [os.path.dirname(out)]
    if refs:
        rf = ["/" + os.path.normpath(os.path.abspath(x)).lstrip("/") for x in refs]
        prompt += ("\n\nภาพตั้งต้น (เปิดดูไฟล์ตาม absolute path แล้วส่งให้เครื่องมือสร้างภาพใช้เป็นภาพอ้างอิง "
                   "คงสิ่งที่ไม่ได้สั่งให้เปลี่ยนไว้เหมือนเดิม): %s" % ", ".join(rf))
        dirs += sorted({os.path.dirname(x) for x in rf} - set(dirs))
    full = prompt + (GEMINI_IMAGE_RULES % out)
    res = call_gemini(account, full, model, None, cwd=cwd or os.path.dirname(out), timeout=timeout,
                      add_dirs=dirs, run_dir=run_dir, run_id=run_id, node=node, ledger=False,
                      simulate_limit=simulate_limit, no_sim=no_sim, env=env, proc_holder=proc_holder,
                      difficulty=GEMINI_IMAGE_DIFFICULTY)
    res["image"] = out
    fresh = is_png(out) and os.path.getmtime(out) >= t0 - 2
    if res["ok"] and not fresh:
        found = _new_pngs(account, t0, res.get("result"), out)
        if found and not _IMG_FAIL_RE.search(res.get("result") or ""):
            shutil.copyfile(found[0], out)
            res["note"] = ((res.get("note") or "") + " คัดลอกภาพจาก %s" % found[0]).strip()
            fresh = True
    res["png_ok"] = bool(fresh)
    if res["ok"] and not fresh:
        m = _IMG_FAIL_RE.search(res.get("result") or "")
        res.update(ok=False, status="image_unavailable" if m else "bad_output",
                   error=short(m.group(0), 300) if m else "ไม่พบไฟล์ PNG ที่ %s (agy ไม่ได้บันทึกภาพ)" % out)
    elif not res["ok"] and res["status"] in ("error", "bad_output") and _IMG_FAIL_RE.search(res.get("error") or ""):
        res["status"] = "image_unavailable"
    ledger_append(_ledger_row(res, full, run_id, node), run_dir)
    return res


def _iso_local(ts):
    if not ts:
        return "-"
    try:
        return _dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return ts


def gemini_quota(account, timeout=60):
    """agy `/usage` in print mode (no model call). agy reports *remaining* %; converted to used %
    (session = 5-hour window, week = weekly window of the Gemini group)."""
    q = {"account": account, "as_of": now_iso(), "source": "/usage (remaining → used)"}
    try:
        rc, out, err, fl = _run_agy([account, "-p", "/usage", "--output-format", "json"], timeout=timeout)
    except FileNotFoundError:
        q["note"] = "ไม่พบคำสั่ง %s" % account
        return q
    if fl["auth"]:
        q["note"] = "ไม่มีข้อมูลโควตา (ไม่ได้ล็อกอิน)"
        return q
    final = _last_json(out) or {}
    groups = {}
    for g in (((final.get("command") or {}).get("data") or {}).get("groups") or []):
        for b in g.get("buckets") or []:
            w = {"5h": "session", "weekly": "week"}.get(b.get("window"))
            rf = b.get("remaining_fraction")
            if w and rf is not None:
                groups.setdefault(g.get("name") or "?", {})[w] = dict(
                    remaining_pct=round(100 * float(rf)), used_pct=round(100 * (1 - float(rf))),
                    resets=_iso_local(b.get("reset_time")))
    if not groups:  # fallback: TAB lines "group<TAB>bucket<TAB>NN%<TAB>reset"
        for line in (final.get("response") or "").splitlines():
            parts = line.split("\t")
            if len(parts) >= 3 and parts[2].strip().endswith("%"):
                w = "session" if "Five Hour" in parts[1] else ("week" if "Weekly" in parts[1] else None)
                try:
                    rem = round(float(parts[2].strip().rstrip("%")))
                except ValueError:
                    w = None
                if w:
                    groups.setdefault(parts[0], {})[w] = dict(remaining_pct=rem, used_pct=100 - rem,
                                                              resets=_iso_local(parts[3]) if len(parts) > 3 else "")
    if not groups:
        q["note"] = "ไม่มีข้อมูลโควตา: " + short(final.get("error") or err or out, 60)
        return q
    main = next((k for k in groups if k.lower().startswith("gemini")), sorted(groups)[0])
    for w in ("session", "week"):
        if w in groups[main]:
            q["%s_pct" % w] = groups[main][w]["used_pct"]
            q["%s_resets" % w] = groups[main][w]["resets"]
    q["groups"] = groups
    q["week_other"] = {k: v.get("week", {}).get("used_pct") for k, v in groups.items() if k != main}
    quota_cache_put(account, q)
    return q


def gemini_check(account, timeout=180):
    """`gyoloN models` (signed in?) then a real minimal call with the difficulty-1 model."""
    logged, detail = gemini_login(account)
    if logged is False:
        return dict(account=account, status="not_logged_in", detail=detail, as_of=now_iso())
    r = call_gemini(account, "ตอบคำว่า OK เท่านั้น", None, None, cwd="/tmp", timeout=timeout, node="check",
                    no_sim=True, difficulty=1)
    if r["ok"] and r["result"]:
        return dict(account=account, status="ready", detail="ตอบ %s ใน %.1fs" % (short(r["result"], 20),
                                                                              r["duration_s"]),
                    as_of=now_iso())
    if r["status"] == "limit" or (r["status"] == "not_logged_in" and logged is not True):
        status = r["status"]
    elif r["status"] == "timeout" or logged is None:
        status = "error"            # could not tell (CLI missing, `models` or the call timed out)
    else:
        status = "unusable"         # signed in (`models` works) but a real call fails
    return dict(account=account, status=status, detail=short(r["error"], 120), as_of=now_iso())


def quota(account, refresh=False):
    if cli_of(account) == "claude":
        return claude_quota(account)
    if cli_of(account) == "gemini":
        return gemini_quota(account)
    if refresh:
        call_codex(account, "ตอบคำว่า OK เท่านั้น", None, "low", ephemeral=False, node="quota-refresh",
                   timeout=180)
    return codex_quota(account)


def quota_text(q):
    if not q:
        return "ไม่มีข้อมูล"
    parts = []
    if q.get("session_pct") is not None:
        parts.append("session %s%%" % q["session_pct"])
    if q.get("week_pct") is not None:
        parts.append("week %s%%" % q["week_pct"])
    if not parts:
        return "ไม่มีข้อมูล" + (" (%s)" % q["note"] if q.get("note") else "")
    return "%s (ข้อมูล %s)" % (" · ".join(parts), (q.get("as_of") or "-")[:16].replace("T", " "))


def quota_used_pct(q):
    """Highest known usage percent (session or week); None when unknown."""
    if not q:
        return None
    vals = [q.get(k) for k in ("session_pct", "week_pct") if q.get(k) is not None]
    return max(vals) if vals else None


def quota_table(accounts, refresh=False):
    rows, data = [], {}
    for a in accounts:
        q = quota(a, refresh=refresh)
        data[a] = q
        if cli_of(a) == "claude":
            rows.append([a, q.get("session_pct", "-"), q.get("session_resets", "-"), q.get("week_pct", "-"),
                         q.get("week_resets", "-"), (q.get("as_of") or "-")[:19], q.get("note", "")])
        elif cli_of(a) == "gemini":
            other = "; ".join("%s week %s%%" % (k, v) for k, v in (q.get("week_other") or {}).items()
                              if v is not None)
            rows.append([a, q.get("session_pct", "-"), q.get("session_resets", "-"), q.get("week_pct", "-"),
                         q.get("week_resets", "-"), (q.get("as_of") or "-")[:19],
                         q.get("note") or ("Gemini (agy รายงาน % ที่เหลือ แปลงเป็น % ที่ใช้)" +
                                           (" · " + other if other else ""))])
        else:
            pr = q.get("primary") or {}
            sc = q.get("secondary") or {}
            rows.append([a, q.get("session_pct", "-"), "-", q.get("week_pct", pr.get("used_percent", "-")),
                         pr.get("resets", "-") if pr else "-", (q.get("as_of") or "ไม่มีข้อมูล")[:19],
                         q.get("note", "") + ("" if not sc else " secondary %s%%" % sc.get("used_percent"))])
    return table(["บัญชี", "session %", "session reset", "week %", "week reset", "เวลาของข้อมูล", "หมายเหตุ"],
                 rows), data


STATUS_TH = {"ready": "พร้อม", "expired": "ล็อกอินแล้วแต่หมดอายุ", "not_logged_in": "ไม่ได้ล็อกอิน",
             "limit": "โควตาหมด", "error": "ผิดพลาด", "unusable": "ล็อกอินแล้วแต่ใช้ไม่ได้"}


def check_accounts(accounts, parallel=True):
    results = {}

    def one(a):
        c = cli_of(a)
        results[a] = claude_check(a) if c == "claude" else (gemini_check(a) if c == "gemini" else codex_check(a))

    ths = [threading.Thread(target=one, args=(a,)) for a in accounts]
    for t in ths:
        t.start()
        if not parallel:
            t.join()
    for t in ths:
        t.join()
    ensure_dir(CACHE_DIR)
    path = os.path.join(CACHE_DIR, "check.json")
    with open(path + ".lock", "a") as lk:     # parallel runs: lock + atomic replace
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
        except (OSError, ValueError):
            old = {}
        old.update(results)
        tmp = path + ".tmp%d.%d" % (os.getpid(), threading.get_ident())
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(old, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        fcntl.flock(lk, fcntl.LOCK_UN)
    return [results[a] for a in accounts]


def check_table(results):
    return table(["บัญชี", "สถานะ", "รายละเอียด", "ตรวจเมื่อ"],
                 [[r["account"], STATUS_TH.get(r["status"], r["status"]), r["detail"], r["as_of"][:19]]
                  for r in results])


def cached_check(max_age_s=600):
    try:
        with open(os.path.join(CACHE_DIR, "check.json"), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    out = {}
    for a, r in data.items():
        try:
            age = time.time() - _dt.datetime.fromisoformat(r["as_of"]).timestamp()
        except (ValueError, KeyError):
            continue
        if age <= max_age_s:
            out[a] = r
    return out


DIFFICULTY_USE = {1: "ดึงข้อมูล จัดรูปแบบ ตรวจความพร้อม", 2: "สรุป ถาม-ตอบ แก้โค้ดจุดเดียว (ค่าเริ่มต้น)",
                  3: "แก้หลายไฟล์ debug วิเคราะห์", 4: "reasoning ซับซ้อน อัลกอริทึม", 5: "ต้องถูกแน่นอน",
                  6: "งานใหญ่ที่วางแผน/แตกงานเอง"}


def difficulty_table():
    """One table for the three CLIs. Codex/Gemini columns show what is resolved from
    models_cache.json / the cached `gyoloN models` list (no model call)."""
    rows = []
    for d in sorted(DIFFICULTY):
        cm, ce, xe = DIFFICULTY[d]
        cx_model = codex_model_for(d)
        cx_model, cx_eff, _ = codex_resolve(cx_model, xe) if cx_model else (None, xe, "")
        gid, _, gnote = gemini_resolve(None, None, None, d)
        rows.append([d, DIFFICULTY_USE[d], "%s/%s" % (cm, ce), "%s/%s" % (cx_model or "default", cx_eff),
                     gid + (" *" if gnote else "")])
    return table(["d", "งาน", "Claude (yoloN)", "Codex (cyoloN)", "Antigravity (gyoloN)"], rows) + \
        "\n\nd6 Claude = fable (แพงกว่า opus ราว 2 เท่า และมีบรรทัดโควตาสัปดาห์ของตัวเอง `Current week (Fable)`)" + \
        " · Codex/Gemini อ่านจากรายชื่อรุ่นจริง (* = ยังไม่มีรายชื่อหรือใช้รุ่นสำรอง) · ดูภาพ: Codex ใช้ " + \
        "/".join(CODEX_VISION_PREF) + " ถ้ามี"


def is_png(path):
    try:
        with open(path, "rb") as f:
            return f.read(8) == b"\x89PNG\r\n\x1a\n"
    except OSError:
        return False


def print_result(res, as_json=False):
    if as_json:
        keep = {k: v for k, v in res.items() if k not in ("usage",)}
        print(json.dumps(keep, ensure_ascii=False, indent=1))
    else:
        if res["ok"]:
            print(res["result"])
        else:
            print("ล้ม (%s): %s" % (res["status"], res["error"]), file=sys.stderr)
        print("\n" + table(["บัญชี", "รุ่น/effort", "เวลา s", "input", "cached_in", "cache_write", "output",
                            "reasoning", "cost_usd", "สถานะ"],
                           [[res["account"], "%s/%s" % (res["model"], res["effort"]), res["duration_s"],
                             res["input_tokens"], res["cached_input_tokens"], res["cache_write_tokens"],
                             res["output_tokens"], res["reasoning_tokens"],
                             "-" if res.get("cost_usd") is None else "%.4f" % res["cost_usd"],
                             res["status"]]]), file=sys.stderr)
        if res.get("note"):
            print("หมายเหตุ: " + res["note"], file=sys.stderr)
