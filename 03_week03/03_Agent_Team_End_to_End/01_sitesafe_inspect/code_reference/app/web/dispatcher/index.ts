import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { createServer, request as requestHttp, type IncomingMessage, type ServerResponse } from 'node:http';
import { request as requestHttps } from 'node:https';
import { performance } from 'node:perf_hooks';
import { setTimeout as sleep } from 'node:timers/promises';
import busboy from 'busboy';
import type { PoolClient } from 'pg';
import { pool } from '../lib/db';
import { beatDispatcher, type GatewayState } from '../lib/heartbeat';
import { isUuid } from '../lib/http';
import { RESET_LOCK_KEY } from '../lib/locks';
import { absolutePhotoPath, sniffImage } from '../lib/photo-store';
import { judge, MAX_FILE_BYTES, type PhotoStatus } from '../lib/rules';

const LOOP_MS = 500;
const REQUEST_TIMEOUT_MS = 90_000;
const HEALTH_TIMEOUT_MS = 5_000;
const MAX_POLL_IDS = 100;
const IN_PROGRESS = `status IN ('QUEUED','PROCESSING')`;
const IMAGE_UNREADABLE = 'เปิดไฟล์รูปไม่ได้';
const MAX_RETRIES = 'ตรวจซ้ำครบ 3 ครั้งแล้วไม่สำเร็จ';
const STUCK_REASON = 'เกินเวลา 15 นาที';

type PendingPhoto = {
  id: string;
  original_filename: string;
  mime: string;
  sha256: string;
  storage_path: string;
  submit_attempts: number;
};

type DetectionCls = 'NO_HARDHAT' | 'NO_VEST' | 'HARDHAT' | 'VEST';

type Detection = {
  cls: DetectionCls;
  confidence: number;
  box: [number, number, number, number];
};

type Telemetry = {
  upstream?: string | null;
  server?: string | null;
  batch_size?: number | null;
  queue_ms?: number | null;
  model_ms?: number | null;
};

type ModelOutput = {
  h: number;
  v: number;
  detections: Detection[];
  image_w: number;
  image_h: number;
  model_version: string;
  conf_threshold: number;
  infer_ms: number;
  telemetry?: Telemetry;
};

type Job = {
  job_id: string;
  status: PhotoStatus;
  queued_at: string;
  started_at: string | null;
  finished_at: string | null;
  result: ModelOutput | null;
  error: { code: 'IMAGE_UNREADABLE' | 'MAX_RETRIES'; message: string } | null;
};

type GatewayReply = {
  status: number;
  retryAfter?: string;
  upstream?: string;
  json: () => unknown;
};

type Lab6DetectResponse = {
  filename?: string;
  server?: string;
  mode?: string;
  batch_size?: number;
  queue_ms?: number;
  model_ms?: number;
  image?: { width?: number; height?: number };
  count?: number;
  detections?: Array<{
    class_id?: number;
    class_name?: string;
    confidence?: number;
    box?: { x1: number; y1: number; x2: number; y2: number };
  }>;
};

function envNumber(name: string, fallback: number, minimum: number): number {
  const raw = process.env[name]?.trim();
  const value = raw ? Number(raw) : fallback;
  return Number.isFinite(value) && value >= minimum ? value : fallback;
}

function logError(message: string): void {
  const key = process.env.GATEWAY_API_KEY;
  const redacted = message
    .replace(/\bX-API-Key\s*[:=].*$/gim, 'X-API-Key: [redacted]')
    .replace(/\bBearer\s+\S+/gim, 'Bearer [redacted]');
  console.error('[dispatcher]', key ? redacted.replaceAll(key, '[redacted]') : redacted);
}

function mapLab6Class(name: string | undefined): DetectionCls | null {
  if (!name) return null;
  const norm = name.trim().toLowerCase().replace(/[\s_]+/g, '-');
  if (norm === 'no-hardhat' || norm === 'no-helmet') return 'NO_HARDHAT';
  if (norm === 'no-safety-vest' || norm === 'no-vest') return 'NO_VEST';
  if (norm === 'hardhat' || norm === 'helmet') return 'HARDHAT';
  if (norm === 'safety-vest' || norm === 'vest') return 'VEST';
  return null;
}

class Retry {
  private next = 0;
  private delay = 1000;

  get ready(): boolean {
    return performance.now() >= this.next;
  }

  get waitMs(): number {
    const remaining = this.next - performance.now();
    return remaining > 0 ? remaining : Infinity;
  }

