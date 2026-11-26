"""Run ON the rented machine: send the 6 sample images with the API key, check 401 without / with a wrong key,
then draw the 2x3 grid (boxes + class names from the API answers, file size under each image)."""
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import requests

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001"
SAMPLES = Path(sys.argv[2] if len(sys.argv) > 2 else "/workspace/lab6/samples")
OUT = Path(sys.argv[3] if len(sys.argv) > 3 else "/workspace/lab6/results")
KEY = os.environ["API_KEY"]
OUT.mkdir(parents=True, exist_ok=True)

health = requests.get(f"{URL}/health", timeout=10)
report = {"health": {"status_code": health.status_code, "body": health.json()}, "images": [], "auth": {}}

files = sorted(SAMPLES.glob("*.jpg"))
assert len(files) == 6, f"expected 6 samples, found {len(files)}"
for rnd in (1, 2):                                  # round 2 = steady state numbers
    for f in files:
        with open(f, "rb") as fh:
            r = requests.post(f"{URL}/v1/detect", headers={"Authorization": f"Bearer {KEY}"},
                              files={"file": (f.name, fh, "image/jpeg")}, timeout=60)
        r.raise_for_status()
        if rnd == 1:
            report["images"].append({"file": f.name, "bytes": f.stat().st_size, "status_code": r.status_code,
                                     "response": r.json()})
        else:
            next(i for i in report["images"] if i["file"] == f.name)["model_ms_round2"] = r.json()["model_ms"]

f0 = files[0]
for name, headers in (("no_key", {}), ("wrong_key", {"Authorization": "Bearer not-the-key"}),
                      ("wrong_scheme", {"Authorization": "Basic abc"})):
    with open(f0, "rb") as fh:
        r = requests.post(f"{URL}/v1/detect", headers=headers, files={"file": (f0.name, fh, "image/jpeg")}, timeout=30)
    report["auth"][name] = {"status_code": r.status_code, "body": r.json()}
r = requests.post(f"{URL}/v1/detect", headers={"Authorization": f"Bearer {KEY}"},
                  files={"file": ("x.jpg", b"not an image", "image/jpeg")}, timeout=30)
report["bad_image"] = {"status_code": r.status_code, "body": r.json()}

(OUT / "test_results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

# ---- 2x3 grid ----
CW, CH, CAP = 640, 480, 44
PALETTE = [(40, 40, 230), (40, 170, 40), (230, 120, 30), (30, 190, 230), (200, 40, 200), (120, 120, 30)]
cells = []
for item in report["images"]:
    img = cv2.imread(str(SAMPLES / item["file"]))
    for d in item["response"]["detections"]:
        b = d["box"]; col = PALETTE[d["class_id"] % len(PALETTE)]
        p1, p2 = (int(b["x1"]), int(b["y1"])), (int(b["x2"]), int(b["y2"]))
        cv2.rectangle(img, p1, p2, col, 2)
        label = f'{d["class_name"]} {d["confidence"]:.2f}'
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        y = p1[1] - 4 if p1[1] - th - 6 >= 0 else p1[1] + th + 6
        cv2.rectangle(img, (p1[0], y - th - 4), (p1[0] + tw + 4, y + 3), col, -1)
        cv2.putText(img, label, (p1[0] + 2, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    h, w = img.shape[:2]
    s = min(CW / w, CH / h)
    small = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    cell = np.full((CH + CAP, CW, 3), 255, np.uint8)
    oy, ox = (CH - small.shape[0]) // 2, (CW - small.shape[1]) // 2
    cell[oy:oy + small.shape[0], ox:ox + small.shape[1]] = small
    cap = f'{item["file"]}  |  {item["bytes"] / 1024:.1f} KB ({item["bytes"]:,} bytes)  |  {w}x{h}  |  {item["response"]["count"]} objects'
    cv2.putText(cell, cap, (10, CH + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 1, cv2.LINE_AA)
    cells.append(cell)
gap = 8
row = lambda cs: np.hstack([np.pad(c, ((gap, gap), (gap, gap), (0, 0)), constant_values=255) for c in cs])
grid = np.vstack([row(cells[:3]), row(cells[3:])])
cv2.imwrite(str(OUT / "dataset_samples.jpg"), grid, [cv2.IMWRITE_JPEG_QUALITY, 92])

# ---- short console summary (no key printed) ----
print("health:", health.status_code, report["health"]["body"]["status"], report["health"]["body"]["mode"],
      report["health"]["body"]["device"], "warmed:", report["health"]["body"]["warmed_batch_sizes"])
for i in report["images"]:
    r = i["response"]; cnt = {}
    for d in r["detections"]:
        cnt[d["class_name"]] = cnt.get(d["class_name"], 0) + 1
    print(i["file"], i["bytes"], i["status_code"], r["server"], "batch", r["batch_size"], "queue_ms", r["queue_ms"],
          "model_ms", r["model_ms"], "round2", i["model_ms_round2"], cnt)
print("auth:", {k: v["status_code"] for k, v in report["auth"].items()}, "bad_image:", report["bad_image"]["status_code"])
