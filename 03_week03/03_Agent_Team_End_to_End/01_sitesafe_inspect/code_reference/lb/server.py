"""LAB 6 - object detection API (FastAPI + YOLO11s) with a single-thread inference worker.

One server process owns one GPU and calls the model one call at a time.
Requests are put in a queue; ONE worker thread (the same thread for the whole
life of the process: load, warm-up, every inference) takes jobs from it.

  MODE=single : take 1 image per model call
  MODE=micro  : take every image waiting in the queue (max MAX_BATCH = 32) into one
                model call; if fewer than MAX_BATCH, wait at most MAX_WAIT_MS = 5 ms for more

  MODEL_SLOWDOWN=F (default 1) : pretend this GPU is F times slower - every model call for a request
                takes F times as long (the same call is done again, so the GPU is really busy).

Config comes from environment variables (see run_server.sh).
"""
import asyncio
import hmac
import os
import queue
import threading
import time
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

MODEL_PATH = os.environ.get("MODEL_PATH", "best.pt")
MODE = os.environ.get("MODE", "single").lower()          # single | micro
IMGSZ = int(os.environ.get("IMGSZ", "640"))
CONF = float(os.environ.get("CONF", "0.35"))
MAX_WAIT_MS = float(os.environ.get("MAX_WAIT_MS", "5"))
SERVER_ID = os.environ.get("SERVER_ID", "server-1")
API_KEY = os.environ.get("API_KEY", "")
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "20")) * 1024 * 1024
# share of the GPU memory this process may use (0 = no limit). Several servers that warm up on the same
# GPU at the same time each try to take much more than they need and one of them dies with CUDA OOM.
GPU_MEM_FRACTION = float(os.environ.get("GPU_MEM_FRACTION", "0"))

# F >= 1: a model call for a request takes F times as long (1 = normal speed). Warm-up is not slowed.
MODEL_SLOWDOWN = float(os.environ.get("MODEL_SLOWDOWN", "1") or "1")

if not 1.0 <= MODEL_SLOWDOWN <= 100.0:
    raise SystemExit(f"MODEL_SLOWDOWN must be 1..100, got {MODEL_SLOWDOWN!r}")
if MODE not in ("single", "micro"):
    raise SystemExit(f"MODE must be 'single' or 'micro', got {MODE!r}")
if not API_KEY:
    raise SystemExit("API_KEY is not set")
MAX_BATCH = 1 if MODE == "single" else int(os.environ.get("MAX_BATCH", "32"))


class Job:
    __slots__ = ("image", "loop", "future", "t_enqueue")

    def __init__(self, image, loop):
        self.image = image
        self.loop = loop
        self.future = loop.create_future()
        self.t_enqueue = time.perf_counter()