  reset(): void {
    this.next = 0;
    this.delay = 1000;
  }

  unavailable(): void {
    this.delay = Math.min(30_000, this.delay * 2);
    this.next = performance.now() + this.delay;
  }

  rateLimited(header?: string): void {
    let delay = 5000;
    if (header && /^\d+$/.test(header)) delay = Number(header) * 1000;
    else if (header && Number.isFinite(Date.parse(header))) delay = Date.parse(header) - Date.now();
    this.next = performance.now() + Math.max(0, delay);
  }
}

class Gateway {
  private healthRetry = new Retry();
  state: GatewayState = 'down';

  constructor(
    private url: URL,
    private key: string,
    public readonly protocol: 'lab6' | 'legacy',
    private ca?: Buffer | string,
  ) {}

  isUnauthorized(): boolean {
    return this.state === 'unauthorized';
  }

  async request(path: string, form?: FormData, timeoutMs = REQUEST_TIMEOUT_MS): Promise<GatewayReply | null> {
    if (this.isUnauthorized()) return null;
    try {
      const url = new URL(path, this.url);
      const request = url.protocol === 'https:' ? requestHttps : requestHttp;
      const payload = form ? new Response(form) : undefined;
      const body = payload ? Buffer.from(await payload.arrayBuffer()) : undefined;
      if (this.isUnauthorized()) return null;
      const headers: Record<string, string | number> =
        this.protocol === 'lab6'
          ? { Authorization: `Bearer ${this.key}` }
          : { 'X-API-Key': this.key };
      if (body && payload) {
        headers['Content-Type'] = payload.headers.get('content-type')!;
        headers['Content-Length'] = body.length;
      }

      const reply = await new Promise<GatewayReply>((resolve, reject) => {
        const req = request(
          url,
          {
            headers,
            method: body ? 'POST' : 'GET',
            ca: this.ca,
            signal: AbortSignal.timeout(timeoutMs),
          },
          (res) => {
            const chunks: Buffer[] = [];
            res.on('data', (chunk: Buffer) => chunks.push(chunk));
            res.once('error', reject);
            res.once('end', () => {
              const up = res.headers['x-upstream'];
              resolve({
                status: res.statusCode ?? 503,
                retryAfter: res.headers['retry-after'],
                upstream: Array.isArray(up) ? up[0] : up,
                json: () => JSON.parse(Buffer.concat(chunks).toString('utf8')),
              });
            });
          },
        );
        req.once('error', reject);
        req.end(body);
      });
      if (reply.status === 401 && !this.isUnauthorized()) {
        this.state = 'unauthorized';
        logError('gateway rejected the API key (HTTP 401). Dispatch stopped.');
      }
      return reply;
    } catch {
      return null;
    }
  }

  async probe(): Promise<void> {
    if (this.isUnauthorized() || !this.healthRetry.ready) return;
    const path = this.protocol === 'lab6' ? '/health' : '/v1/health';
    const reply = await this.request(path, undefined, HEALTH_TIMEOUT_MS);
    if (this.isUnauthorized()) return;
    if (reply?.status === 200) {
      this.healthRetry.reset();
      this.state = 'ok';
    } else {
      this.healthRetry.unavailable();
      this.state = 'down';
    }
  }
}

async function failPhoto(client: PoolClient, id: string, reason: string): Promise<void> {
  await client.query(
    `UPDATE photos SET status = 'FAILED', dispatch_state = 'CLOSED', fail_reason = $2, finished_at = now()
     WHERE id = $1 AND ${IN_PROGRESS}`,
    [id, reason],
  );
}

async function saveCompleted(client: PoolClient, photoId: string, output: ModelOutput): Promise<void> {
  const result = judge(output.h, output.v);
  const t = output.telemetry;
  await client.query(
    `WITH completed AS (
       UPDATE photos SET status = 'DONE', dispatch_state = 'CLOSED', finished_at = now(), fail_reason = NULL,
           model_h = $2, model_v = $3, model_result = $4, current_result = $4, model_version = $5,
           conf_threshold = $6, image_w = $7, image_h = $8,
           lb_upstream = $10, lb_server = $11, lb_batch_size = $12, lb_queue_ms = $13, lb_model_ms = $14
       WHERE id = $1 AND ${IN_PROGRESS}
       RETURNING id
     )
     INSERT INTO detections (photo_id, cls, confidence, x1, y1, x2, y2)
     SELECT completed.id, d.cls, d.confidence, d.box[1], d.box[2], d.box[3], d.box[4]
     FROM completed CROSS JOIN jsonb_to_recordset($9::jsonb) AS d(cls text, confidence numeric, box integer[])`,
    [
      photoId,
      output.h,
      output.v,
      result,
      output.model_version,
      output.conf_threshold,
      output.image_w,
      output.image_h,
      JSON.stringify(output.detections),
      t?.upstream ?? null,
      t?.server ?? null,
      t?.batch_size ?? null,
      t?.queue_ms ?? null,
      t?.model_ms ?? null,
    ],
  );
}

