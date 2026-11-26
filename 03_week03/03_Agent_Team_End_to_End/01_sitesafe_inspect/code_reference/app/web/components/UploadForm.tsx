'use client';

// Multi-photo upload (FR-01–FR-03). Flow (DESIGN 3):
//   1) POST /api/uploads {count} → batch_id (BR-06 is decided there)
//   2) POST /api/uploads/{batch_id}/photos — one file per request, up to 8 in flight
//   3) each file shows "รับแล้ว" or the reason it was rejected

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react';

const MAX_PARALLEL = 8;

export type UploadLimits = {
  min_photos: number;
  max_photos: number;
  max_file_bytes: number;
  max_file_mb: number;
  accepted_types: string[];
};

type Messages = { tooFew: string; tooMany: string; tooLarge: string };

type ItemState = 'waiting' | 'sending' | 'accepted' | 'rejected';
type Item = { name: string; size: number; state: ItemState; message?: string };

const STATE_TEXT: Record<ItemState, string> = {
  waiting: 'รอส่ง',
  sending: 'กำลังส่ง…',
  accepted: 'รับแล้ว',
  rejected: 'ไม่รับ',
};

const STATE_PILL: Record<ItemState, string> = {
  waiting: 'bg-slate-100 text-slate-600',
  sending: 'bg-sky-100 text-sky-700 animate-pulse',
  accepted: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-red-100 text-red-700',
};

function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

async function errorMessage(res: Response): Promise<string> {
  const body = (await res.json().catch(() => null)) as { message?: string } | null;
  if (body?.message) return body.message;
  if (res.status === 401) return 'กรุณาเข้าสู่ระบบใหม่';
  if (res.status === 403) return 'บัญชีนี้ไม่มีสิทธิ์อัปโหลดรูป';
  return `ส่งไม่สำเร็จ (รหัส ${res.status})`;
}

