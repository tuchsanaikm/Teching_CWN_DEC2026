'use client';

// Polls GET /api/uploads/{batchId} every 1.5 seconds while the page is open.
import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import type { PhotoStatus, Result } from '@/lib/rules';

const POLL_MS = 1500;

type BatchPhoto = {
  id: string;
  original_filename: string;
  status: PhotoStatus;
  status_label: string;
  fail_reason: string | null;
  h: number | null;
  v: number | null;
  current_result: Result | null;
  current_result_label: string | null;
  is_overridden: boolean;
  lb_upstream?: string | null;
  lb_server?: string | null;
  lb_batch_size?: number | null;
  lb_queue_ms?: number | null;
  lb_model_ms?: number | null;
};

type BatchResponse = {
  batch: {
    id: string;
    site: { code: string; name: string };
    declared_count: number;
    created_at: string;
    uploaded_by: { full_name: string };
  };
  accepted_count: number;
  counts: { queued: number; processing: number; done: number; failed: number };
  photos: BatchPhoto[];
};

export default function BatchStatus({
  batchId,
  statusLabels,
}: {
  batchId: string;
  statusLabels: Record<PhotoStatus, string>;
}) {
  const [data, setData] = useState<BatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const inFlight = useRef(false);

  const load = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const res = await fetch(`/api/uploads/${encodeURIComponent(batchId)}`, {
        cache: 'no-store',
        credentials: 'same-origin',
      });
      if (res.status === 401) {
        window.location.assign('/login');
        return;
      }
      if (res.status === 404) {
        setNotFound(true);
        return;
      }
      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as { message?: string } | null;
        setError(body?.message ?? `โหลดสถานะไม่สำเร็จ (รหัส ${res.status})`);
        return;
      }
      setData((await res.json()) as BatchResponse);
      setError(null);
      setUpdatedAt(new Date());
    } catch {
      setError('เชื่อมต่อระบบไม่ได้ จะลองใหม่อัตโนมัติ');
    } finally {
      inFlight.current = false;
    }
  }, [batchId]);

  useEffect(() => {
    void load();
    const t = window.setInterval(() => void load(), POLL_MS);
    return () => window.clearInterval(t);
  }, [load]);

  if (notFound) {
    return (
      <div className="card text-center py-8 text-slate-600" data-testid="batch-not-found">
        ไม่พบการอัปโหลดนี้ หรือบัญชีนี้ไม่มีสิทธิ์เห็นข้อมูลนี้
      </div>
    );
  }

  const c = data?.counts ?? { queued: 0, processing: 0, done: 0, failed: 0 };
  const total = data?.accepted_count ?? 0;
  const donePct = total > 0 ? Math.round(((c.done + c.failed) / total) * 100) : 0;

  return (
    <div className="space-y-5">
      <div className="card space-y-4">
        {data && (
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-slate-600 border-b border-slate-100 pb-3">
            <div>
              ไซต์ <strong className="text-slate-900">{data.batch.site.name}</strong> · ผู้อัปโหลด{' '}
              <strong className="text-slate-900">{data.batch.uploaded_by.full_name}</strong> · แจ้งจำนวนไว้{' '}
              <strong>{data.batch.declared_count}</strong> รูป
            </div>
            <div className="text-xs font-semibold text-cyan-700 bg-cyan-50 border border-cyan-200 rounded-full px-3 py-1">
              ความคืบหน้า {donePct}%
            </div>
          </div>
        )}

        <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-gradient-to-r from-sky-500 to-emerald-500 transition-all duration-500"
            style={{ width: `${donePct}%` }}
          />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
            <div className="text-xs font-medium text-slate-500">รูปที่ระบบรับแล้ว</div>
            <span className="mt-1 block text-2xl font-bold text-slate-900 tabular-nums" data-testid="batch-accepted-count">
              {data ? data.accepted_count : '–'}
            </span>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-3.5 status-QUEUED">
            <div className="text-xs font-medium text-slate-500">{statusLabels.QUEUED}</div>
            <span className="mt-1 block text-2xl font-bold tabular-nums" data-testid="batch-count-queued">{c.queued}</span>
          </div>
          <div className="rounded-xl border border-sky-200 bg-sky-50/60 p-3.5 status-PROCESSING">
            <div className="text-xs font-medium text-sky-700">{statusLabels.PROCESSING}</div>
            <span className="mt-1 block text-2xl font-bold tabular-nums" data-testid="batch-count-processing">{c.processing}</span>
          </div>
          <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-3.5 status-DONE">
            <div className="text-xs font-medium text-emerald-700">{statusLabels.DONE}</div>
            <span className="mt-1 block text-2xl font-bold tabular-nums" data-testid="batch-count-done">{c.done}</span>
          </div>
          <div className="rounded-xl border border-red-200 bg-red-50/60 p-3.5 status-FAILED">
            <div className="text-xs font-medium text-red-700">{statusLabels.FAILED}</div>
            <span className="mt-1 block text-2xl font-bold tabular-nums" data-testid="batch-count-failed">{c.failed}</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-1">
          <button type="button" className="secondary" data-testid="batch-refresh" onClick={() => void load()}>
            โหลดใหม่
          </button>
          <span className="text-xs text-slate-500">
            อัปเดตอัตโนมัติทุก 1.5 วินาที
            {updatedAt && ` · ล่าสุด ${updatedAt.toLocaleTimeString('th-TH', { timeZone: 'Asia/Bangkok' })}`}
          </span>
        </div>
        {error && (
          <p className="error" role="alert" data-testid="batch-error">
            {error}
          </p>
        )}
      </div>

      {data && (
        <div className="overflow-x-auto">
          <table className="data">
            <thead>
              <tr>
                <th>#</th>
                <th>ไฟล์</th>
                <th>สถานะ</th>
                <th>ผล</th>
                <th className="num">H</th>
                <th className="num">V</th>
                <th>LAB 6 GPU / Micro-batch</th>
                <th>เหตุผล</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data.photos.length === 0 && (
                <tr>
                  <td colSpan={9} className="text-center text-slate-500 py-8">
                    ยังไม่มีรูปที่ระบบรับ
                  </td>
                </tr>
              )}
              {data.photos.map((p, i) => (
                <tr key={p.id} data-testid={`batch-row-${p.id}`} data-status={p.status}>
                  <td className="font-mono text-xs text-slate-400">{i + 1}</td>
                  <td className="font-medium text-slate-800 break-all max-w-xs">{p.original_filename}</td>
                  <td className={`status-${p.status}`} data-testid={`batch-row-status-${p.id}`} data-status={p.status}>
                    {p.status_label}
                  </td>
                  <td>
                    <span
                      className={p.current_result ? `result-${p.current_result}` : 'muted'}
                      data-testid={`batch-row-result-${p.id}`}
                      data-result={p.current_result ?? ''}
                    >
                      {p.current_result_label ?? '–'}
                    </span>
                    {p.is_overridden && (
                      <span className="badge edited ml-1.5">
                        แก้ผลแล้ว
                      </span>
                    )}
                  </td>
                  <td className="num font-semibold">{p.h ?? '–'}</td>
                  <td className="num font-semibold">{p.v ?? '–'}</td>
                  <td>
                    {p.lb_server ? (
                      <div className="flex flex-wrap items-center gap-1 text-[11px] font-mono">
                        <span
                          className={`rounded-md px-2 py-0.5 font-semibold ${
                            p.lb_server.startsWith('gpu1')
                              ? 'bg-violet-100 text-violet-800 border border-violet-200'
                              : 'bg-cyan-100 text-cyan-800 border border-cyan-200'
                          }`}
                          data-testid={`batch-row-gpu-${p.id}`}
                        >
                          {p.lb_server}
                        </span>
                        {p.lb_batch_size !== null && p.lb_batch_size !== undefined && (
                          <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-slate-700">
                            b={p.lb_batch_size}
                          </span>
                        )}
                        {p.lb_model_ms !== null && p.lb_model_ms !== undefined && (
                          <span className="rounded-md bg-emerald-50 px-1.5 py-0.5 text-emerald-700">
                            {p.lb_model_ms.toFixed(1)}ms
                          </span>
                        )}
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400">–</span>
                    )}
                  </td>
                  <td className="text-xs text-red-600" data-testid={`batch-row-reason-${p.id}`}>{p.fail_reason ?? ''}</td>
                  <td>
                    <Link
                      href={`/photos/${p.id}`}
                      data-testid={`batch-open-photo-${p.id}`}
                      className="inline-flex items-center rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-sky-700 no-underline hover:bg-sky-100 transition"
                    >
                      เปิดรูป →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
