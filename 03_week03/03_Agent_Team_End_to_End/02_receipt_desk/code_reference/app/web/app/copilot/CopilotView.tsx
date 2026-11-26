'use client';
/**
 * Live SSE Streaming Accounting Copilot UI
 * Streams real-time Thai accounting answers from 2x RTX 4090 vLLM Data Parallelism + NGINX least_conn
 * with live TTFT (ms), Decode Speed (tok/s), and X-Replica (gpu0 / gpu1) pills.
 */
import { useState } from 'react';
import type { FormEvent } from 'react';
import type { Role } from '../_ui/roles';

interface StreamMetrics {
  replica: string;
  ttftMs: number | null;
  tps: number | null;
  tokens: number;
  mode: string;
  model: string;
  streaming: boolean;
}

interface Message {
  id: number;
  role: 'user' | 'assistant';
  text: string;
  metrics?: StreamMetrics;
}

const QUICK_PROMPTS = [
  'สรุปรายจ่ายที่ยืนยันแล้วในระบบตอนนี้แยกตามร้านและหมวดให้หน่อย พร้อมข้อสังเกตทางบัญชี',
  'ใบเสร็จที่ติดธงความมั่นใจต่ำกว่า 0.90 และยอดไม่ตรงรายการ พนักงานควรตรวจจุดไหนก่อนยืนยัน',
  'อธิบายหลักการนับเดือนตามวันที่บนใบเสร็จ (BR-14) และผลกระทบต่อภาษีซื้อรายเดือน',
  'ถ้าสิ้นเดือนมีใบเสร็จเข้ามาพร้อมกัน 400 ใบ ระบบคิวงานด่วน 4:1 และ 2× RTX 4090 ช่วยอย่างไร',
];

