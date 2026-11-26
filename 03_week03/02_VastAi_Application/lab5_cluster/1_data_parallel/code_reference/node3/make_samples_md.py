#!/usr/bin/env python3
"""Build results/dataset_samples.md from the first 6 rows of the shared training set."""
import json
rows = [json.loads(l) for l in open("state/samples6.jsonl")]
esc = lambda s: s.replace("|", "\\|").replace("\n", " ")
out = ["# ตัวอย่าง Dataset b-mc2/sql-create-context (6 รายการแรกของ Training Set, สับด้วย seed 0)", "",
       "| # | คำถาม (question) | โครงสร้างตาราง (context) | SQL เฉลย (answer) |", "|---|---|---|---|"]
for i, r in enumerate(rows, 1):
    out.append(f"| {i} | {esc(r['question'])} | `{esc(r['context'])}` | `{esc(r['answer'])}` |")
open("results/dataset_samples.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
