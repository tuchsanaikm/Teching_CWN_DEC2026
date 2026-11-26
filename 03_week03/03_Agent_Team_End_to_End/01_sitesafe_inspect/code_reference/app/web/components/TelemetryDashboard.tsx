'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';

type TelemetryData = {
  ai_mode: 'real' | 'mock';
  protocol: string;
  concurrency: number;
  dispatcher: 'ok' | 'down';
  gateway: 'ok' | 'down' | 'unauthorized';
  upstream: {
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
  live: {
    live_photos: number;
    avg_batch: number | null;
    max_batch: number | null;
    avg_queue_ms: number | null;
    avg_model_ms: number | null;
    gpu0_count: number;
    gpu1_count: number;
  };
  by_server: Array<{
    lb_server: string;
    lb_upstream: string | null;
    photos: number;
    avg_batch: number;
    max_batch: number;
    avg_queue_ms: number;
    avg_model_ms: number;
  }>;
  recent: Array<{
    id: string;
    original_filename: string;
    current_result: string | null;
    lb_server: string;
    lb_upstream: string | null;
    lb_batch_size: number | null;
    lb_queue_ms: number | null;
    lb_model_ms: number | null;
    finished_at: string | null;
  }>;
  benchmarks: {
    machine?: string;
    designs?: Array<{
      id: string;
      label: string;
      capacity: number;
      max_rps: number;
      p95_at_cap_ms: number;
      gpu_util_pct: string;
    }>;
    slow_gpu?: {
      rr_capacity: number;
      lc_capacity: number;
      rr_rps: number;
      lc_rps: number;
    };
    failover?: {
      off_errors: number;
      off_error_pct: number;
      on_errors: number;
      on_error_pct: number;
    };
  } | null;
};

export default function TelemetryDashboard() {
  const [data, setData] = useState<TelemetryData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/telemetry', { cache: 'no-store', credentials: 'same-origin' });
      if (res.status === 401) {
        window.location.assign('/login');
        return;
      }
      if (!res.ok) {
        setError(`โหลด Telemetry ไม่สำเร็จ (${res.status})`);
        return;
      }
      setData((await res.json()) as TelemetryData);
      setError(null);
    } catch {
      setError('เชื่อมต่อ Telemetry API ไม่ได้');
    }
  }, []);

  useEffect(() => {
    void load();
    const t = window.setInterval(() => void load(), 3000);
    return () => window.clearInterval(t);
  }, [load]);

  const maxCap = Math.max(1, ...(data?.benchmarks?.designs?.map((d) => d.capacity) ?? [1]));
  const totalGpuPhotos = Math.max(1, (data?.live.gpu0_count ?? 0) + (data?.live.gpu1_count ?? 0));
  const gpu0Pct = Math.round(((data?.live.gpu0_count ?? 0) / totalGpuPhotos) * 100);
  const gpu1Pct = 100 - gpu0Pct;

  return (
    <div className="space-y-6" data-testid="telemetry-dashboard">
      <section className="rounded-3xl bg-navy-950 text-white p-6 sm:p-8 shadow-xl border border-slate-800 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-500/15 px-3 py-1 text-xs font-semibold text-cyan-300 mb-2">
              <span className={`h-2 w-2 rounded-full ${data?.upstream.reachable ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
              LAB 6 Multi-GPU Serving Architecture · NGINX Least Connections + 8× FastAPI Micro-batch
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white m-0">
              GPU Load Balancer &amp; Micro-batching Telemetry
            </h1>
            <p className="text-sm text-slate-300 mt-1 m-0">
              ติดตามการกระจายโหลดแบบเรียลไทม์บนเครื่อง 2× RTX 4090 พร้อมผล Benchmark จริงจากห้องปฏิบัติการ LAB 6
            </p>
          </div>
          <button
            type="button"
            className="secondary bg-slate-900 border-slate-700 text-slate-200 hover:bg-slate-800"
            data-testid="telemetry-refresh"
            onClick={() => void load()}
          >
            รีเฟรชสด
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-xs text-slate-400">NGINX Upstream Status</div>
            <div className="mt-1 flex items-center gap-2">
              <span
                className={`text-lg font-bold ${data?.upstream.reachable ? 'text-emerald-400' : 'text-red-400'}`}
                data-testid="telemetry-upstream-status"
              >
                {data?.upstream.reachable ? 'ONLINE' : 'OFFLINE'}
              </span>
              {data?.upstream.latency_ms !== null && data?.upstream.latency_ms !== undefined && (
                <span className="text-xs font-mono text-slate-400">{data.upstream.latency_ms}ms</span>
              )}
            </div>
            <div className="text-[11px] font-mono text-cyan-300 mt-1" data-testid="telemetry-upstream-addr">
              {data?.upstream.server ?? '–'} ({data?.upstream.upstream ?? '–'})
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-xs text-slate-400">Live GPU Inference</div>
            <div className="mt-1 text-2xl font-bold text-white tabular-nums" data-testid="telemetry-live-photos">
              {data?.live.live_photos ?? 0} <span className="text-xs font-normal text-slate-400">รูป</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              GPU0: <strong className="text-cyan-300">{data?.live.gpu0_count ?? 0}</strong> · GPU1:{' '}
              <strong className="text-violet-300">{data?.live.gpu1_count ?? 0}</strong>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-xs text-slate-400">Avg / Max Micro-batch</div>
            <div className="mt-1 text-2xl font-bold text-amber-300 tabular-nums" data-testid="telemetry-avg-batch">
              {data?.live.avg_batch ?? '–'}{' '}
              <span className="text-xs font-normal text-slate-400">/ max {data?.live.max_batch ?? '–'}</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Dispatcher Concurrency: {data?.concurrency ?? 16}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-xs text-slate-400">Avg YOLO11s Model / Queue</div>
            <div className="mt-1 text-2xl font-bold text-emerald-300 tabular-nums" data-testid="telemetry-avg-model-ms">
              {data?.live.avg_model_ms !== null && data?.live.avg_model_ms !== undefined
                ? `${data.live.avg_model_ms.toFixed(1)} ms`
                : '–'}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Queue avg: {data?.live.avg_queue_ms !== null && data?.live.avg_queue_ms !== undefined ? `${data.live.avg_queue_ms.toFixed(1)} ms` : '–'}
            </div>
          </div>
        </div>
      </section>

      {error && <p className="error">{error}</p>}

      {data?.benchmarks?.designs && (
        <section className="card space-y-4" data-testid="telemetry-benchmarks">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-lg font-bold text-slate-900 m-0">
                ผล Benchmark จริงบนเครื่อง {data.benchmarks.machine ?? '2× RTX 4090'} (LAB 6)
              </h2>
              <p className="text-xs text-slate-500 mt-0.5 m-0">
                เกณฑ์ผ่าน: p95 ≤ 500 ms และ Error &lt; 1% · เทียบ 4 สถาปัตยกรรมตั้งแต่ 1 process เดี่ยว จนถึง 2× RTX 4090 + NGINX least_conn
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.benchmarks.designs.map((d, idx) => {
              const pct = Math.max(8, Math.round((d.capacity / maxCap) * 100));
              const isWinner = idx === data.benchmarks!.designs!.length - 1;
              return (
                <div
                  key={d.id}
                  className={`rounded-2xl border p-4 space-y-2.5 ${
                    isWinner
                      ? 'border-cyan-400 bg-gradient-to-br from-navy-950 to-navy-800 text-white shadow-md'
                      : 'border-slate-200 bg-slate-50/70 text-slate-900'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-bold">{d.label}</span>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
                        isWinner ? 'bg-cyan-400 text-slate-950' : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {d.capacity} users
                    </span>
                  </div>
                  <div className={`h-2.5 w-full overflow-hidden rounded-full ${isWinner ? 'bg-white/15' : 'bg-slate-200'}`}>
                    <div
                      className={`h-full rounded-full ${isWinner ? 'bg-gradient-to-r from-cyan-400 to-emerald-400' : 'bg-sky-500'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className={`flex flex-wrap justify-between text-xs ${isWinner ? 'text-slate-300' : 'text-slate-600'}`}>
                    <span>Max Throughput: <strong>{d.max_rps.toFixed(1)} req/s</strong></span>
                    <span>p95 @ cap: <strong>{d.p95_at_cap_ms.toFixed(0)} ms</strong></span>
                    <span>GPU: <strong>{d.gpu_util_pct}</strong></span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            {data.benchmarks.slow_gpu && (
              <div className="rounded-2xl border border-amber-200 bg-amber-50/60 p-4 space-y-1">
                <div className="text-xs font-bold uppercase tracking-wider text-amber-800">
                  GPU 1 ช้าลง 3 เท่า · Round Robin vs Least Connections
                </div>
                <div className="text-sm text-slate-800">
                  Round Robin รับได้ <strong>{data.benchmarks.slow_gpu.rr_capacity} users</strong> ({data.benchmarks.slow_gpu.rr_rps.toFixed(1)} req/s) ·
                  NGINX <code className="font-mono font-bold text-sky-700">least_conn</code> รับได้{' '}
                  <strong className="text-emerald-700">{data.benchmarks.slow_gpu.lc_capacity} users</strong> ({data.benchmarks.slow_gpu.lc_rps.toFixed(1)} req/s)
                </div>
              </div>
            )}
            {data.benchmarks.failover && (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-4 space-y-1">
                <div className="text-xs font-bold uppercase tracking-wider text-emerald-800">
                  ทดสอบฆ่า GPU 1 กลางทาง (SIGKILL) · Failover OFF vs ON
                </div>
                <div className="text-sm text-slate-800">
                  Failover OFF: <strong className="text-red-700">{data.benchmarks.failover.off_errors} errors ({data.benchmarks.failover.off_error_pct.toFixed(2)}%)</strong> ·
                  Failover ON: <strong className="text-emerald-700">{data.benchmarks.failover.on_errors} errors ({data.benchmarks.failover.on_error_pct.toFixed(2)}%)</strong>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <section className="lg:col-span-5 card space-y-4">
          <h2 className="text-base font-bold text-slate-900 m-0">การกระจายโหลดสดระหว่าง GPU 0 &amp; GPU 1</h2>
          {(data?.live.live_photos ?? 0) > 0 ? (
            <>
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-cyan-700">GPU 0 (RTX 4090): {data!.live.gpu0_count} รูป ({gpu0Pct}%)</span>
                  <span className="text-violet-700">GPU 1 (RTX 4090): {data!.live.gpu1_count} รูป ({gpu1Pct}%)</span>
                </div>
                <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-100">
                  <div className="bg-cyan-500 h-full" style={{ width: `${gpu0Pct}%` }} />
                  <div className="bg-violet-500 h-full" style={{ width: `${gpu1Pct}%` }} />
                </div>
              </div>
              <div className="space-y-2">
                {data!.by_server.map((s) => (
                  <div key={s.lb_server} className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50 px-3 py-2 text-xs">
                    <span className="font-mono font-bold text-slate-800">{s.lb_server}</span>
                    <span className="text-slate-600">
                      <strong>{s.photos}</strong> รูป · b={s.avg_batch} · {s.avg_model_ms}ms
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-500">
              ยังไม่มีรูปที่ตรวจผ่านคลัสเตอร์ในฐานข้อมูลรอบนี้ · ลองอัปโหลดรูปหน้างานเพื่อดูการกระจายโหลดข้าม 8 Worker แบบสด ๆ
            </p>
          )}
        </section>

        <section className="lg:col-span-7 card space-y-3">
          <h2 className="text-base font-bold text-slate-900 m-0">ประวัติคำขอ Inference ล่าสุดผ่าน NGINX</h2>
          <div className="overflow-x-auto">
            <table className="data">
              <thead>
                <tr>
                  <th>ไฟล์</th>
                  <th>Server (X-Upstream)</th>
                  <th className="num">Batch</th>
                  <th className="num">Queue</th>
                  <th className="num">Model</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {(!data || data.recent.length === 0) && (
                  <tr>
                    <td colSpan={6} className="text-center text-slate-500 py-6">
                      ยังไม่มีประวัติการตรวจสด
                    </td>
                  </tr>
                )}
                {data?.recent.map((r) => (
                  <tr key={r.id}>
                    <td className="text-xs font-medium text-slate-800 break-all max-w-[180px]">{r.original_filename}</td>
                    <td className="font-mono text-xs">
                      <span className={r.lb_server.startsWith('gpu1') ? 'text-violet-700 font-bold' : 'text-cyan-700 font-bold'}>
                        {r.lb_server}
                      </span>
                    </td>
                    <td className="num font-mono text-xs">{r.lb_batch_size ?? '–'}</td>
                    <td className="num font-mono text-xs">{r.lb_queue_ms !== null ? `${r.lb_queue_ms.toFixed(1)}ms` : '–'}</td>
                    <td className="num font-mono text-xs text-emerald-700 font-semibold">
                      {r.lb_model_ms !== null ? `${r.lb_model_ms.toFixed(1)}ms` : '–'}
                    </td>
                    <td>
                      <Link href={`/photos/${r.id}`} className="text-xs font-semibold text-sky-600 no-underline hover:underline">
                        ดู →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