class InferenceWorker(threading.Thread):
    """The only thread that ever touches the model."""

    def __init__(self):
        super().__init__(name="inference-worker", daemon=True)
        self.jobs: "queue.Queue[Job | None]" = queue.Queue()
        self.ready = threading.Event()
        self.error: str | None = None
        self.warmup_ms: dict[int, float] = {}
        self.device = None
        self.names: dict[int, str] = {}
        self.model = None

    # ---- model call (worker thread only) ----
    def _predict(self, images):
        return self.model.predict(images, imgsz=IMGSZ, conf=CONF, verbose=False)

    def _predict_slowed(self, images):
        """Model call for real requests. MODEL_SLOWDOWN = F: the work of the call is done F times
        (whole part: the same call again; rest of F: sleep that share of one call), the first answer is kept."""
        t0 = time.perf_counter()
        results = self._predict(images)
        if MODEL_SLOWDOWN > 1.0:
            one = time.perf_counter() - t0
            extra = MODEL_SLOWDOWN - 1.0
            while extra >= 1.0:
                self._predict(images)
                extra -= 1.0
            if extra > 1e-9:
                time.sleep(extra * one)
        return results

    def _load_and_warmup(self):
        import torch
        from ultralytics import YOLO

        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        if self.device != "cpu" and 0 < GPU_MEM_FRACTION < 1:
            torch.cuda.set_per_process_memory_fraction(GPU_MEM_FRACTION, 0)
        self.model = YOLO(MODEL_PATH)
        self.model.to(self.device)
        self.names = dict(self.model.names)
        dummy = np.random.default_rng(0).integers(0, 255, (IMGSZ, IMGSZ, 3), dtype=np.uint8)
        self._predict([dummy])                       # first call: builds predictor, CUDA init
        for n in range(1, MAX_BATCH + 1):            # every batch size this mode can produce
            t0 = time.perf_counter()
            self._predict([dummy] * n)
            self.warmup_ms[n] = round((time.perf_counter() - t0) * 1000, 2)

    # ---- queue handling ----
    def _take_batch(self):
        first = self.jobs.get()                      # block until there is work
        if first is None:
            return None
        batch = [first]
        if MAX_BATCH > 1:
            deadline = time.perf_counter() + MAX_WAIT_MS / 1000.0
            while len(batch) < MAX_BATCH:
                try:                                 # everything already waiting comes out at once;
                    remaining = deadline - time.perf_counter()   # then wait up to the deadline
                    job = self.jobs.get_nowait() if remaining <= 0 else self.jobs.get(timeout=remaining)
                except queue.Empty:
                    break
                if job is None:
                    self.jobs.put(None)
                    break
                batch.append(job)
        return batch

    def run(self):
        try:
            self._load_and_warmup()
        except Exception as exc:                     # startup failure is reported by lifespan
            self.error = f"{type(exc).__name__}: {exc}"
            self.ready.set()
            return
        self.ready.set()
        while True:
            batch = self._take_batch()
            if batch is None:
                return
            t0 = time.perf_counter()
            try:
                results = self._predict_slowed([j.image for j in batch])
                model_ms = (time.perf_counter() - t0) * 1000
                outs = []
                for job, res in zip(batch, results):
                    boxes = res.boxes
                    xyxy = boxes.xyxy.cpu().numpy()
                    confs = boxes.conf.cpu().numpy()
                    clss = boxes.cls.cpu().numpy().astype(int)
                    dets = [
                        {
                            "class_id": int(c),
                            "class_name": self.names.get(int(c), str(int(c))),
                            "confidence": round(float(p), 4),
                            "box": {k: round(float(v), 1) for k, v in zip(("x1", "y1", "x2", "y2"), b)},
                        }
                        for b, p, c in zip(xyxy, confs, clss)
                    ]
                    outs.append(
                        {
                            "server": SERVER_ID,
                            "mode": MODE,
                            "batch_size": len(batch),
                            "queue_ms": round((t0 - job.t_enqueue) * 1000, 2),
                            "model_ms": round(model_ms, 2),
                            "image": {"width": int(job.image.shape[1]), "height": int(job.image.shape[0])},
                            "count": len(dets),
                            "detections": dets,
                        }
                    )
                for job, out in zip(batch, outs):
                    job.loop.call_soon_threadsafe(_resolve, job.future, out, None)
            except Exception as exc:
                for job in batch:
                    job.loop.call_soon_threadsafe(_resolve, job.future, None, exc)


def _resolve(future, value, exc):
    if future.done():                                # client went away
        return
    if exc is not None:
        future.set_exception(exc)
    else:
        future.set_result(value)


worker = InferenceWorker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker.start()
    await asyncio.to_thread(worker.ready.wait)       # port opens only after warm-up is done
    if worker.error:
        raise RuntimeError(f"model startup failed: {worker.error}")
    yield
    worker.jobs.put(None)


app = FastAPI(title="LAB6 detect API", lifespan=lifespan)


def require_key(request: Request):
    auth = request.headers.get("authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(token.strip().encode(), API_KEY.encode()):
        raise HTTPException(status_code=401, detail="missing or invalid API key",
                            headers={"WWW-Authenticate": "Bearer"})


@app.middleware("http")
async def auth_before_body(request: Request, call_next):
    # reject bad keys before the upload body is parsed
    if request.url.path.startswith("/v1/"):
        try:
            require_key(request)
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)
    return await call_next(request)


@app.get("/health")
async def health():
    ok = worker.ready.is_set() and worker.error is None and worker.is_alive()
    body = {
        "status": "ready" if ok else "not_ready",
        "server": SERVER_ID,
        "mode": MODE,
        "max_batch": MAX_BATCH,
        "max_wait_ms": MAX_WAIT_MS if MODE == "micro" else 0,
        "slowdown": MODEL_SLOWDOWN,
        "imgsz": IMGSZ,
        "conf": CONF,
        "device": worker.device,
        "classes": list(worker.names.values()),
        "warmed_batch_sizes": len(worker.warmup_ms),
        "queue_len": worker.jobs.qsize(),
    }
    return JSONResponse(body, status_code=200 if ok else 503)


def _decode(data: bytes):
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)


@app.post("/v1/detect", dependencies=[Depends(require_key)])
async def detect(file: UploadFile = File(...)):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="file too large")
    image = await asyncio.to_thread(_decode, data) if data else None
    if image is None:
        raise HTTPException(status_code=400, detail="file is not a readable image")
    job = Job(image, asyncio.get_running_loop())
    worker.jobs.put(job)
    try:
        out = await job.future
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"inference failed: {type(exc).__name__}")
    return {"filename": file.filename, **out}