async function saveJob(client: PoolClient, job: Job): Promise<void> {
  if (job.status === 'QUEUED' || job.status === 'PROCESSING') {
    await client.query(
      `UPDATE photos SET status = $2
       WHERE id = $1 AND dispatch_state = 'SUBMITTED' AND ${IN_PROGRESS} AND status <> $2`,
      [job.job_id, job.status],
    );
  } else if (job.status === 'FAILED') {
    await failPhoto(client, job.job_id, job.error?.code === 'MAX_RETRIES' ? MAX_RETRIES : IMAGE_UNREADABLE);
  } else if (job.status === 'DONE' && job.result) {
    await saveCompleted(client, job.job_id, job.result);
  }
}

class Dispatcher {
  private submitRetry = new Retry();
  private pollRetry = new Retry();
  private pollCursor: string | null = null;
  private stuckMinutes = envNumber('STUCK_TIMEOUT_MIN', 15, 0);
  private concurrency = Math.floor(envNumber('DISPATCH_CONCURRENCY', 16, 1));

  constructor(private gateway: Gateway) {}

  waitMs(started: number): number {
    const nextRound = Math.max(0, LOOP_MS - (performance.now() - started));
    return Math.ceil(Math.min(nextRound, this.submitRetry.waitMs, this.pollRetry.waitMs));
  }

  async round(client: PoolClient): Promise<void> {
    await beatDispatcher(client, this.gateway.state);
    const lock = await client.query<{ locked: boolean }>('SELECT pg_try_advisory_lock_shared($1) AS locked', [RESET_LOCK_KEY]);
    if (!lock.rows[0].locked) return;

    try {
      await client.query(
        `UPDATE photos SET status = 'FAILED', dispatch_state = 'CLOSED', fail_reason = $1, finished_at = now()
         WHERE ${IN_PROGRESS} AND dispatch_state <> 'CLOSED'
           AND accepted_at < now() - $2::double precision * interval '1 minute'`,
        [STUCK_REASON, this.stuckMinutes],
      );
      const health = this.gateway.probe();
      try {
        if (this.gateway.protocol === 'lab6') {
          await this.dispatchLab6Concurrent(client);
        } else {
          await this.submitLegacy(client);
          await this.pollLegacy(client);
        }
      } finally {
        await health;
      }
    } finally {
      await client.query('SELECT pg_advisory_unlock_shared($1)', [RESET_LOCK_KEY]);
      await beatDispatcher(client, this.gateway.state);
    }
  }

