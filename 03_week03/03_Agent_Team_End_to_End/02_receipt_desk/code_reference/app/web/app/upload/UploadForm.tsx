'use client';
/**
 * ฟอร์มอัปโหลดชุด (W7 POST /api/batches · W6 GET /api/clients · W23 GET /api/queue)
 * Upgraded with Executive Hero banner + Priority Queue & Backpressure live gauge (queued / 400).
 * Preserves ALL existing data-testids.
 */
import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { api, errorText } from '../_ui/api';
import type { ApiErrorBody } from '../_ui/api';
import QueueFull from '../_ui/QueueFull';
import { useClients } from '../_ui/useClients';

interface QueueInfo {
  normal: { pending: number; limit: number; room: number; full: boolean; retryAfterMinutesIfFull: number | null };
  urgent: { usedToday: number; limitPerDay: number; remainingToday: number; canSetMore: boolean; maxReceipts: number };
}

interface UploadOk {
  batchId: string;
  accepted: number;
  priority: 'normal' | 'urgent';
  queue: { pendingNormal: number; limit: number };
  urgentUsedToday?: number;
  message: string;
}

type Outcome =
  | { kind: 'ok'; data: UploadOk; sent: number }
  | { kind: 'full'; error: ApiErrorBody }
  | { kind: 'error'; error: ApiErrorBody };

