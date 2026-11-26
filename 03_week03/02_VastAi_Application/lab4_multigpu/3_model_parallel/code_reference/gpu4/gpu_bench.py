"""Run the same workload on each GPU, one at a time, and compare speed.
Workload: FP16 matmul 8192x8192 plus a small transformer-layer train step."""
import json, sys, time, torch

def bench(i, rounds=3):
    dev = torch.device(f"cuda:{i}")
    g = torch.Generator(device=dev).manual_seed(0)
    a = torch.randn(8192, 8192, device=dev, dtype=torch.half, generator=g)
    b = torch.randn(8192, 8192, device=dev, dtype=torch.half, generator=g)
    torch.manual_seed(0)
    layer = torch.nn.TransformerEncoderLayer(1024, 16, 4096, batch_first=True).to(dev)
    opt = torch.optim.SGD(layer.parameters(), lr=1e-4)
    x = torch.randn(16, 256, 1024, device=dev, generator=g)

    def matmul(n=60):
        for _ in range(n): (a @ b)
    def train(n=30):
        for _ in range(n):
            with torch.autocast("cuda", dtype=torch.float16):
                loss = layer(x).float().pow(2).mean()
            opt.zero_grad(); loss.backward(); opt.step()
    def timed(fn, n):
        torch.cuda.synchronize(dev); t = time.perf_counter(); fn(n); torch.cuda.synchronize(dev)
        return n / (time.perf_counter() - t)

    matmul(10); train(5)  # warm-up
    mm = max(timed(matmul, 60) for _ in range(rounds))
    tr = max(timed(train, 30) for _ in range(rounds))
    del a, b, layer, x; torch.cuda.empty_cache()
    return {"gpu": i, "name": torch.cuda.get_device_name(i), "matmul_it_s": round(mm, 2), "train_it_s": round(tr, 2)}

res = [bench(i) for i in range(torch.cuda.device_count())]
for k in ("matmul_it_s", "train_it_s"):
    best = max(r[k] for r in res)
    for r in res: r[k.replace("it_s", "slower_pct")] = round((1 - r[k] / best) * 100, 1)
worst = max(max(r["matmul_slower_pct"], r["train_slower_pct"]) for r in res)
out = {"torch": torch.__version__, "cuda": torch.version.cuda, "gpus": res,
       "worst_slower_pct": worst, "pass": worst <= 20.0}
print(json.dumps(out, indent=1))
if len(sys.argv) > 1: json.dump(out, open(sys.argv[1], "w"), indent=1)
