'use client';

// Detail of one photo from GET /api/photos/{id}; history from GET /api/photos/{id}/overrides;
// override through POST /api/photos/{id}/overrides + LAB 6 NGINX Load Balancer telemetry.

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState, type FormEvent } from 'react';
import type { PhotoStatus, Result } from '@/lib/rules';
import PhotoWithBoxes, { type Detection } from '@/components/PhotoWithBoxes';

type Option = { value: string; label: string };

type Photo = {
  id: string;
  site: { code: string; name: string };
  upload_date: string;
  original_filename: string;
  status: PhotoStatus;
  status_label: string;
  fail_reason: string | null;
  h: number | null;
  v: number | null;
  model_result: Result | null;
  model_result_label: string | null;
  current_result: Result | null;
  current_result_label: string | null;
  is_overridden: boolean;
  model_version: string | null;
  conf_threshold: number | null;
  image_w: number | null;
  image_h: number | null;
  lb_upstream: string | null;
  lb_server: string | null;
  lb_batch_size: number | null;
  lb_queue_ms: number | null;
  lb_model_ms: number | null;
  accepted_at: string;
  finished_at: string | null;
  image_url: string;
  detections: Detection[];
  override_count: number;
  can_override: boolean;
  can_view_history: boolean;
};

type Override = {
  id: number;
  edited_by: { full_name: string };
  edited_at: string;
  result_before: Result;
  result_before_label: string;
  result_after: Result;
  result_after_label: string;
  reason: string;
};

function thaiTime(iso: string | null): string {
  if (!iso) return '–';
  return new Date(iso).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok', dateStyle: 'medium', timeStyle: 'medium' });
}

async function messageOf(res: Response, fallback: string): Promise<string> {
  const body = (await res.json().catch(() => null)) as { message?: string } | null;
  return body?.message ?? `${fallback} (รหัส ${res.status})`;
}

