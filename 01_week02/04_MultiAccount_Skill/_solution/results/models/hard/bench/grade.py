"""Grade hard benchmark. Usage: python grade.py <out_dir>"""
import json, re, subprocess, sys, tempfile
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
OUT = Path(sys.argv[1])
HARD = HERE.parent
KEY = json.loads((HERE / "key.json").read_text(encoding="utf-8"))
ORDER = {
    "claude": ["haiku", "sonnet", "opus", "fable"],
    "codex": ["gpt-6.2-sol", "gpt-6.2-astra", "gpt-6.1-terra"],
    "gemini": ["gemini-3.8-flash", "gemini-4-hydrogen", "gemini-4-argon", "gemini-4-carbon", "gemini-4-neon"],
}
EFFORTS = ["low", "high"]
TASKS = ["h1_math", "h2_logic", "h3_bug", "h4_algo", "h5_doc"]
VENDOR_LABEL = {"claude": "Anthropic (yolo1)", "codex": "OpenAI (cyolo1)", "gemini": "Google (gyolo1)"}
COLOR = {"claude": "#d97757", "codex": "#10a37f", "gemini": "#4285f4"}


def answer_line(text):
    m = re.findall(r"ANSWER\s*[:：]\s*`?([^\n`]*)", text or "")
    return m[-1].strip().strip("*").strip() if m else ""


def num(s):
    s = re.sub(r"[,\s฿*]|บาท|THB", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def run_hidden(kind, text, must):
    blocks = [b for b in re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", text or "", re.S) if must in b]
    if not blocks:
        return False, "no code block"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(blocks[-1])
    try:
        p = subprocess.run([sys.executable, "-I", str(HERE / "hidden_tests.py"), kind, f.name],
                           capture_output=True, text=True, timeout=120)
        if p.returncode == 0 and "PASS" in p.stdout:
            return True, "hidden tests PASS"
        err = (p.stderr.strip().splitlines() or ["?"])[-1]
        return False, "FAIL " + err[:160]
    except subprocess.TimeoutExpired:
        return False, "FAIL timeout"


def grade(task, text):
    a = answer_line(text)
    if task == "h1_math":
        return num(a) == float(KEY[task]), a
    if task == "h2_logic":
        got = ",".join(x.strip() for x in re.split(r"[,，、\s]+", a) if x.strip())
        return got == KEY[task], a
    if task == "h5_doc":
        v = num(a)
        return v is not None and abs(v - float(KEY[task])) < 0.005, a
    if task == "h3_bug":
        return run_hidden("h3", text, "def evaluate")
    return run_hidden("h4", text, "def shortest_subarray")


rows = []
for vendor, models in ORDER.items():
    for model in models:
        row = dict(vendor=vendor, model=model)
        for eff in EFFORTS:
            per = []
            for t in TASKS:
                f = OUT / f"{vendor}__{model}__{eff}__{t}.json"
                d = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"ok": False, "status": "missing"}
                if d.get("ok"):
                    ok, got = grade(t, d.get("result", ""))
                else:
                    ok, got = False, f"ERROR {d.get('status')}: {str(d.get('error'))[:150]}"
                per.append(dict(task=t, correct=ok, got=got, status=d.get("status"), duration_s=d.get("duration_s"),
                                output_tokens=d.get("output_tokens"), reasoning_tokens=d.get("reasoning_tokens"),
                                real_model=d.get("real_model"), effort_used=d.get("effort"), note=d.get("note"),
                                raw_tail=(d.get("result") or "")[-400:]))
            done = [p for p in per if p["status"] == "ok" and p["duration_s"] is not None]
            row[eff] = dict(correct=sum(p["correct"] for p in per), n_ok=len(done),
                            avg_time=round(sum(p["duration_s"] for p in done) / len(done), 1) if done else None,
                            avg_out=round(sum(p["output_tokens"] or 0 for p in done) / len(done), 1) if done else None,
                            tasks=per)
        rows.append(row)

(HERE / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

for r in rows:
    for e in EFFORTS:
        x = r[e]
        marks = " ".join(("✔" if p["correct"] else "✘") + f"{p['task'][:2]}[{p['got'][:45]}]({p['duration_s']}s)" for p in x["tasks"])
        print(f"{r['vendor']:6} {r['model']:18} {e:4} {x['correct']}/5 ok={x['n_ok']} avg={x['avg_time']} out={x['avg_out']} | {marks}")

# per-task solve rate
print("\nper task (correct / runs):")
for t in TASKS:
    c = sum(p["correct"] for r in rows for e in EFFORTS for p in r[e]["tasks"] if p["task"] == t)
    print(f"  {t}: {c}/{len(rows) * 2}")

# charts: grouped bars low/high
labels = [r["model"] for r in rows]
x = np.arange(len(rows))
w = 0.38

def grouped(key, title, ylabel, fname, fmt):
    fig, ax = plt.subplots(figsize=(14, 6.5))
    for j, (eff, alpha, hatch) in enumerate([("low", 0.45, "//"), ("high", 1.0, "")]):
        vals = [r[eff][key] for r in rows]
        bars = ax.bar(x + (j - 0.5) * w, [v or 0 for v in vals], w, alpha=alpha, hatch=hatch,
                      color=[COLOR[r["vendor"]] for r in rows], edgecolor="black", linewidth=0.4)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), "n/a" if v is None else fmt(v),
                    ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x, labels, rotation=35, ha="right")
    top = max((r[e][key] or 0) for r in rows for e in EFFORTS)
    ax.set_ylim(0, top * 1.35 if top else 1)
    ax.set_title(title); ax.set_ylabel(ylabel); ax.grid(axis="y", alpha=.3)
    h = [plt.Rectangle((0, 0), 1, 1, color=COLOR[v]) for v in ORDER]
    h += [plt.Rectangle((0, 0), 1, 1, facecolor="grey", alpha=.45, hatch="//", edgecolor="black"),
          plt.Rectangle((0, 0), 1, 1, facecolor="grey", edgecolor="black")]
    ax.legend(h, [VENDOR_LABEL[v] for v in ORDER] + ["effort: low (hatched)", "effort: high (solid)"],
              loc="upper left", ncol=2, fontsize=9)
    fig.tight_layout(); fig.savefig(HARD / fname, dpi=130); plt.close(fig)

grouped("correct", "Hard set - correct answers out of 5, by effort", "correct (of 5)", "correct_by_effort.png", lambda v: f"{v}")
grouped("avg_time", "Hard set - average time per task (s), by effort", "seconds", "avg_time_by_effort.png", lambda v: f"{v:.0f}")
print("charts saved")
