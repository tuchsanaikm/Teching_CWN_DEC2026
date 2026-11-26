"""Run inside container: python3 /workspace/bench_hard/run_bench.py [vendor ...]"""
import json, subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor

S = "/root/ai-accounts/.Claude/shared/skills"
B = "/workspace/bench_hard"
T = f"{B}/tasks"
EFFORTS = ["low", "high"]
VENDORS = {
    "claude": dict(script=f"{S}/yolo/scripts/yolo.py", acct="yolo1", models=["haiku", "sonnet", "opus", "fable"]),
    "codex": dict(script=f"{S}/cyolo/scripts/cyolo.py", acct="cyolo1",
                  models=["gpt-6.2-sol", "gpt-6.2-astra", "gpt-6.1-terra"]),
    "gemini": dict(script=f"{S}/gyolo/scripts/gyolo.py", acct="gyolo1",
                   models=["gemini-3.8-flash", "gemini-4-hydrogen", "gemini-4-argon", "gemini-4-carbon", "gemini-4-neon"]),
}
TASKS = ["h1_math", "h2_logic", "h3_bug", "h4_algo", "h5_doc"]


def job(vendor, model, effort, task):
    v = VENDORS[vendor]
    tag = f"{vendor}__{model}__{effort}__{task}"
    out = f"{B}/out/{tag}.json"
    if os.path.exists(out):
        try:
            if json.load(open(out)).get("ok"):
                return tag, "cached"
        except Exception:
            pass
    cwd = f"{B}/runs/{tag}"
    os.makedirs(cwd, exist_ok=True)
    prompt = open(f"{T}/{task}.txt", encoding="utf-8").read()
    cmd = ["python3", v["script"], "run", "-", "-a", v["acct"], "--cwd", cwd, "--timeout", "1200",
           "--run-id", f"hard-{tag}", "--node", "bench_hard", "--json"]
    cmd += ["-m", f"{model}-{effort}"] if vendor == "gemini" else ["-m", model, "-e", effort]
    try:
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=1300)
        data = json.loads(p.stdout)
    except Exception as e:
        data = {"ok": False, "status": "runner_error", "error": repr(e)[:500]}
    json.dump(data, open(out, "w"), ensure_ascii=False, indent=1)
    return tag, f"{data.get('status')} {data.get('duration_s')}s"


def run_vendor(vendor):
    jobs = [(vendor, m, e, t) for m in VENDORS[vendor]["models"] for e in EFFORTS for t in TASKS]
    with ThreadPoolExecutor(3) as ex:
        for tag, st in ex.map(lambda a: job(*a), jobs):
            print(tag, st, flush=True)


if __name__ == "__main__":
    os.makedirs(f"{B}/out", exist_ok=True)
    vs = sys.argv[1:] or list(VENDORS)
    with ThreadPoolExecutor(len(vs)) as ex:
        list(ex.map(run_vendor, vs))