export default function PhotoDetail({ photoId, resultOptions }: { photoId: string; resultOptions: Option[] }) {
  const router = useRouter();
  const [photo, setPhoto] = useState<Photo | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [history, setHistory] = useState<Override[] | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [result, setResult] = useState('');
  const [reason, setReason] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const base = `/api/photos/${encodeURIComponent(photoId)}`;

  const loadPhoto = useCallback(async () => {
    try {
      const res = await fetch(base, { cache: 'no-store', credentials: 'same-origin' });
      if (res.status === 401) {
        window.location.assign('/login');
        return;
      }
      if (!res.ok) {
        setLoadError(await messageOf(res, 'โหลดรูปไม่สำเร็จ'));
        return;
      }
      const body = (await res.json()) as { photo: Photo };
      setPhoto(body.photo);
      setLoadError(null);
    } catch {
      setLoadError('เชื่อมต่อระบบไม่ได้ กรุณาลองใหม่');
    }
  }, [base]);

  const loadHistory = useCallback(async () => {
    try {
      const res = await fetch(`${base}/overrides`, { cache: 'no-store', credentials: 'same-origin' });
      if (!res.ok) {
        setHistoryError(await messageOf(res, 'โหลดประวัติไม่สำเร็จ'));
        return;
      }
      const body = (await res.json()) as { overrides: Override[] };
      setHistory(body.overrides);
      setHistoryError(null);
    } catch {
      setHistoryError('เชื่อมต่อระบบไม่ได้ กรุณาลองใหม่');
    }
  }, [base]);

  useEffect(() => {
    void loadPhoto();
  }, [loadPhoto]);

  useEffect(() => {
    if (!photo || photo.status === 'DONE' || photo.status === 'FAILED') return;
    const t = window.setInterval(() => void loadPhoto(), 1500);
    return () => window.clearInterval(t);
  }, [photo, loadPhoto]);

  function toggleHistory() {
    const open = !historyOpen;
    setHistoryOpen(open);
    if (open) void loadHistory();
  }

  function resetForm() {
    setResult('');
    setReason('');
    setFormError(null);
    setSaved(false);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setFormError(null);
    setSaved(false);
    try {
      const res = await fetch(`${base}/overrides`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ result, reason }),
      });
      if (res.status === 201) {
        setResult('');
        setReason('');
        setSaved(true);
        await loadPhoto();
        if (historyOpen) await loadHistory();
        else setHistory(null);
        router.refresh();
      } else {
        setFormError(await messageOf(res, 'แก้ผลไม่สำเร็จ'));
      }
    } catch {
      setFormError('เชื่อมต่อระบบไม่ได้ กรุณาลองใหม่');
    }
    setSaving(false);
  }

  function back() {
    if (window.history.length > 1) router.back();
    else router.push('/photos');
  }

  const backButton = (
    <button type="button" className="secondary" data-testid="photo-back" onClick={back}>
      ← กลับ
    </button>
  );

  if (loadError && !photo) {
    return (
      <div className="card space-y-3">
        <p className="error" role="alert" data-testid="photo-error">
          {loadError}
        </p>
        {backButton}
      </div>
    );
  }
  if (!photo) {
    return (
      <div className="card space-y-3">
        <p className="muted">กำลังโหลด…</p>
        {backButton}
      </div>
    );
  }

  const violationCount = photo.detections.filter((d) => d.cls === 'NO_HARDHAT' || d.cls === 'NO_VEST').length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {backButton}
        {photo.lb_server && (
          <div className="inline-flex flex-wrap items-center gap-2 rounded-full border border-cyan-200 bg-navy-900 px-3.5 py-1.5 text-xs font-mono text-white shadow-sm">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            <span className="text-cyan-300 font-bold" data-testid="photo-lb-server">{photo.lb_server}</span>
            {photo.lb_upstream && <span className="text-slate-400" data-testid="photo-lb-upstream">({photo.lb_upstream})</span>}
            {photo.lb_batch_size !== null && (
              <span className="rounded bg-white/10 px-1.5 py-0.5 text-amber-300" data-testid="photo-lb-batch">
                batch={photo.lb_batch_size}
              </span>
            )}
            {photo.lb_model_ms !== null && (
              <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-emerald-300" data-testid="photo-lb-model-ms">
                model={photo.lb_model_ms.toFixed(1)}ms
              </span>
            )}
            {photo.lb_queue_ms !== null && (
              <span className="rounded bg-sky-500/20 px-1.5 py-0.5 text-sky-300" data-testid="photo-lb-queue-ms">
                queue={photo.lb_queue_ms.toFixed(1)}ms
              </span>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-7 card">
          <PhotoWithBoxes
            src={photo.image_url}
            alt={photo.original_filename}
            imageW={photo.image_w}
            imageH={photo.image_h}
            detections={photo.detections}
          />
          {photo.status === 'DONE' && violationCount === 0 && (
            <p className="mt-3 rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-2.5 text-sm font-medium text-emerald-800" data-testid="photo-no-box">
              ไม่พบคนที่ไม่ใส่หมวกหรือเสื้อสะท้อนแสง
            </p>
          )}
        </div>

        <div className="lg:col-span-5 space-y-5">
          <div className="card space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-base font-bold text-slate-900 m-0">ผลการตรวจ PPE</h2>
              <span
                className={`rounded-full px-3 py-1 text-xs font-bold ${
                  photo.current_result === 'PASS'
                    ? 'bg-emerald-100 text-emerald-800'
                    : photo.current_result === 'WARN'
                      ? 'bg-amber-100 text-amber-800'
                      : photo.current_result === 'FAIL'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-slate-100 text-slate-600'
                }`}
              >
                {photo.current_result_label ?? photo.status_label}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-red-100 bg-red-50/70 p-3">
                <div className="text-xs text-red-700 font-medium">ไม่ใส่หมวก (H)</div>
                <div className="text-2xl font-bold text-red-800 mt-0.5 tabular-nums" data-testid="photo-h">
                  {photo.h ?? '–'}
                </div>
              </div>
              <div className="rounded-xl border border-amber-100 bg-amber-50/70 p-3">
                <div className="text-xs text-amber-700 font-medium">ไม่ใส่เสื้อสะท้อนแสง (V)</div>
                <div className="text-2xl font-bold text-amber-800 mt-0.5 tabular-nums" data-testid="photo-v">
                  {photo.v ?? '–'}
                </div>
              </div>
            </div>

            <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2 text-sm m-0">
              <dt className="text-slate-500">ไฟล์</dt>
              <dd className="m-0 font-semibold text-slate-800 break-all">{photo.original_filename}</dd>
              <dt className="text-slate-500">ไซต์</dt>
              <dd className="m-0 font-semibold text-slate-800">{photo.site.name}</dd>
              <dt className="text-slate-500">วันที่อัปโหลด</dt>
              <dd className="m-0 font-semibold text-slate-800">{photo.upload_date}</dd>
              <dt className="text-slate-500">สถานะ</dt>
              <dd className={`m-0 status-${photo.status}`} data-testid="photo-status" data-status={photo.status}>
                {photo.status_label}
                {photo.fail_reason && <div className="text-xs text-red-600 font-normal">{photo.fail_reason}</div>}
              </dd>
              <dt className="text-slate-500">ผลของโมเดล</dt>
              <dd
                className={`m-0 ${photo.model_result ? `result-${photo.model_result}` : 'muted'}`}
                data-testid="photo-model-result"
                data-result={photo.model_result ?? ''}
              >
                {photo.model_result_label ?? 'ยังไม่มีผล'}
              </dd>
              <dt className="text-slate-500">ผลล่าสุด</dt>
              <dd className="m-0">
                <span
                  className={photo.current_result ? `result-${photo.current_result}` : 'muted'}
                  data-testid="photo-current-result"
                  data-result={photo.current_result ?? ''}
                >
                  {photo.current_result_label ?? 'ยังไม่มีผล'}
                </span>
                {photo.is_overridden && (
                  <span className="badge edited ml-2" data-testid="photo-edited-badge">
                    แก้ผลโดยคน
                  </span>
                )}
              </dd>
              <dt className="text-slate-500">ตรวจเสร็จเมื่อ</dt>
              <dd className="m-0 font-medium text-slate-700">{thaiTime(photo.finished_at)}</dd>
              {photo.model_version && (
                <>
                  <dt className="text-slate-500">รุ่นโมเดล</dt>
                  <dd className="m-0 font-mono text-xs text-slate-700">{photo.model_version}</dd>
                </>
              )}
            </dl>
          </div>

          {photo.lb_server && (
            <div className="rounded-2xl border border-slate-800 bg-navy-950 p-4 text-white shadow-md space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-cyan-300">
                  LAB 6 NGINX Least-Conn Telemetry
                </span>
                <Link href="/telemetry" className="text-xs text-amber-300 hover:underline no-underline">
                  ดูคลัสเตอร์ทั้งหมด →
                </Link>
              </div>
              <div className="grid grid-cols-2 gap-2.5 text-xs">
                <div className="rounded-xl bg-white/5 border border-white/10 p-2.5">
                  <div className="text-slate-400">Upstream / Server</div>
                  <div className="font-mono font-bold text-cyan-300 mt-0.5">{photo.lb_server}</div>
                  <div className="font-mono text-[11px] text-slate-400">{photo.lb_upstream ?? '–'}</div>
                </div>
                <div className="rounded-xl bg-white/5 border border-white/10 p-2.5">
                  <div className="text-slate-400">Micro-batch Size</div>
                  <div className="font-mono font-bold text-amber-300 text-base mt-0.5">
                    {photo.lb_batch_size ?? 1} <span className="text-[11px] font-normal text-slate-400">รูป/รอบ</span>
                  </div>
                </div>
                <div className="rounded-xl bg-white/5 border border-white/10 p-2.5">
                  <div className="text-slate-400">Queue Wait</div>
                  <div className="font-mono font-bold text-sky-300 mt-0.5">
                    {photo.lb_queue_ms !== null ? `${photo.lb_queue_ms.toFixed(2)} ms` : '–'}
                  </div>
                </div>
                <div className="rounded-xl bg-white/5 border border-white/10 p-2.5">
                  <div className="text-slate-400">YOLO11s GPU Time</div>
                  <div className="font-mono font-bold text-emerald-300 mt-0.5">
                    {photo.lb_model_ms !== null ? `${photo.lb_model_ms.toFixed(2)} ms` : '–'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {photo.can_override && (
            <form className="card space-y-3" onSubmit={onSubmit}>
              <h2 className="text-base font-bold text-slate-900 m-0">แก้ผล (Audit Trail)</h2>
              <label className="block space-y-1 text-sm">
                <span className="font-medium text-slate-700">ผลใหม่</span>
                <select
                  data-testid="override-result-select"
                  value={result}
                  onChange={(e) => setResult(e.target.value)}
                  className="w-full"
                >
                  <option value="">– เลือกผล –</option>
                  {resultOptions.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block space-y-1 text-sm">
                <span className="font-medium text-slate-700">เหตุผล (ต้องใส่)</span>
                <textarea
                  data-testid="override-reason"
                  rows={3}
                  className="w-full"
                  placeholder="ระบุเหตุผลการแก้ไขผลตรวจ…"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </label>
              {formError && (
                <p className="error" role="alert" data-testid="override-error">
                  {formError}
                </p>
              )}
              {saved && (
                <p className="rounded-xl bg-emerald-50 border border-emerald-200 px-3 py-2 text-sm font-medium text-emerald-800" data-testid="override-saved">
                  บันทึกการแก้ผลแล้ว ·{' '}
                  <Link href={`/reports/daily?date=${photo.upload_date}`} className="underline font-bold text-emerald-900">
                    ดูรายงานรายวัน
                  </Link>
                </p>
              )}
              <div className="flex gap-2">
                <button type="submit" data-testid="override-submit" disabled={saving}>
                  {saving ? 'กำลังบันทึก…' : 'บันทึกการแก้ผล'}
                </button>
                <button type="button" className="secondary" data-testid="override-cancel" onClick={resetForm} disabled={saving}>
                  ล้าง
                </button>
              </div>
            </form>
          )}

          {photo.can_view_history && (
            <div className="card space-y-3">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-base font-bold text-slate-900 m-0">ประวัติการแก้ผล ({photo.override_count})</h2>
                <button
                  type="button"
                  className="secondary text-xs py-1.5 px-3"
                  data-testid="override-history-toggle"
                  onClick={toggleHistory}
                >
                  {historyOpen ? 'ซ่อนประวัติ' : 'ดูประวัติการแก้ผล'}
                </button>
              </div>
              {historyOpen && (
                <div data-testid="override-history">
                  {historyError && (
                    <p className="error" role="alert">
                      {historyError}
                    </p>
                  )}
                  {!history && !historyError && <p className="muted text-sm">กำลังโหลด…</p>}
                  {history && history.length === 0 && <p className="muted text-sm">ยังไม่มีประวัติการแก้ผล</p>}
                  {history && history.length > 0 && (
                    <ul className="divide-y divide-slate-100 p-0 m-0 list-none">
                      {history.map((o) => (
                        <li key={o.id} data-testid={`override-item-${o.id}`} className="py-2.5 text-sm space-y-1">
                          <div>
                            <span className={`result-${o.result_before}`}>{o.result_before_label}</span>
                            <span className="mx-1.5 text-slate-400">→</span>
                            <span className={`result-${o.result_after}`}>{o.result_after_label}</span>
                          </div>
                          <div className="text-slate-700">{o.reason}</div>
                          <div className="text-xs text-slate-400">
                            โดย {o.edited_by.full_name} · {thaiTime(o.edited_at)}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