export default function UploadForm({ limits, messages }: { limits: UploadLimits; messages: Messages }) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [batchId, setBatchId] = useState<string | null>(null);

  useEffect(() => {
    if (!busy) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [busy]);

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    const list = e.target.files ? Array.from(e.target.files) : [];
    setFiles(list);
    setItems([]);
    setError(null);
    setBatchId(null);
  }

  function clear() {
    setFiles([]);
    setItems([]);
    setError(null);
    setBatchId(null);
    if (inputRef.current) inputRef.current.value = '';
  }

  function update(index: number, patch: Partial<Item>) {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, ...patch } : it)));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setError(null);
    setBatchId(null);

    if (files.length < limits.min_photos) {
      setError(messages.tooFew);
      return;
    }
    if (files.length > limits.max_photos) {
      setError(messages.tooMany);
      return;
    }

    setBusy(true);
    const selected = files.slice();
    try {
      const res = await fetch('/api/uploads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ count: selected.length }),
      });
      if (!res.ok) {
        setError(await errorMessage(res));
        setBusy(false);
        return;
      }
      const created = (await res.json()) as { batch_id: string; upload_url?: string };
      const id = created.batch_id;
      const uploadUrl = created.upload_url ?? `/api/uploads/${id}/photos`;

      const initial: Item[] = selected.map((f) =>
        f.size > limits.max_file_bytes
          ? { name: f.name, size: f.size, state: 'rejected', message: messages.tooLarge }
          : { name: f.name, size: f.size, state: 'waiting' },
      );
      setItems(initial);
      const toSend = initial.map((it, i) => (it.state === 'waiting' ? i : -1)).filter((i) => i >= 0);
      let rejected = initial.length - toSend.length;

      let next = 0;
      const worker = async () => {
        while (next < toSend.length) {
          const index = toSend[next++];
          update(index, { state: 'sending' });
          try {
            const fd = new FormData();
            fd.append('file', selected[index], selected[index].name);
            const r = await fetch(uploadUrl, { method: 'POST', body: fd, credentials: 'same-origin' });
            if (r.status === 201) {
              update(index, { state: 'accepted', message: undefined });
            } else {
              rejected += 1;
              update(index, { state: 'rejected', message: await errorMessage(r) });
            }
          } catch {
            rejected += 1;
            update(index, { state: 'rejected', message: 'ส่งไม่สำเร็จ กรุณาตรวจการเชื่อมต่อแล้วลองใหม่' });
          }
        }
      };
      await Promise.all(Array.from({ length: Math.min(MAX_PARALLEL, toSend.length) }, worker));

      setBusy(false);
      if (rejected === 0) {
        router.push(`/uploads/${id}`);
      } else {
        setBatchId(id);
      }
    } catch {
      setError('เชื่อมต่อระบบไม่ได้ กรุณาลองใหม่');
      setBusy(false);
    }
  }

  const accepted = items.filter((i) => i.state === 'accepted').length;
  const rejectedCount = items.filter((i) => i.state === 'rejected').length;
  const showFiles: Item[] = items.length
    ? items
    : files.map((f) => ({ name: f.name, size: f.size, state: 'waiting' as const }));

  return (
    <form className="card space-y-5" onSubmit={onSubmit}>
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <label className="flex flex-col gap-1.5 text-sm font-semibold text-slate-700">
          <span>เลือกรูป (เลือกได้หลายรูปพร้อมกัน)</span>
          <input
            ref={inputRef}
            data-testid="upload-file-input"
            type="file"
            name="files"
            multiple
            accept={limits.accepted_types.join(',')}
            onChange={onChange}
            disabled={busy}
            className="block w-full max-w-md text-sm text-slate-600 file:mr-4 file:rounded-lg file:border-0 file:bg-sky-50 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-sky-700 hover:file:bg-sky-100 cursor-pointer"
          />
        </label>

        <div className="flex flex-wrap items-center gap-4">
          <div className="rounded-xl bg-slate-50 border border-slate-200 px-4 py-2 text-sm text-slate-600">
            เลือกแล้ว <strong data-testid="upload-selected-count" className="text-lg font-bold text-slate-900 mx-1">{files.length}</strong> รูป
          </div>
          <div className="flex gap-2">
            <button
              data-testid="upload-submit"
              type="submit"
              disabled={busy}
              className="bg-gradient-to-r from-sky-600 to-cyan-600 hover:from-sky-700 hover:to-cyan-700 px-5 py-2.5 text-sm font-bold shadow-md"
            >
              {busy ? 'กำลังส่งเข้าคิว AI…' : 'ส่งรูปตรวจ AI'}
            </button>
            <button data-testid="upload-clear" type="button" className="secondary" onClick={clear} disabled={busy}>
              ล้างรายการ
            </button>
          </div>
        </div>
      </div>

      {error && (
        <p className="error" role="alert" data-testid="upload-error">
          {error}
        </p>
      )}

      {items.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-900 px-4 py-3 text-sm text-white">
          <p data-testid="upload-summary" className="m-0 font-medium">
            รับแล้ว <strong className="text-emerald-400">{accepted}</strong> รูป · ไม่รับ{' '}
            <strong className="text-red-400">{rejectedCount}</strong> รูป · จาก {items.length} รูป
          </p>
          {batchId && (
            <Link
              href={`/uploads/${batchId}`}
              data-testid="upload-open-batch"
              className="inline-flex items-center rounded-lg bg-cyan-500 px-3.5 py-1.5 text-xs font-bold text-slate-950 no-underline hover:bg-cyan-400 transition"
            >
              ดูสถานะการตรวจของรูปที่รับแล้ว →
            </Link>
          )}
        </div>
      )}

      {showFiles.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50/70 py-10 px-6 text-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/images/empty-upload.png"
            alt="พร้อมรับภาพหน้างาน"
            className="w-60 h-auto rounded-2xl shadow-sm mb-4 border border-slate-200/80"
          />
          <h2 className="text-base font-bold text-slate-800 m-0">พร้อมตรวจภาพหน้างานด้วย AI ความเร็วสูง</h2>
          <p className="text-sm text-slate-500 mt-1 max-w-md">
            เลือกรูปหน้างาน JPG หรือ PNG สูงสุด {limits.max_photos} รูป ระบบจะส่งแบบขนานเข้าคลัสเตอร์ 2× RTX 4090 (NGINX Least Connections + Micro-batching)
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200 overflow-hidden m-0 p-0 list-none">
          {showFiles.map((it, i) => (
            <li
              key={`${i}-${it.name}`}
              data-testid={`upload-file-${i}`}
              data-state={it.state}
              className="flex flex-wrap items-center gap-3 bg-white px-4 py-2.5 text-sm hover:bg-slate-50"
            >
              <span className="w-7 text-xs font-mono text-slate-400">#{i + 1}</span>
              <span className="flex-1 font-medium text-slate-800 break-all">{it.name}</span>
              <span className="text-xs font-mono text-slate-500">{formatSize(it.size)}</span>
              <span
                data-testid={`upload-file-state-${i}`}
                className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATE_PILL[it.state]}`}
              >
                {STATE_TEXT[it.state]}
              </span>
              {it.state === 'rejected' && it.message && (
                <span className="error py-1 px-2.5 text-xs" data-testid={`upload-file-error-${i}`}>
                  {it.message}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}
