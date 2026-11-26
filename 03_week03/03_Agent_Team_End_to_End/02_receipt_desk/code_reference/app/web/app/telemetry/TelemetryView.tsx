'use client';
/**
 * LAB 7 vLLM Serving Telemetry Dashboard
 * Shows live NGINX least_conn + 2x RTX 4090 Data Parallelism replica health
 * and measured LAB 7 benchmark results.
 */
import { useCallback, useEffect, useState } from 'react';
import { api, errorText } from '../_ui/api';

interface BenchRow {
  config: string;
  gpus: number;
  cap: number;
  stdUsers: number | string;
  fastUsers: number | string;
  peakTps: number | string;
  ttftP95: string;
  efficiency: string;
}

interface TelemetryData {
  cluster: {
    mode: string;
    reachable: boolean;
    strategy: string;
    pool: string;
    proxyBuffering: string;
    observedReplicas: string[];
    probeLatencyMs: number | null;
    model: string;
    hardware: string;
  };
  benchmarks: {
    measuredOn?: string;
    model?: string;
    n1SpeedTps?: number;
    n1TtftMs?: number;
    scalingEfficiencyPct?: number;
    ocrDp1Rpm?: number;
    ocrDp2Rpm?: number;
    ocrSpeedup?: number;
    mixBalance?: { gpu0Pct: number; gpu1Pct: number };
    failoverErrorsAfterCut?: number;
    table?: BenchRow[];
  } | null;
}

export default function TelemetryView() {
  const [data, setData] = useState<TelemetryData | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    const r = await api<TelemetryData>('/api/telemetry');
    if (r.ok) {
      setData(r.data);
      setErr(null);
    } else {
      setErr(errorText(r.error));
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 10_000);
    return () => clearInterval(t);
  }, [load]);

  const c = data?.cluster;
  const b = data?.benchmarks;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="!mb-1">LAB 7 vLLM Serving Telemetry</h1>
          <p className="muted m-0 text-sm">
            สถาปัตยกรรมที่ดีที่สุดจาก LAB 7: 1 vLLM Replica ต่อ 1 GPU (Data Parallelism 2×1) + Continuous Batching + NGINX <code className="font-semibold">least_conn</code> (<code className="font-semibold">proxy_buffering off</code>)
          </p>
        </div>
        <button type="button" className="secondary" onClick={load}>
          รีเฟรชสถานะคลัสเตอร์
        </button>
      </div>

      {err ? <div className="notice error">{err}</div> : null}

      <div className="stats">
        <div className="stat">
          <div className="label">สถานะคลัสเตอร์ NGINX + vLLM</div>
          <div className="value flex items-center gap-2" data-testid="telemetry-cluster-status">
            <span className={`w-3 h-3 rounded-full ${c?.reachable ? 'bg-emerald-500' : 'bg-amber-500'}`} />
            <span>{c ? (c.reachable ? 'ONLINE' : 'STANDBY') : '…'}</span>
          </div>
          <div className="text-xs text-slate-500 mt-1">
            โหมด: {c?.mode ?? '…'} · Strategy: {c?.strategy ?? 'least_conn'} · Buffering: {c?.proxyBuffering ?? 'off'}
          </div>
        </div>

        <div className="stat" style={{ borderTopColor: '#4338ca' }}>
          <div className="label">Active GPU Replicas (X-Replica)</div>
          <div className="value flex items-center gap-2 flex-wrap" data-testid="telemetry-replicas">
            {(c?.observedReplicas ?? ['gpu0', 'gpu1']).map((rep) => (
              <span key={rep} className="badge live !text-sm !px-3 !py-1">
                ● {rep}
              </span>
            ))}
          </div>
          <div className="text-xs text-slate-500 mt-1">{c?.hardware ?? '2× RTX 4090 (24 GB)'}</div>
        </div>

        <div className="stat" style={{ borderTopColor: '#d97706' }}>
          <div className="label">Data Parallelism Scaling Efficiency</div>
          <div className="value">{b?.scalingEfficiencyPct ? `${b.scalingEfficiencyPct}%` : '—'}</div>
          <div className="text-xs text-slate-500 mt-1">
            Receipt OCR Speedup: {b?.ocrSpeedup ? `${b.ocrSpeedup}×` : '—'} ({b?.ocrDp1Rpm ?? '—'} → {b?.ocrDp2Rpm ?? '—'} ใบ/นาที)
          </div>
        </div>

        <div className="stat" style={{ borderTopColor: '#0284c7' }}>
          <div className="label">Failover &amp; least_conn Balance</div>
          <div className="value">
            {b?.mixBalance ? `${b.mixBalance.gpu0Pct}% / ${b.mixBalance.gpu1Pct}%` : '—'}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Errors หลังปิด gpu1 กลางสตรีม: {b?.failoverErrorsAfterCut ?? 0} ครั้ง
          </div>
        </div>
      </div>

      <section className="card">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-bold m-0 text-slate-900">
            ผลวัดจริงบน 2× RTX 4090 · โมเดล Qwen3-VL-2B-Instruct + LoRA (receipt-vlm)
          </h2>
          <span className="badge">{b?.measuredOn ?? 'Vast.ai 2× RTX 4090'}</span>
        </div>
        <table data-testid="telemetry-bench-table">
          <thead>
            <tr>
              <th>การตั้งค่า (LAB 7)</th>
              <th className="num">GPU</th>
              <th className="num">Max Seqs</th>
              <th className="num">Standard SLO (ผู้ใช้)</th>
              <th className="num">Fast SLO (ผู้ใช้)</th>
              <th className="num">Peak Throughput (tok/s)</th>
              <th className="num">TTFT p95</th>
              <th className="num">Scaling Efficiency</th>
            </tr>
          </thead>
          <tbody>
            {b?.table?.length ? (
              b.table.map((row) => (
                <tr key={row.config}>
                  <td className="font-semibold text-slate-900">{row.config}</td>
                  <td className="num">{row.gpus}</td>
                  <td className="num">{row.cap}</td>
                  <td className="num font-bold text-emerald-700">{row.stdUsers}</td>
                  <td className="num">{row.fastUsers}</td>
                  <td className="num font-bold text-indigo-700">{row.peakTps}</td>
                  <td className="num">{row.ttftP95}</td>
                  <td className="num">{row.efficiency}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={8} className="muted">
                  กำลังรอไฟล์สรุปผลวัดจริง (public/data/lb_summary.json)
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