  /**
   * LAB 6 direct NGINX least_conn + 8× FastAPI Micro-batching concurrent dispatcher.
   * Sends up to `concurrency` photos simultaneously to POST /v1/detect so micro-batching
   * fills cleanly across both RTX 4090 GPUs and completes 20–50 photos in a few seconds.
   */
  private async dispatchLab6Concurrent(client: PoolClient): Promise<void> {
    if (!this.submitRetry.ready || this.gateway.isUnauthorized()) return;
    const pending = await client.query<PendingPhoto>(
      `SELECT id, original_filename, mime, sha256, storage_path, submit_attempts FROM photos
       WHERE dispatch_state = 'PENDING' AND ${IN_PROGRESS}
       ORDER BY accepted_at, id LIMIT $1`,
      [Math.max(this.concurrency * 2, 32)],
    );
    if (pending.rows.length === 0) return;

    // Mark batch as PROCESSING & increment attempts up-front, then run HTTP calls concurrently.
    const claimed: PendingPhoto[] = [];
    for (const p of pending.rows) {
      const r = await client.query(
        `UPDATE photos SET status = 'PROCESSING', submit_attempts = submit_attempts + 1, submitted_at = now()
         WHERE id = $1 AND dispatch_state = 'PENDING' AND ${IN_PROGRESS}`,
        [p.id],
      );
      if (r.rowCount) claimed.push({ ...p, submit_attempts: p.submit_attempts + 1 });
    }
    if (claimed.length === 0) return;

    type Outcome =
      | { kind: 'done'; photo: PendingPhoto; output: ModelOutput }
      | { kind: 'fail'; photo: PendingPhoto; reason: string }
      | { kind: 'retry'; photo: PendingPhoto; rateLimited?: string };

    const outcomes: Outcome[] = [];
    let cursor = 0;

    const worker = async () => {
      while (cursor < claimed.length && !this.gateway.isUnauthorized()) {
        const photo = claimed[cursor++];
        let bytes: Buffer;
        try {
          bytes = await readFile(absolutePhotoPath(photo.storage_path));
        } catch {
          outcomes.push({ kind: 'fail', photo, reason: IMAGE_UNREADABLE });
          continue;
        }
        const form = new FormData();
        form.set('file', new Blob([new Uint8Array(bytes)], { type: photo.mime }), photo.original_filename);
        const reply = await this.gateway.request('/v1/detect', form, REQUEST_TIMEOUT_MS);
        if (!reply) {
          outcomes.push(
            photo.submit_attempts >= 3
              ? { kind: 'fail', photo, reason: MAX_RETRIES }
              : { kind: 'retry', photo },
          );
          continue;
        }
        if (reply.status === 200) {
          try {
            const payload = reply.json() as Lab6DetectResponse;
            const dets: Detection[] = [];
            let h = 0;
            let v = 0;
            for (const d of payload.detections ?? []) {
              const cls = mapLab6Class(d.class_name);
              if (!cls || !d.box) continue;
              if (cls === 'NO_HARDHAT') h += 1;
              else if (cls === 'NO_VEST') v += 1;
              dets.push({
                cls,
                confidence: Number(d.confidence ?? 0),
                box: [
                  Math.round(d.box.x1),
                  Math.round(d.box.y1),
                  Math.round(d.box.x2),
                  Math.round(d.box.y2),
                ],
              });
            }
            const output: ModelOutput = {
              h,
              v,
              detections: dets,
              image_w: Math.max(1, Number(payload.image?.width ?? 640)),
              image_h: Math.max(1, Number(payload.image?.height ?? 640)),
              model_version: `yolo11s-lab6-${payload.mode ?? 'micro'}`,
              conf_threshold: 0.35,
              infer_ms: Number(payload.model_ms ?? 0),
              telemetry: {
                upstream: reply.upstream ?? null,
                server: payload.server ?? null,
                batch_size: payload.batch_size ?? 1,
                queue_ms: payload.queue_ms ?? 0,
                model_ms: payload.model_ms ?? 0,
              },
            };
            outcomes.push({ kind: 'done', photo, output });
          } catch {
            outcomes.push({ kind: 'fail', photo, reason: IMAGE_UNREADABLE });
          }
        } else if (reply.status === 400 || reply.status === 413 || reply.status === 415) {
          outcomes.push({ kind: 'fail', photo, reason: IMAGE_UNREADABLE });
        } else if (reply.status === 401) {
          outcomes.push({ kind: 'retry', photo });
        } else if (reply.status === 429) {
          outcomes.push({ kind: 'retry', photo, rateLimited: reply.retryAfter });
        } else {
          outcomes.push(
            photo.submit_attempts >= 3
              ? { kind: 'fail', photo, reason: MAX_RETRIES }
              : { kind: 'retry', photo },
          );
        }
      }
    };

    const workers = Math.min(this.concurrency, claimed.length);
    await Promise.all(Array.from({ length: workers }, worker));

    let anyOk = false;
    let anyRetry = false;
    let rateLimitHeader: string | undefined;
    for (const o of outcomes) {
      if (o.kind === 'done') {
        anyOk = true;
        await saveCompleted(client, o.photo.id, o.output);
      } else if (o.kind === 'fail') {
        await failPhoto(client, o.photo.id, o.reason);
      } else {
        anyRetry = true;
        if (o.rateLimited) rateLimitHeader = o.rateLimited;
        await client.query(
          `UPDATE photos SET status = 'QUEUED', dispatch_state = 'PENDING'
           WHERE id = $1 AND ${IN_PROGRESS}`,
          [o.photo.id],
        );
      }
    }
    if (anyOk) this.submitRetry.reset();
    else if (rateLimitHeader) this.submitRetry.rateLimited(rateLimitHeader);
    else if (anyRetry && !this.gateway.isUnauthorized()) this.submitRetry.unavailable();
  }

