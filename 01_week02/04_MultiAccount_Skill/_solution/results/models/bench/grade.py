"""Grade every answer and build charts + results.json. Usage: python grade.py <out_dir>"""
import json, re, subprocess, sys, tempfile
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
OUT = Path(sys.argv[1])
MODELS_DIR = HERE.parent
TESTS = (HERE / "tasks" / "tests_t2.py").read_text(encoding="utf-8")
ORDER = {
    "claude": ["haiku", "sonnet", "opus", "fable"],
    "codex": ["gpt-6.2-sol", "gpt-6.2-astra", "gpt-6.1-terra", "gpt-6.1-sol", "gpt-6-astra",
              "gpt-6-sol", "gpt-6-luna", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"],
    "gemini": ["gemini-3.8-flash-medium", "gemini-4-hydrogen-medium", "gemini-4-argon-medium",
               "gemini-4-carbon-medium", "gemini-4-neon-medium"],
}
TASKS = ["t1_math", "t2_bugfix", "t3_needle", "t4_sign"]
VENDOR_LABEL = {"claude": "Anthropic (yolo1)", "codex": "OpenAI (cyolo1)", "gemini": "Google (gyolo1)"}
COLOR = {"claude": "#d97757", "codex": "#10a37f", "gemini": "#4285f4"}


def answer_line(text):
    m = re.findall(r"ANSWER\s*[:：]\s*`?([^\n`]*)", text or "")
    return m[-1].strip() if m else ""


def grade(task, text):
    a = answer_line(text)
    if task == "t1_math":
        s = re.sub(r"[,\s฿]|บาท|\*", "", a)
        try:
            return abs(float(s) - 490428.75) < 1e-6, a
        except ValueError:
            return False, a
    if task == "t3_needle":
        return ("VX-7318-KAPPA" in a.upper() and "SIGMA" not in a.upper()), a
    if task == "t4_sign":
        return re.sub(r"\D", "", a) == "73915", a
    # t2: run the model's function against the tests
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text or "", re.S)
    blocks = [b for b in blocks if "def second_largest" in b]
    if not blocks:
        return False, "(no code block)"
    code = blocks[-1] + "\n" + TESTS + "\nprint('PASS')\n"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
    try:
        p = subprocess.run([sys.executable, "-I", f.name], capture_output=True, text=True, timeout=20)
        ok = p.returncode == 0 and "PASS" in p.stdout
        return ok, "tests PASS" if ok else ("tests FAIL: " + (p.stderr.strip().splitlines() or ["?"])[-1])
    except subprocess.TimeoutExpired:
        return False, "tests TIMEOUT"


rows = []
for vendor, models in ORDER.items():
    for model in models:
        per = []
        for t in TASKS:
            f = OUT / f"{vendor}__{model}__{t}.json"
            d = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"ok": False, "status": "missing"}
            ok, got = grade(t, d.get("result", "")) if d.get("ok") else (False, f"ERROR {d.get('status')}: {str(d.get('error'))[:120]}")
            per.append(dict(task=t, correct=ok, got=got, status=d.get("status"),
                            duration_s=d.get("duration_s"), output_tokens=d.get("output_tokens"),
                            reasoning_tokens=d.get("reasoning_tokens"), real_model=d.get("real_model"),
                            raw=(d.get("result") or "")[-600:]))
        done = [p for p in per if p["duration_s"] is not None and p["status"] == "ok"]
        rows.append(dict(
            vendor=vendor, model=model,
            real_model=next((p["real_model"] for p in per if p["real_model"]), model),
            correct=sum(p["correct"] for p in per),
            avg_time=round(sum(p["duration_s"] for p in done) / len(done), 2) if done else None,
            avg_out=round(sum(p["output_tokens"] or 0 for p in done) / len(done), 1) if done else None,
            n_ok=len(done), tasks=per))

(HERE / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

for r in rows:
    marks = " ".join(("✔" if p["correct"] else "✘") + f"{p['task'][:2]}[{p['got'][:40]}]({p['duration_s']}s,{p['output_tokens']})" for p in r["tasks"])
    print(f"{r['vendor']:6} {r['model']:26} {r['correct']}/4 avg={r['avg_time']} out={r['avg_out']} | {marks}")

# charts
labels = [r["model"].replace("-medium", "") for r in rows]
colors = [COLOR[r["vendor"]] for r in rows]
handles = [plt.Rectangle((0, 0), 1, 1, color=COLOR[v]) for v in ORDER]

def bar(values, title, ylabel, fname, fmt):
    fig, ax = plt.subplots(figsize=(14, 6))
    vals = [v if v is not None else 0 for v in values]
    bars = ax.bar(range(len(vals)), vals, color=colors)
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), "n/a" if v is None else fmt(v),
                ha="center", va="bottom", fontsize=9)
    ax.set_xticks(range(len(vals)), labels, rotation=40, ha="right")
    ax.set_ylim(0, max(vals) * 1.3)
    ax.set_title(title); ax.set_ylabel(ylabel)
    ax.legend(handles, [VENDOR_LABEL[v] for v in ORDER], loc="upper left")
    ax.grid(axis="y", alpha=.3)
    fig.tight_layout(); fig.savefig(MODELS_DIR / fname, dpi=130); plt.close(fig)

bar([r["avg_time"] for r in rows], "Average time per task (s) - 4 tasks, medium effort", "seconds",
    "avg_time.png", lambda v: f"{v:.1f}")
bar([r["correct"] for r in rows], "Correct answers (out of 4)", "correct", "correct.png", lambda v: f"{v}")
print("charts saved")
