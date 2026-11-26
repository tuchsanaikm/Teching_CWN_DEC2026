#!/usr/bin/env python3
"""Build results/dataset_samples.md: first 6 rows of the training split."""
import json, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
rows = [json.loads(l) for l in open("data/train.jsonl", encoding="utf-8")][:6]
esc = lambda s: s.replace("|", "\\|").replace("\n", " ")
out = ["# ตัวอย่าง Dataset b-mc2/sql-create-context", "",
       "สับด้วย seed 0 · 6 รายการแรกของ Training Set (4,000 ตัวอย่าง) · Test Set 200 ตัวอย่าง", "",
       "| # | คำถาม (question) | โครงสร้างตาราง (context) | SQL เฉลย (answer) |", "|---|---|---|---|"]
for i, r in enumerate(rows, 1):
    out.append(f"| {i} | {esc(r['question'])} | `{esc(r['context'])}` | `{esc(r['answer'])}` |")
open("results/dataset_samples.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
