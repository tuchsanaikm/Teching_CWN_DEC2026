// GET /api/telemetry — live LAB 6 Multi-GPU NGINX least_conn + Micro-batching telemetry
import { promises as fs } from 'node:fs';
import path from 'node:path';
import type { NextRequest } from 'next/server';
import { requireAccess } from '@/lib/access';
import { pool } from '@/lib/db';
import { readDispatcherState } from '@/lib/heartbeat';
import { json, serverError } from '@/lib/http';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type UpstreamProbe = {
  reachable: boolean;
  status: number | null;
  upstream: string | null;
  server: string | null;
  mode: string | null;
  max_batch: number | null;
  max_wait_ms: number | null;
  device: string | null;
  queue_len: number | null;
  latency_ms: number | null;
};

async function probeUpstream(): Promise<UpstreamProbe> {
  const gw = process.env.GATEWAY_URL?.trim();
  const mode = process.env.AI_MODE === 'mock' ? 'mock' : 'real';
  if (!gw || mode === 'mock') {
    return {
      reachable: mode === 'mock',
      status: mode === 'mock' ? 200 : null,
      upstream: mode === 'mock' ? '127.0.0.1:8101' : null,
      server: mode === 'mock' ? 'mock-gpu0-8101' : null,
      mode: mode === 'mock' ? 'mock' : null,
      max_batch: 1,
      max_wait_ms: 0,
      device: mode === 'mock' ? 'mock' : null,
      queue_len: 0,
      latency_ms: 1.2,
    };
  }
  const t0 = performance.now();
  try {
    const url = new URL('/health', gw);
    const res = await fetch(url, { signal: AbortSignal.timeout(3000), cache: 'no-store' });
    const latency_ms = Math.round((performance.now() - t0) * 10) / 10;
    const body = (await res.json().catch(() => null)) as Record<string, unknown> | null;
    return {
      reachable: res.ok,
      status: res.status,
      upstream: res.headers.get('x-upstream'),
      server: typeof body?.server === 'string' ? body.server : null,
      mode: typeof body?.mode === 'string' ? body.mode : null,
      max_batch: typeof body?.max_batch === 'number' ? body.max_batch : null,
      max_wait_ms: typeof body?.max_wait_ms === 'number' ? body.max_wait_ms : null,
      device: typeof body?.device === 'string' ? body.device : null,
      queue_len: typeof body?.queue_len === 'number' ? body.queue_len : null,
      latency_ms,
    };
  } catch {
    return {
      reachable: false,
      status: null,
      upstream: null,
      server: null,
      mode: null,
      max_batch: null,
      max_wait_ms: null,
      device: null,
      queue_len: null,
      latency_ms: null,
    };
  }
}

export async function GET(req: NextRequest) {
  try {
    const a = await requireAccess(req, 'telemetry.view');
    if (a.res) return a.res;

    const [disp, upstream, byServer, summary, recent] = await Promise.all([
      readDispatcherState(pool()),
      probeUpstream(),
      pool().query<{
        lb_server: string;
        lb_upstream: string | null;
        photos: number;
        avg_batch: number;
        max_batch: number;
        avg_queue_ms: number;
        avg_model_ms: number;
      }>(
        `SELECT COALESCE(lb_server, 'unknown') AS lb_server,
                MAX(lb_upstream) AS lb_upstream,
                count(*)::int AS photos,
                ROUND(AVG(COALESCE(lb_batch_size, 1))::numeric, 2)::float8 AS avg_batch,
                MAX(COALESCE(lb_batch_size, 1))::int AS max_batch,
                ROUND(AVG(COALESCE(lb_queue_ms, 0))::numeric, 2)::float8 AS avg_queue_ms,
                ROUND(AVG(COALESCE(lb_model_ms, 0))::numeric, 2)::float8 AS avg_model_ms
           FROM photos
          WHERE status = 'DONE' AND lb_server IS NOT NULL
          GROUP BY lb_server
          ORDER BY lb_server`,
      ),
      pool().query<{
        live_photos: number;
        avg_batch: number | null;
        max_batch: number | null;
        avg_queue_ms: number | null;
        avg_model_ms: number | null;
        gpu0_count: number;
        gpu1_count: number;
      }>(
        `SELECT count(*)::int AS live_photos,
                ROUND(AVG(lb_batch_size)::numeric, 2)::float8 AS avg_batch,
                MAX(lb_batch_size)::int AS max_batch,
                ROUND(AVG(lb_queue_ms)::numeric, 2)::float8 AS avg_queue_ms,
                ROUND(AVG(lb_model_ms)::numeric, 2)::float8 AS avg_model_ms,
                (count(*) FILTER (WHERE lb_server LIKE 'gpu0%'))::int AS gpu0_count,
                (count(*) FILTER (WHERE lb_server LIKE 'gpu1%'))::int AS gpu1_count
           FROM photos
          WHERE status = 'DONE' AND lb_server IS NOT NULL`,
      ),
      pool().query<{
        id: string;
        original_filename: string;
        current_result: string | null;
        lb_server: string;
        lb_upstream: string | null;
        lb_batch_size: number | null;
        lb_queue_ms: string | null;
        lb_model_ms: string | null;
        finished_at: Date | null;
      }>(
        `SELECT id, original_filename, current_result, lb_server, lb_upstream,
                lb_batch_size, lb_queue_ms, lb_model_ms, finished_at
           FROM photos
          WHERE status = 'DONE' AND lb_server IS NOT NULL
          ORDER BY finished_at DESC NULLS LAST
          LIMIT 16`,
      ),
    ]);

    let benchmarks: unknown = null;
    try {
      const p = path.join(process.cwd(), 'public', 'data', 'lab6-benchmarks.json');
      benchmarks = JSON.parse(await fs.readFile(p, 'utf8'));
    } catch {
      benchmarks = null;
    }

    return json({
      ai_mode: process.env.AI_MODE === 'mock' ? 'mock' : 'real',
      protocol: process.env.GATEWAY_PROTOCOL ?? 'lab6',
      concurrency: Number(process.env.DISPATCH_CONCURRENCY ?? 16),
      dispatcher: disp.dispatcher,
      gateway: disp.gateway,
      upstream,
      live: summary.rows[0],
      by_server: byServer.rows,
      recent: recent.rows.map((r) => ({
        ...r,
        lb_queue_ms: r.lb_queue_ms === null ? null : Number(r.lb_queue_ms),
        lb_model_ms: r.lb_model_ms === null ? null : Number(r.lb_model_ms),
      })),
      benchmarks,
    });
  } catch (e) {
    return serverError('telemetry GET', e);
  }
}
