'use client';

// List of photos from GET /api/photos (FR-11, FR-12).
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState, type FormEvent } from 'react';
import type { PhotoStatus, Result } from '@/lib/rules';

export type Filters = { date: string; site: string; result: string; status: string; page: number };
export type Option = { value: string; label: string };

type ListPhoto = {
  id: string;
  site: { code: string; name: string };
  upload_date: string;
  original_filename: string;
  status: PhotoStatus;
  status_label: string;
  fail_reason: string | null;
  h: number | null;
  v: number | null;
  current_result: Result | null;
  current_result_label: string | null;
  is_overridden: boolean;
  lb_server?: string | null;
  lb_batch_size?: number | null;
  lb_model_ms?: number | null;
  accepted_at: string;
};

type ListResponse = {
  page: number;
  page_size: number;
  total: number;
  pages: number;
  counts: { pass: number; warn: number; fail: number };
  photos: ListPhoto[];
};

function toQuery(f: Filters, mode: 'all' | 'problems'): URLSearchParams {
  const q = new URLSearchParams();
  if (f.date) q.set('date', f.date);
  if (f.site) q.set('site', f.site);
  if (mode === 'all' && f.result) q.set('result', f.result);
  if (mode === 'all' && f.status) q.set('status', f.status);
  if (f.page > 1) q.set('page', String(f.page));
  return q;
}