export default function CopilotView({
  role,
  displayName,
  clientName,
}: {
  role: Role;
  displayName: string;
  clientName: string | null;
}) {
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState<StreamMetrics>({
    replica: '—',
    ttftMs: null,
    tps: null,
    tokens: 0,
    mode: 'ready',
    model: 'receipt-vlm',
    streaming: false,
  });

  async function ask(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    setError(null);
    setBusy(true);
    setPrompt('');

    const userId = Date.now();
    const botId = userId + 1;
    const initMetrics: StreamMetrics = {
      replica: 'routing…',
      ttftMs: null,
      tps: null,
      tokens: 0,
      mode: 'connecting',
      model: 'receipt-vlm',
      streaming: true,
    };
    setLive(initMetrics);
    setMessages((prev) => [
      ...prev,
      { id: userId, role: 'user', text: q },
      { id: botId, role: 'assistant', text: '', metrics: initMetrics },
    ]);

    try {
      const res = await fetch('/api/copilot/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: q }),
      });
      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      let accText = '';
      let curMetrics = { ...initMetrics };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split('\n\n');
        buf = parts.pop() ?? '';

        for (const chunk of parts) {
          const lines = chunk.split('\n');
          let evName = 'message';
          let dataStr = '';
          for (const ln of lines) {
            if (ln.startsWith('event:')) evName = ln.slice(6).trim();
            else if (ln.startsWith('data:')) dataStr += ln.slice(5).trim();
          }
          if (!dataStr) continue;
          const payload = JSON.parse(dataStr) as Record<string, unknown>;
          if (evName === 'meta') {
            curMetrics = {
              ...curMetrics,
              replica: String(payload.replica ?? 'gpu0'),
              ttftMs: Number(payload.ttft_ms ?? 0),
              mode: String(payload.mode ?? 'live'),
              model: String(payload.model ?? 'receipt-vlm'),
            };
          } else if (evName === 'token') {
            accText += String(payload.text ?? '');
            curMetrics = {
              ...curMetrics,
              tokens: Number(payload.tokens ?? curMetrics.tokens),
              tps: Number(payload.tps ?? curMetrics.tps ?? 0),
            };
          } else if (evName === 'done') {
            curMetrics = {
              ...curMetrics,
              replica: String(payload.replica ?? curMetrics.replica),
              ttftMs: Number(payload.ttft_ms ?? curMetrics.ttftMs ?? 0),
              tps: Number(payload.decode_tps ?? curMetrics.tps ?? 0),
              tokens: Number(payload.total_tokens ?? curMetrics.tokens),
              streaming: false,
            };
          } else if (evName === 'error') {
            setError(String(payload.message ?? 'เกิดข้อผิดพลาดในการสตรีม'));
            curMetrics = { ...curMetrics, streaming: false };
          }
          setLive({ ...curMetrics });
          setMessages((prev) =>
            prev.map((m) => (m.id === botId ? { ...m, text: accText, metrics: { ...curMetrics } } : m)),
          );
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ไม่สามารถเชื่อมต่อสตรีมได้');
      setLive((s) => ({ ...s, streaming: false }));
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    ask(prompt);
  }

  return (
    <div className="space-y-5">
      <div className="card !bg-slate-900 !text-white !border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/images/copilot-avatar.png"
            alt="ReceiptDesk AI Copilot"
            width={60}
            height={60}
            className="rounded-2xl shadow-lg border border-emerald-400/40"
          />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="!text-white !text-2xl !m-0">ReceiptDesk Accounting Copilot</h1>
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
                LIVE SSE STREAM
              </span>
            </div>
            <p className="text-slate-300 text-sm m-0 mt-1">
              ผู้ช่วยวิเคราะห์บัญชีและรายจ่ายรายเดือนแบบสตรีมทีละโทเคน (NGINX <code className="text-emerald-300">least_conn</code> + <code className="text-emerald-300">proxy_buffering off</code>)
              {role === 'client' && clientName ? ` · ขอบเขตข้อมูลเฉพาะร้าน: ${clientName}` : ` · ผู้ใช้งาน: ${displayName}`}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <div className="px-3 py-2 rounded-xl bg-slate-800/90 border border-slate-700 min-w-[108px]">
            <div className="text-[11px] text-slate-400 font-semibold">TTFT</div>
            <div className="text-lg font-extrabold text-emerald-300 tabular-nums" data-testid="copilot-ttft">
              {live.ttftMs !== null ? `${live.ttftMs} ms` : '—'}
            </div>
          </div>
          <div className="px-3 py-2 rounded-xl bg-slate-800/90 border border-slate-700 min-w-[122px]">
            <div className="text-[11px] text-slate-400 font-semibold">Decode Speed</div>
            <div className="text-lg font-extrabold text-sky-300 tabular-nums" data-testid="copilot-tps">
              {live.tps !== null ? `${live.tps} tok/s` : '—'}
            </div>
          </div>
          <div className="px-3 py-2 rounded-xl bg-slate-800/90 border border-slate-700 min-w-[120px]">
            <div className="text-[11px] text-slate-400 font-semibold">X-Replica</div>
            <div className="text-lg font-extrabold text-amber-300 flex items-center gap-1.5" data-testid="copilot-replica">
              <span className={`w-2 h-2 rounded-full ${live.streaming ? 'bg-emerald-400 animate-ping' : 'bg-emerald-400'}`} />
              {live.replica}
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {QUICK_PROMPTS.map((q, idx) => (
          <button
            key={idx}
            type="button"
            data-testid={`copilot-chip-${idx}`}
            disabled={busy}
            onClick={() => ask(q)}
            className="secondary !text-xs !py-2 !px-3 !rounded-full hover:!border-emerald-500 hover:!text-emerald-700"
          >
            ✨ {q}
          </button>
        ))}
      </div>

      <div className="card min-h-[340px] flex flex-col justify-between gap-4">
        <div className="space-y-4 max-h-[460px] overflow-y-auto pr-1">
          {messages.length === 0 ? (
            <div className="text-center py-14 text-slate-500">
              <div className="text-base font-semibold text-slate-700">เลือกคำถามด่วนด้านบน หรือพิมพ์คำถามบัญชีของคุณด้านล่าง</div>
              <div className="text-sm mt-1">
                คำตอบจะสตรีมแบบเรียลไทม์ผ่าน 2× RTX 4090 Data Parallelism พร้อมแสดงค่า TTFT, tok/s และ X-Replica (gpu0 / gpu1)
              </div>
            </div>
          ) : (
            messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                    m.role === 'user'
                      ? 'bg-emerald-600 text-white shadow-sm'
                      : 'bg-slate-50 border border-slate-200 text-slate-900'
                  }`}
                >
                  {m.role === 'assistant' && m.metrics ? (
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 mb-2 pb-1.5 border-b border-slate-200">
                      <span className="font-bold text-emerald-700">ReceiptDesk Copilot</span>
                      <span className="badge live">X-Replica: {m.metrics.replica}</span>
                      {m.metrics.ttftMs !== null ? <span className="badge">TTFT {m.metrics.ttftMs} ms</span> : null}
                      {m.metrics.tps !== null ? <span className="badge">{m.metrics.tps} tok/s</span> : null}
                      <span className="badge">{m.metrics.tokens} tokens</span>
                    </div>
                  ) : null}
                  <div
                    className="whitespace-pre-wrap leading-relaxed text-[14.5px]"
                    data-testid={m.role === 'assistant' ? 'copilot-response' : undefined}
                  >
                    {m.text || (m.metrics?.streaming ? 'กำลังรอโทเคนแรกจาก GPU…' : '')}
                    {m.metrics?.streaming ? <span className="inline-block w-2 h-4 ml-1 bg-emerald-500 animate-pulse align-middle" /> : null}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {error ? <div className="notice error">{error}</div> : null}

        <form onSubmit={onSubmit} className="flex gap-3 pt-3 border-t border-slate-200">
          <input
            type="text"
            data-testid="copilot-input"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="ถามเรื่องใบเสร็จ รายจ่ายรายเดือน ภาษีซื้อ หรือกติกาบัญชี…"
            className="flex-1"
            disabled={busy}
          />
          <button type="submit" data-testid="copilot-send-button" disabled={busy || !prompt.trim()}>
            {busy ? 'กำลังสตรีม…' : 'ส่งคำถาม'}
          </button>
        </form>
      </div>
    </div>
  );
}