  private async submitLegacy(client: PoolClient): Promise<void> {
    if (!this.submitRetry.ready || this.gateway.isUnauthorized()) return;
    const pending = await client.query<PendingPhoto>(
      `SELECT id, original_filename, mime, sha256, storage_path, submit_attempts FROM photos
       WHERE dispatch_state = 'PENDING' AND ${IN_PROGRESS} ORDER BY accepted_at, id LIMIT $1`,
      [MAX_POLL_IDS],
    );
    const deadline = performance.now() + LOOP_MS;
    for (const photo of pending.rows) {
      if (performance.now() >= deadline || !(await this.submitPhotoLegacy(client, photo))) break;
    }
  }

  private async submitPhotoLegacy(client: PoolClient, photo: PendingPhoto): Promise<boolean> {
    if (this.gateway.isUnauthorized()) return false;
    let bytes: Buffer<ArrayBufferLike>;
    try {
      bytes = await readFile(absolutePhotoPath(photo.storage_path));
    } catch {
      await failPhoto(client, photo.id, IMAGE_UNREADABLE);
      return true;
    }

    const form = new FormData();
    form.set('job_id', photo.id);
    form.set('sha256', photo.sha256);
    form.set('image', new Blob([new Uint8Array(bytes)], { type: photo.mime }), photo.original_filename);
    if (this.gateway.isUnauthorized()) return false;
    const attempt = await client.query(
      `UPDATE photos SET submit_attempts = submit_attempts + 1
       WHERE id = $1 AND dispatch_state = 'PENDING' AND ${IN_PROGRESS}`,
      [photo.id],
    );
    if (!attempt.rowCount) return true;
    const reply = await this.gateway.request('/v1/jobs', form);
    switch (reply?.status) {
      case 200:
      case 202:
        this.submitRetry.reset();
        await client.query(
          `UPDATE photos SET dispatch_state = 'SUBMITTED', submitted_at = now()
           WHERE id = $1 AND dispatch_state = 'PENDING' AND ${IN_PROGRESS}`,
          [photo.id],
        );
        return true;
      case 400:
      case 413:
      case 415:
        this.submitRetry.reset();
        await failPhoto(client, photo.id, IMAGE_UNREADABLE);
        return true;
      case 401:
        return false;
      case 429:
        this.submitRetry.rateLimited(reply.retryAfter);
        return false;
      default:
        this.submitRetry.unavailable();
        return false;
    }
  }

  private async pollLegacy(client: PoolClient): Promise<void> {
    if (!this.pollRetry.ready || this.gateway.isUnauthorized()) return;
    const { rows } = await client.query<{ id: string }>(
      `SELECT id FROM photos WHERE dispatch_state = 'SUBMITTED' AND ${IN_PROGRESS}
         AND ($1::uuid IS NULL OR id > $1) ORDER BY id LIMIT $2`,
      [this.pollCursor, MAX_POLL_IDS],
    );
    if (rows.length === 0) {
      this.pollCursor = null;
      return;
    }
    const ids = rows.map(({ id }) => id);
    const reply = await this.gateway.request(`/v1/jobs?ids=${ids.join(',')}`);
    let unknownIds: string[];
    if (reply?.status === 404) {
      unknownIds = ids;
    } else if (reply?.status === 200) {
      let payload: { jobs: Job[]; not_found: string[] };
      try {
        payload = reply.json() as typeof payload;
        if (!Array.isArray(payload?.jobs) || !Array.isArray(payload.not_found)) throw new Error();
      } catch {
        this.pollRetry.unavailable();
        return;
      }
      const requested = new Set(ids);
      this.pollCursor = rows.length === MAX_POLL_IDS ? ids[ids.length - 1] : null;
      for (const job of payload.jobs) {
        if (job && requested.has(job.job_id)) await saveJob(client, job);
      }
      unknownIds = payload.not_found.filter((id) => requested.has(id));
    } else {
      if (reply?.status === 429) this.pollRetry.rateLimited(reply.retryAfter);
      else if (reply?.status !== 401) this.pollRetry.unavailable();
      return;
    }
    this.pollRetry.reset();
    if (unknownIds.length) {
      await client.query(
        `UPDATE photos SET status = 'QUEUED', dispatch_state = 'PENDING', submitted_at = NULL
         WHERE id = ANY($1::uuid[]) AND dispatch_state = 'SUBMITTED' AND ${IN_PROGRESS}`,
        [unknownIds],
      );
    }
  }
}