export default function UploadForm({ canSetUrgent }: { canSetUrgent: boolean }) {
  const { clients, error: clientsError } = useClients();
  const [clientId, setClientId] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [urgent, setUrgent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [queue, setQueue] = useState<QueueInfo | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadQueue = useCallback(async () => {
    const r = await api<QueueInfo>('/api/queue');
    if (r.ok) setQueue(r.data);
  }, []);

  useEffect(() => {
    loadQueue();
    const t = setInterval(loadQueue, 15_000);
    return () => clearInterval(t);
  }, [loadQueue]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setOutcome(null);
    if (!clientId) {
      setOutcome({ kind: 'error', error: { error: 'client_required', message: 'กรุณาเลือกลูกค้าของชุดนี้' } });
      return;
    }
    const form = new FormData();
    form.set('clientId', clientId);
    if (canSetUrgent && urgent) form.set('urgent', 'true');
    for (const f of files) form.append('files', f, f.name);
    setBusy(true);
    const r = await api<UploadOk>('/api/batches', { method: 'POST', body: form });
    setBusy(false);
    if (r.ok) {
      setOutcome({ kind: 'ok', data: r.data, sent: files.length });
      setFiles([]);
      setUrgent(false);
      if (fileRef.current) fileRef.current.value = '';
    } else if (r.status === 429 || r.error.error === 'queue_full') {
      setOutcome({ kind: 'full', error: r.error });
    } else {
      setOutcome({ kind: 'error', error: r.error });
    }
    loadQueue();
  }

  const urgentBlocked = queue ? !queue.urgent.canSetMore : false;
  const pending = queue?.normal.pending ?? 0;
  const limit = queue?.normal.limit ?? 400;
  const pct = Math.min(100, Math.round((pending / Math.max(1, limit)) * 100));
  const barColor = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-500' : 'bg-emerald-500';

  return (
    <>
      <div className="hero-banner">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/images/hero-receiptdesk.png" alt="" className="hero-bg" />
        <div className="hero-scrim flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-200 border border-emerald-400/30 mb-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              2× RTX 4090 Data Parallelism · Continuous Batching + NGINX least_conn
            </div>
            <div className="text-xl font-extrabold text-white">ศูนย์รับชุดใบเสร็จอัตโนมัติ (Batch OCR Intake)</div>
            <div className="text-sm text-slate-300 mt-0.5">
              รับชุด 1–100 ไฟล์ (JPG · PNG · PDF 1 หน้า ≤ 10 MB) พร้อมระบบ Backpressure เพดานคิว {limit} ใบ และ Priority Queue 4:1
            </div>
          </div>
          <div className="flex gap-2">
            <Link href="/copilot" className="button">
              เปิด AI Copilot สตรีมสด
            </Link>
            <Link href="/telemetry" className="button secondary">
              ดู LAB 7 Telemetry
            </Link>
          </div>
        </div>
      </div>

      <div className="stats" style={{ marginBottom: 18 }}>
        <div className="stat" style={{ flex: '2 1 300px' }}>
          <div className="flex items-center justify-between">
            <div className="label">ใบงานปกติที่ค้างในคิว (Backpressure Gauge)</div>
            <span className={`badge ${pct >= 90 ? 'bad' : pct >= 70 ? 'warn' : 'live'}`}>{pct}% ของเพดาน</span>
          </div>
          <div className="value">
            <span data-testid="upload-queue-pending">{queue ? queue.normal.pending : '…'}</span>
            <span className="muted" style={{ fontSize: 14, fontWeight: 500 }}> / {limit} ใบ</span>
          </div>
          <div className="w-full h-2.5 bg-slate-200 rounded-full overflow-hidden mt-2" data-testid="upload-queue-bar">
            <div className={`h-full transition-all duration-300 ${barColor}`} style={{ width: `${pct}%` }} />
          </div>
        </div>
        {canSetUrgent && queue ? (
          <div className="stat" style={{ borderTopColor: '#4338ca' }}>
            <div className="label">โควตางานด่วนวันนี้ (BR-09 · หัวหน้าทีม)</div>
            <div className="value">
              {queue.urgent.usedToday}
              <span className="muted" style={{ fontSize: 14, fontWeight: 500 }}> / {queue.urgent.limitPerDay} งาน</span>
            </div>
            <div className="text-xs text-slate-500 mt-1">แซงคิว 4:1 · สูงสุด {queue.urgent.maxReceipts} ใบ/ชุด (BR-08)</div>
          </div>
        ) : null}
      </div>

      <form className="card" onSubmit={onSubmit} noValidate>
        <div className="row">
          <label className="field">
            ลูกค้า (ร้าน)
            <select data-testid="upload-client-select" value={clientId} onChange={(e) => setClientId(e.target.value)}>
              <option value="">— เลือกลูกค้า —</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} · {c.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field" style={{ flex: '1 1 320px' }}>
            ไฟล์ใบเสร็จ (JPG · PNG · PDF 1 หน้า · ไม่เกิน 10 MB ต่อไฟล์ · 1–100 ไฟล์)
            <input
              ref={fileRef}
              type="file"
              multiple
              data-testid="upload-file-input"
              className="border border-dashed border-emerald-400/70 bg-emerald-50/40 rounded-lg p-2 cursor-pointer"
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            />
          </label>
        </div>
        {clientsError ? <div className="notice error">{clientsError}</div> : null}
        <p className="muted" style={{ marginTop: 10 }}>
          เลือกแล้ว <strong className="text-slate-800">{files.length}</strong> ไฟล์
        </p>
        {canSetUrgent ? (
          <label className="flex items-center gap-2 my-3 p-3 rounded-lg bg-amber-50/80 border border-amber-200 text-sm font-medium text-amber-950">
            <input
              type="checkbox"
              data-testid="upload-urgent-checkbox"
              checked={urgent}
              onChange={(e) => setUrgent(e.target.checked)}
            />
            <span>
              งานด่วน (ไม่เกิน {queue?.urgent.maxReceipts ?? 10} ใบต่อชุด · ไม่เกิน {queue?.urgent.limitPerDay ?? 5} งานต่อวัน)
            </span>
            {urgentBlocked ? <span className="badge bad">วันนี้ใช้ครบแล้ว</span> : null}
          </label>
        ) : null}
        <button type="submit" data-testid="upload-submit-button" disabled={busy}>
          {busy ? 'กำลังส่งชุดใบเสร็จ…' : 'ส่งชุดนี้เข้าคิวอ่าน'}
        </button>
      </form>

      {outcome?.kind === 'ok' ? (
        <div className="notice ok" role="status">
          รับแล้ว <strong data-testid="upload-accepted-count">{outcome.data.accepted}</strong> ใบ (ส่ง {outcome.sent} ไฟล์)
          {outcome.data.priority === 'urgent' ? <span className="badge urgent">ด่วน</span> : null}
          {' · '}
          <Link href={`/batches/${outcome.data.batchId}`} className="underline font-bold">
            ดูสถานะชุดนี้
          </Link>
          <div className="muted" style={{ fontSize: 13 }}>ระบบอ่านต่อเบื้องหลังด้วย 2× RTX 4090 ออกจากหน้านี้ได้ทันที</div>
        </div>
      ) : null}

      {outcome?.kind === 'full' ? (
        <>
          <QueueFull
            minutes={outcome.error.retryAfterMinutes}
            testId="upload-full-message"
            minutesTestId="upload-retry-minutes"
          />
          <p className="muted">
            รับแล้ว <span data-testid="upload-accepted-count">0</span> ใบ
          </p>
        </>
      ) : null}

      {outcome?.kind === 'error' ? (
        <div className="notice error" role="alert">
          <div data-testid="upload-error">{errorText(outcome.error)}</div>
          {outcome.error.files?.length ? (
            <ul className="file-errors">
              {outcome.error.files.map((f) => (
                <li key={f.index} data-testid={`upload-file-error-${f.index}`}>
                  ไฟล์ที่ {f.index + 1} “{f.name}”: {f.message}
                </li>
              ))}
            </ul>
          ) : null}
          <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
            รับแล้ว <span data-testid="upload-accepted-count">0</span> ใบ — ทั้งชุดไม่ถูกรับ แก้ไฟล์แล้วส่งใหม่ทั้งชุด
          </div>
        </div>
      ) : null}
    </>
  );
}