export default function PhotoList({
  mode,
  initial,
  sites,
  resultOptions,
  statusOptions,
  resultLabels,
}: {
  mode: 'all' | 'problems';
  initial: Filters;
  sites: Option[];
  resultOptions: Option[];
  statusOptions: Option[];
  resultLabels: Record<Result, string>;
}) {
  const router = useRouter();
  const basePath = mode === 'problems' ? '/photos/problems' : '/photos';
  const prefix = mode === 'problems' ? 'problems' : 'photos';
  const [form, setForm] = useState<Filters>(initial);
  const [data, setData] = useState<ListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    const q = toQuery(initial, mode);
    if (mode === 'problems') q.set('problems', '1');
    (async () => {
      try {
        const res = await fetch(`/api/photos?${q.toString()}`, { cache: 'no-store', credentials: 'same-origin' });
        if (!alive) return;
        if (res.status === 401) {
          window.location.assign('/login');
          return;
        }
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as { message?: string } | null;
          setError(body?.message ?? `โหลดรายการไม่สำเร็จ (รหัส ${res.status})`);
          setData(null);
        } else {
          setData((await res.json()) as ListResponse);
          setError(null);
        }
      } catch {
        if (alive) setError('เชื่อมต่อระบบไม่ได้ กรุณาลองใหม่');
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [initial, mode]);

  function go(f: Filters) {
    const qs = toQuery(f, mode).toString();
    router.push(qs ? `${basePath}?${qs}` : basePath);
  }

  function onApply(e: FormEvent) {
    e.preventDefault();
    go({ ...form, page: 1 });
  }

  const page = data?.page ?? initial.page;
  const pages = data?.pages ?? 1;

  return (
    <div className="space-y-4">
      <form className="card flex flex-wrap items-end gap-4" onSubmit={onApply}>
        <label className="flex flex-col gap-1 text-xs font-semibold text-slate-600">
          วันที่อัปโหลด
          <input
            type="date"
            data-testid={`${prefix}-filter-date`}
            value={form.date}
            onChange={(e) => setForm({ ...form, date: e.target.value })}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-slate-600">
          ไซต์
          <select
            data-testid={`${prefix}-filter-site`}
            value={form.site}
            onChange={(e) => setForm({ ...form, site: e.target.value })}
          >
            {sites.length > 1 && <option value="">ทุกไซต์</option>}
            {sites.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        {mode === 'all' && (
          <>
            <label className="flex flex-col gap-1 text-xs font-semibold text-slate-600">
              ผล
              <select
                data-testid="photos-filter-result"
                value={form.result}
                onChange={(e) => setForm({ ...form, result: e.target.value })}
              >
                <option value="">ทุกผล</option>
                {resultOptions.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs font-semibold text-slate-600">
              สถานะ
              <select
                data-testid="photos-filter-status"
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              >
                <option value="">ทุกสถานะ</option>
                {statusOptions.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          </>
        )}
        <button type="submit" data-testid={`${prefix}-filter-apply`}>
          กรองข้อมูล
        </button>
      </form>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs font-medium text-slate-500">
            {mode === 'problems' ? 'รูปที่มีปัญหาทั้งหมด' : 'จำนวนรูปทั้งหมด'}
          </div>
          <span className="mt-1 block text-2xl font-bold text-slate-900 tabular-nums" data-testid={`${prefix}-total-count`}>
            {data ? data.total : '–'}
          </span>
        </div>
        {mode === 'problems' ? (
          <>
            <div className="rounded-2xl border border-red-200 bg-red-50/70 p-4 shadow-sm result-FAIL">
              <div className="text-xs font-medium text-red-700">{resultLabels.FAIL}</div>
              <span className="mt-1 block text-2xl font-bold tabular-nums" data-testid="problems-count-fail">
                {data ? data.counts.fail : '–'}
              </span>
            </div>
            <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-4 shadow-sm result-WARN">
              <div className="text-xs font-medium text-amber-700">{resultLabels.WARN}</div>
              <span className="mt-1 block text-2xl font-bold tabular-nums" data-testid="problems-count-warn">
                {data ? data.counts.warn : '–'}
              </span>
            </div>
          </>
        ) : (
          <>
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-4 shadow-sm result-PASS">
              <div className="text-xs font-medium text-emerald-700">{resultLabels.PASS}</div>
              <span className="mt-1 block text-2xl font-bold tabular-nums">{data ? data.counts.pass : '–'}</span>
            </div>
            <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-4 shadow-sm result-WARN">
              <div className="text-xs font-medium text-amber-700">{resultLabels.WARN}</div>
              <span className="mt-1 block text-2xl font-bold tabular-nums">{data ? data.counts.warn : '–'}</span>
            </div>
            <div className="rounded-2xl border border-red-200 bg-red-50/70 p-4 shadow-sm result-FAIL">
              <div className="text-xs font-medium text-red-700">{resultLabels.FAIL}</div>
              <span className="mt-1 block text-2xl font-bold tabular-nums">{data ? data.counts.fail : '–'}</span>
            </div>
          </>
        )}
      </div>

      {error && (
        <p className="error" role="alert" data-testid={`${prefix}-error`}>
          {error}
        </p>
      )}
      {loading && <p className="muted text-sm">กำลังโหลดรายการ…</p>}

      {!loading && data && (
        <>
          <div className="overflow-x-auto">
            <table className="data">
              <thead>
                <tr>
                  <th>วันที่</th>
                  <th>ไซต์</th>
                  <th>ไฟล์</th>
                  <th>สถานะ</th>
                  <th>ผลล่าสุด</th>
                  <th className="num">H</th>
                  <th className="num">V</th>
                  <th>GPU / Batch</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.photos.length === 0 && (
                  <tr>
                    <td colSpan={9} className="text-center text-slate-500 py-8" data-testid={`${prefix}-empty`}>
                      ไม่พบรูปตามเงื่อนไขที่เลือก
                    </td>
                  </tr>
                )}
                {data.photos.map((p) => (
                  <tr
                    key={p.id}
                    data-testid={`${prefix}-row-${p.id}`}
                    data-site={p.site.code}
                    data-status={p.status}
                    data-result={p.current_result ?? ''}
                  >
                    <td className="font-mono text-xs text-slate-600">{p.upload_date}</td>
                    <td className="font-medium text-slate-800">{p.site.name}</td>
                    <td className="break-all max-w-xs text-slate-700">{p.original_filename}</td>
                    <td className={`status-${p.status}`} data-testid={`${prefix}-row-status-${p.id}`}>
                      {p.status_label}
                      {p.fail_reason && <div className="text-xs text-red-600 font-normal">{p.fail_reason}</div>}
                    </td>
                    <td>
                      <span
                        className={p.current_result ? `result-${p.current_result}` : 'muted'}
                        data-testid={`${prefix}-row-result-${p.id}`}
                        data-result={p.current_result ?? ''}
                      >
                        {p.current_result_label ?? '–'}
                      </span>
                      {p.is_overridden && <span className="badge edited ml-1.5">แก้ผลแล้ว</span>}
                    </td>
                    <td className="num font-semibold">{p.h ?? '–'}</td>
                    <td className="num font-semibold">{p.v ?? '–'}</td>
                    <td>
                      {p.lb_server ? (
                        <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 font-mono text-[11px] text-slate-700">
                          {p.lb_server}
                          {p.lb_batch_size ? ` · b=${p.lb_batch_size}` : ''}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">–</span>
                      )}
                    </td>
                    <td>
                      <Link
                        href={`/photos/${p.id}`}
                        data-testid={`${prefix}-open-photo-${p.id}`}
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

          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              className="secondary"
              data-testid={`${prefix}-prev-page`}
              disabled={page <= 1}
              onClick={() => go({ ...initial, page: page - 1 })}
            >
              ← ก่อนหน้า
            </button>
            <span className="text-sm text-slate-600 font-medium" data-testid={`${prefix}-page-info`}>
              หน้า {page} / {pages}
            </span>
            <button
              type="button"
              className="secondary"
              data-testid={`${prefix}-next-page`}
              disabled={page >= pages}
              onClick={() => go({ ...initial, page: page + 1 })}
            >
              ถัดไป →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