export async function runDispatcher(gateway: Gateway, signal: AbortSignal): Promise<void> {
  const dispatcher = new Dispatcher(gateway);
  let client: PoolClient | undefined;
  let disconnected = false;
  const markDisconnected = () => { disconnected = true; };

  try {
    while (!signal.aborted) {
      const started = performance.now();
      try {
        if (disconnected) throw new Error('database disconnected');
        if (!client) {
          client = await pool().connect();
          client.on('error', markDisconnected);
        }
        await dispatcher.round(client);
      } catch {
        logError('database round failed. Retrying on the next round.');
        client?.removeListener('error', markDisconnected);
        client?.release(true);
        client = undefined;
        disconnected = false;
      }
      if (!signal.aborted) {
        await sleep(dispatcher.waitMs(started), undefined, { signal }).catch(() => undefined);
      }
    }
  } finally {
    client?.removeListener('error', markDisconnected);
    client?.release(true);
  }
}

// The mock is an HTTP service so the dispatcher exercises the same protocol in mock mode.
const MOCK_MODEL = 'ppe-mock-v1';
const MOCK_THRESHOLD = 0.5;
const FRAME_MARKERS = new Set([0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf]);

function imageDimensions(data: Buffer, mime: string): [number, number] {
  if (mime === 'image/png' && data.length >= 24 && data.toString('ascii', 12, 16) === 'IHDR') {
    return [data.readUInt32BE(16), data.readUInt32BE(20)];
  }
  if (mime === 'image/jpeg') {
    let offset = 2;
    while (offset + 4 <= data.length && data[offset] === 0xff) {
      const marker = data[offset + 1];
      if (marker === 0xff) { offset += 1; continue; }
      if (marker === 0xda || marker === 0xd9) break;
      const length = data.readUInt16BE(offset + 2);
      if (length < 2 || offset + 2 + length > data.length) break;
      if (FRAME_MARKERS.has(marker) && length >= 8) {
        return [data.readUInt16BE(offset + 7), data.readUInt16BE(offset + 5)];
      }
      offset += 2 + length;
    }
  }
  return [640, 480];
}

type MockImage = { filename: string; bytes: Buffer };
type MockUpload = { jobId?: string; sha256?: string; image?: MockImage; oversized: boolean };

function readMultipart(req: IncomingMessage): Promise<MockUpload> {
  const parser = busboy({
    headers: req.headers,
    defParamCharset: 'utf8',
    limits: { files: 1, fileSize: MAX_FILE_BYTES + 1, fields: 16, fieldSize: 4096, parts: 18 },
  });
  return new Promise((resolve, reject) => {
    const upload: MockUpload = { oversized: false };
    parser.on('field', (name, value, info) => {
      if (info.valueTruncated) return;
      if (name === 'job_id') upload.jobId = value.trim().toLowerCase();
      if (name === 'sha256') upload.sha256 = value.trim().toLowerCase();
    });
    parser.on('file', (name, stream, info) => {
      const chunks: Buffer[] = [];
      if (name === 'image') {
        stream.on('data', (chunk: Buffer) => chunks.push(chunk));
        stream.once('end', () => {
          if (!upload.oversized) upload.image = { filename: info.filename ?? '', bytes: Buffer.concat(chunks) };
        });
      } else {
        stream.resume();
      }
      stream.once('limit', () => { upload.oversized = true; });
      stream.once('error', reject);
    });
    for (const event of ['filesLimit', 'fieldsLimit', 'partsLimit']) {
      parser.once(event, () => reject(new Error('invalid multipart')));
    }
    parser.once('close', () => resolve(upload));
    parser.once('error', reject);
    req.once('error', (err) => parser.destroy(err));
    req.pipe(parser);
  });
}

function mockResult(image: MockImage, mime: string): ModelOutput | null {
  const counts = /^h(\d+)_v(\d+).*\.(?:jpg|png)$/i.exec(image.filename);
  const h = Number(counts?.[1] ?? 0);
  const v = Number(counts?.[2] ?? 0);
  if (h + v > 10_000) return null;
  const [width, height] = imageDimensions(image.bytes, mime);
  const image_w = Math.max(1, width);
  const image_h = Math.max(1, height);
  const detections = Array.from({ length: h + v }, (_, i): Detection => {
    const x = Math.floor(image_w * ((i % 8) / 10));
    const y = Math.floor(image_h * ((Math.floor(i / 8) % 6) / 8));
    return {
      cls: i < h ? 'NO_HARDHAT' : 'NO_VEST',
      confidence: 0.9,
      box: [x, y, Math.min(image_w, x + Math.ceil(image_w / 5)), Math.min(image_h, y + Math.ceil(image_h / 4))],
    };
  });
  return {
    h,
    v,
    detections,
    image_w,
    image_h,
    model_version: MOCK_MODEL,
    conf_threshold: MOCK_THRESHOLD,
    infer_ms: 4.2,
    telemetry: {
      upstream: '127.0.0.1:8101',
      server: 'mock-gpu0-8101',
      batch_size: 1,
      queue_ms: 0.4,
      model_ms: 4.2,
    },
  };
}

