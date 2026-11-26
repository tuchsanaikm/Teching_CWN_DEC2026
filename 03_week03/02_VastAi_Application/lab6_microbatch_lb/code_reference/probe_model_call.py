# where does the time of one model call go? (run on the idle GPU 1, same settings as server.py)
import glob, time, cv2, numpy as np, torch
from ultralytics import YOLO
m = YOLO("/workspace/lab6/best.pt"); m.to("cuda:0")
imgs = [cv2.imread(p) for p in sorted(glob.glob("/workspace/lab6/samples/*.jpg"))]
print("image sizes", [i.shape for i in imgs])
for n in (1, 2, 4, 8, 16, 32):
    batch = [imgs[i % len(imgs)] for i in range(n)]
    for _ in range(3): m.predict(batch, imgsz=640, conf=0.35, verbose=False)
    tot = []; sp = {"preprocess": [], "inference": [], "postprocess": []}
    for _ in range(15):
        t0 = time.perf_counter(); r = m.predict(batch, imgsz=640, conf=0.35, verbose=False)
        tot.append((time.perf_counter() - t0) * 1000)
        for k in sp: sp[k].append(r[0].speed[k] * n)      # speed is ms per image
    print(f"batch={n:2d} call={np.median(tot):7.1f} ms  per-image={np.median(tot)/n:5.1f}  "
          + "  ".join(f"{k}={np.median(v):6.1f}" for k, v in sp.items()))
