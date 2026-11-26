"""Run inside container: python3 /workspace/bench/run_bench.py [vendor ...]"""
import json, subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor

S = "/root/ai-accounts/.Claude/shared/skills"
B = "/workspace/bench"
T = f"{B}/tasks"
IMG = f"{T}/t4_sign.png"

VENDORS = {
    "claude": dict(script=f"{S}/yolo/scripts/yolo.py", acct="yolo1",
                   models=["haiku", "sonnet", "opus", "fable"]),
    "codex": dict(script=f"{S}/cyolo/scripts/cyolo.py", acct="cyolo1",
                  models=["gpt-6.2-sol", "gpt-6.2-astra", "gpt-6.1-terra", "gpt-6.1-sol", "gpt-6-astra",
                          "gpt-6-sol", "gpt-6-luna", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"]),
    "gemini": dict(script=f"{S}/gyolo/scripts/gyolo.py", acct="gyolo1",
                   models=["gemini-3.8-flash-medium", "gemini-4-hydrogen-medium", "gemini-4-argon-medium",
                           "gemini-4-carbon-medium", "gemini-4-neon-medium"]),
}
TASKS = ["t1_math", "t2_bugfix", "t3_needle", "t4_sign"]


def job(vendor, model, task):
    v = VENDORS[vendor]
    rid = f"bench-{vendor}-{model}-{task}"
    out = f"{B}/out/{vendor}__{model}__{task}.json"
    if os.path.exists(out):
        try:
            if json.load(open(out)).get("ok"):
                return rid, "cached"
        except Exception:
            pass
    cwd = f"{B}/runs/{vendor}__{model}__{task}"
    os.makedirs(cwd, exist_ok=True)
    prompt = open(f"{T}/{task}.txt", encoding="utf-8").read()
    cmd = ["python3", v["script"], "run", "-", "-a", v["acct"], "-m", model,
           "--cwd", cwd, "--timeout", "900", "--run-id", rid, "--node", "bench", "--json"]
    if vendor != "gemini":
        cmd += ["-e", "medium"]
    if task == "t4_sign":
        if vendor == "claude":
            prompt = prompt.replace("{IMG}", IMG)          # Claude Code reads the image with its Read tool
        else:
            prompt = prompt.replace("{IMG}", "ที่แนบมา")
            cmd += ["--image", IMG]
    p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=1000)
    try:
        data = json.loads(p.stdout)
    except Exception:
        data = {"ok": False, "status": "parse_error", "stdout": p.stdout[-2000:], "stderr": p.stderr[-2000:]}
    json.dump(data, open(out, "w"), ensure_ascii=False, indent=1)
    return rid, data.get("status")


def run_vendor(vendor):
    jobs = [(vendor, m, t) for m in VENDORS[vendor]["models"] for t in TASKS]
    with ThreadPoolExecutor(2) as ex:
        for rid, st in ex.map(lambda a: job(*a), jobs):
            print(rid, st, flush=True)


if __name__ == "__main__":
    os.makedirs(f"{B}/out", exist_ok=True)
    vs = sys.argv[1:] or list(VENDORS)
    with ThreadPoolExecutor(len(vs)) as ex:
        list(ex.map(run_vendor, vs))