function respond(res: ServerResponse, status: number, body: unknown, headers: Record<string, string | number> = {}): void {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', ...headers });
  res.end(JSON.stringify(body));
}

export function createMockGateway(key: string) {
  const jobs = new Map<string, { job: Job; readyAt: number }>();
  const digest = (value: string) => createHash('sha256').update(value).digest();
  const keyDigest = digest(key);
  const available = process.env.MOCK_QUEUE_AVAILABLE !== '0';
  const workers = Math.floor(envNumber('MOCK_WORKERS', 1, 0));
  const maxDepth = Math.floor(envNumber('MAX_QUEUE_DEPTH', 200, 1));
  const delay = envNumber('MOCK_QUEUE_DELAY_MS', 150, 0);
  const view = ({ job, readyAt }: { job: Job; readyAt: number }): Job => workers > 0 && Date.now() >= readyAt
    ? job
    : { ...job, status: 'QUEUED', started_at: null, finished_at: null, result: null, error: null };
  const depth = () => [...jobs.values()].filter((entry) => view(entry).status === 'QUEUED').length;

  async function handle(req: IncomingMessage, res: ServerResponse): Promise<void> {
    const supplied = req.headers['x-api-key'];
    if (!timingSafeEqual(digest(typeof supplied === 'string' ? supplied : ''), keyDigest) || !key) {
      respond(res, 401, { error: 'UNAUTHORIZED', message: 'ต้องมี X-API-Key ที่ถูกต้อง' });
      return;
    }
    const url = new URL(req.url ?? '/', 'http://localhost');
    const badRequest = (message: string) => respond(res, 400, { error: 'BAD_REQUEST', message });
    const notFound = () => respond(res, 404, { error: 'JOB_NOT_FOUND', message: 'ไม่พบงานนี้' });

    if (req.method === 'GET' && url.pathname === '/v1/health') {
      const healthy = available && workers > 0;
      respond(res, healthy ? 200 : 503, {
        status: healthy ? 'ok' : 'down', upstream: available ? 'ok' : 'down', workers: available ? workers : 0,
        queue_depth: depth(), max_queue_depth: maxDepth, gpu: 'mock', model_version: MOCK_MODEL,
      });
    } else if (req.method === 'GET' && url.pathname === '/v1/jobs') {
      const raw = url.searchParams.get('ids');
      const ids = [...new Set(raw?.split(',').map((id) => id.trim()).filter(Boolean))];
      if (raw === null || ids.length > MAX_POLL_IDS) return badRequest('ต้องระบุ ids ไม่เกิน 100 งาน');
      const found = [], not_found = [];
      for (const id of ids) {
        const entry = jobs.get(id.toLowerCase());
        if (entry) found.push(view(entry));
        else not_found.push(id);
      }
      respond(res, 200, { jobs: found, not_found });
    } else if (req.method === 'GET' && url.pathname.startsWith('/v1/jobs/')) {
      const entry = jobs.get(decodeURIComponent(url.pathname.slice('/v1/jobs/'.length)).toLowerCase());
      if (entry) respond(res, 200, view(entry));
      else notFound();
    } else if (req.method === 'POST' && url.pathname === '/v1/jobs') {
      let upload: MockUpload;
      try {
        upload = await readMultipart(req);
      } catch {
        req.resume();
        return badRequest('multipart ไม่ถูกต้อง');
      }
      const { jobId, image, sha256 } = upload;
      if (!isUuid(jobId)) return badRequest('ต้องมี job_id เป็น UUID');
      const existing = jobs.get(jobId);
      if (existing) return respond(res, 200, view(existing));
      if (upload.oversized) return respond(res, 413, { error: 'FILE_TOO_LARGE', message: 'ไฟล์ใหญ่เกินกำหนด' });
      if (!image || !sha256 || !/^[0-9a-f]{64}$/.test(sha256)) return badRequest('ต้องมี image และ sha256');
      const kind = sniffImage(image.bytes);
      if (!kind) return respond(res, 415, { error: 'UNSUPPORTED_TYPE', message: 'รับเฉพาะไฟล์ JPG และ PNG' });
      if (createHash('sha256').update(image.bytes).digest('hex') !== sha256) return badRequest('sha256 ไม่ตรงกับไฟล์');
      if (!available) return respond(res, 503, { error: 'QUEUE_UNAVAILABLE', message: 'คิวใช้งานไม่ได้' });
      const queueDepth = depth();
      if (queueDepth >= maxDepth) {
        const retryAfter = Math.max(5, Math.ceil((queueDepth - maxDepth + 10) * delay / 1000));
        return respond(res, 429, {
          error: 'QUEUE_FULL', message: 'คิวเต็ม', queue_depth: queueDepth, max_queue_depth: maxDepth, retry_after_s: retryAfter,
        }, { 'Retry-After': retryAfter });
      }
      const error = /^corrupt.*\.jpg$/i.test(image.filename)
        ? { code: 'IMAGE_UNREADABLE' as const, message: IMAGE_UNREADABLE } : null;
      const result = error ? null : mockResult(image, kind.mime);
      if (!error && !result) return badRequest('จำนวน detections ของรูปจำลองเกินกำหนด');
      const now = Date.now();
      const queuedAt = new Date(now).toISOString();
      const readyAt = now + delay;
      jobs.set(jobId, { readyAt, job: {
        job_id: jobId, queued_at: queuedAt, started_at: queuedAt, finished_at: new Date(readyAt).toISOString(),
        status: error ? 'FAILED' : 'DONE', result, error,
      } });
      respond(res, 202, { job_id: jobId, status: 'QUEUED', queue_depth: queueDepth + 1 });
    } else {
      notFound();
    }
  }

  return createServer((req, res) => {
    void handle(req, res).catch(() => {
      if (!res.headersSent) respond(res, 400, { error: 'BAD_REQUEST', message: 'คำขอไม่ถูกต้อง' });
      else res.destroy();
    });
  });
}

async function listenMock(key: string, host: string, port: number) {
  const server = createMockGateway(key);
  await new Promise<void>((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, host, () => {
      server.removeListener('error', reject);
      resolve();
    });
  });
  return server;
}

async function main(): Promise<void> {
  let key = process.env.GATEWAY_API_KEY ?? '';
  if (process.argv.includes('--mock-gateway')) {
    await listenMock(key, '0.0.0.0', envNumber('MOCK_GATEWAY_PORT', 8080, 0));
    return;
  }

  const mockMode = process.env.AI_MODE === 'mock';
  const protocol: 'lab6' | 'legacy' =
    mockMode || process.env.GATEWAY_PROTOCOL?.toLowerCase() === 'legacy' ? 'legacy' : 'lab6';
  const configuredUrl = process.env.GATEWAY_URL?.trim();
  const caSpec = process.env.GATEWAY_CA_CERT?.trim();
  let server: Awaited<ReturnType<typeof listenMock>> | undefined;
  let url: URL;
  if (mockMode && !configuredUrl) {
    key ||= randomBytes(32).toString('hex');
    server = await listenMock(key, '127.0.0.1', 0);
    const address = server.address();
    if (!address || typeof address === 'string') throw new Error('mock-gateway has no TCP address');
    url = new URL(`http://127.0.0.1:${address.port}`);
  } else {
    if (!configuredUrl) throw new Error('GATEWAY_URL is missing');
    url = new URL(configuredUrl);
    if (url.protocol !== 'https:' && url.protocol !== 'http:') {
      throw new Error('GATEWAY_URL must use HTTP or HTTPS');
    }
  }
  const stop = new AbortController();
  const stopDispatcher = () => stop.abort();
  process.on('SIGINT', stopDispatcher);
  process.on('SIGTERM', stopDispatcher);
  try {
    const ca = caSpec && url.protocol === 'https:'
      ? (caSpec.startsWith('-----BEGIN CERTIFICATE-----') ? caSpec : await readFile(caSpec))
      : undefined;
    await runDispatcher(new Gateway(url, key, protocol, ca), stop.signal);
  } finally {
    process.removeListener('SIGINT', stopDispatcher);
    process.removeListener('SIGTERM', stopDispatcher);
    server?.close();
    await pool().end();
  }
}

if (require.main === module) {
  void main().catch(() => {
    logError('startup failed. Check DATABASE_URL, GATEWAY_URL, GATEWAY_CA_CERT and mock port settings.');
    process.exitCode = 1;
  });
}
