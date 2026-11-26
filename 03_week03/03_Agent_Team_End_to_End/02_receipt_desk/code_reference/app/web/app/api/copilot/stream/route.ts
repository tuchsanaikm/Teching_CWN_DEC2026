/**
 * Live SSE Streaming Accounting Copilot API · POST /api/copilot/stream
 * Streams Thai accounting analysis & monthly expense Q&A from Vast.ai 2x RTX 4090
 * vLLM Data Parallelism + NGINX least_conn (proxy_buffering off), reporting live
 * TTFT (ms), Decode Speed (tok/s), and X-Replica (gpu0 / gpu1).
 */
import { requireUser } from '../../_lib/auth';
import { query } from '../../_lib/db';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

interface ContextRow {
  client_name: string;
  category_name: string | null;
  cnt: string;
  total_sum: string;
}

async function buildAccountingContext(role: string, clientId: string | null): Promise<string> {
  const params: unknown[] = [];
  let where = "WHERE r.status = 'confirmed'";
  if (role === 'client' && clientId) {
    params.push(clientId);
    where += ' AND r.client_id = $1';
  }
  const rows = await query<ContextRow>(
    `SELECT c.name AS client_name, cat.name AS category_name,
            COUNT(*)::text AS cnt, COALESCE(SUM(r.total), 0)::text AS total_sum
       FROM receipts r
       JOIN clients c ON c.id = r.client_id
       LEFT JOIN categories cat ON cat.id = r.category_id
       ${where}
       GROUP BY c.name, cat.name
       ORDER BY SUM(r.total) DESC NULLS LAST
       LIMIT 12`,
    params,
  );
  if (!rows.length) {
    return 'ยังไม่มีใบเสร็จที่ยืนยันแล้วในฐานข้อมูลขณะนี้';
  }
  return rows
    .map((r) => `- ${r.client_name} | หมวด ${r.category_name ?? 'ไม่ระบุ'}: ${r.cnt} ใบ รวม ${Number(r.total_sum).toLocaleString('th-TH', { minimumFractionDigits: 2 })} บาท`)
    .join('\n');
}

function sseChunk(event: string, payload: unknown): Uint8Array {
  return new TextEncoder().encode(`event: ${event}\ndata: ${JSON.stringify(payload)}\n\n`);
}

export async function POST(request: Request): Promise<Response> {
  let user;
  try {
    user = await requireUser(request);
  } catch {
    return new Response(JSON.stringify({ error: 'unauthenticated' }), { status: 401 });
  }

  let body: { prompt?: string } = {};
  try {
    body = (await request.json()) as { prompt?: string };
  } catch {
    return new Response(JSON.stringify({ error: 'invalid_json' }), { status: 400 });
  }

  const question = (body.prompt ?? '').trim();
  if (!question) {
    return new Response(JSON.stringify({ error: 'empty_prompt' }), { status: 400 });
  }

  const contextText = await buildAccountingContext(user.role, user.clientId);
  const vllmUrl = process.env.VLLM_URL?.trim();
  const vllmKey = process.env.VLLM_API_KEY?.trim() || '';
  const vllmModel = process.env.VLLM_MODEL?.trim() || 'receipt-vlm';
  const aiMode = process.env.AI_MODE || 'vllm';
  const useLive = Boolean(vllmUrl) && aiMode !== 'mock';

  const systemPrompt =
    'คุณคือ ReceiptDesk Accounting Copilot ผู้ช่วยบัญชีอัจฉริยะสำหรับสำนักงานบัญชี "ใส่ใจการบัญชี" ' +
    'ตอบเป็นภาษาไทยอย่างสุภาพ กระชับ ชัดเจน เป็นข้อ ๆ พร้อมตัวเลขจริงจากบริบทด้านล่าง และแนะนำแนวทางปฏิบัติทางบัญชีที่ถูกต้อง\n\n' +
    `ข้อมูลสรุปใบเสร็จที่ยืนยันแล้วในระบบ (${user.role === 'client' ? 'เฉพาะร้านของคุณ' : 'ทั้งสำนักงาน'}):\n${contextText}`;

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const tSend = performance.now();
      let tFirst: number | null = null;
      let tokenCount = 0;

      if (!useLive) {
        // Deterministic mock SSE stream for port 3421
        const replica = Math.random() < 0.5 ? 'gpu0' : 'gpu1';
        const mockAnswer =
          `สรุปการวิเคราะห์บัญชีสำหรับคำถาม: "${question}"\n\n` +
          `1. ภาพรวมข้อมูลในระบบขณะนี้:\n${contextText}\n\n` +
          `2. ข้อแนะนำทางบัญชีของ ReceiptDesk:\n` +
          `- ตรวจสอบใบเสร็จที่ติดธงความมั่นใจต่ำกว่า 0.90 (BR-04) และผลต่างรายการเกิน 1.00 บาท (BR-05) ก่อนกดยืนยัน\n` +
          `- การสรุปรายเดือนนับตามวันที่บนใบเสร็จตั้งแต่วันที่ 1 ถึงวันสิ้นเดือน (BR-14) เพื่อความถูกต้องในการยื่นภาษีซื้อ\n` +
          `- โหมดนี้รันผ่าน Mock SSE Stream สำหรับทดสอบเส้นแบ่ง Business Rule อย่างแม่นยำ`;
        await new Promise((r) => setTimeout(r, 80));
        tFirst = performance.now();
        const ttftMs = Math.round(tFirst - tSend);
        controller.enqueue(sseChunk('meta', { replica, ttft_ms: ttftMs, mode: 'mock', model: 'receipt-vlm-mock' }));
        const chunks = mockAnswer.match(/.{1,6}/gu) ?? [mockAnswer];
        for (const piece of chunks) {
          tokenCount += 2;
          const elapsedSec = Math.max(0.01, (performance.now() - tFirst) / 1000);
          controller.enqueue(sseChunk('token', { text: piece, tokens: tokenCount, tps: Math.round(tokenCount / elapsedSec) }));
          await new Promise((r) => setTimeout(r, 18));
        }
        const totalSec = Math.max(0.01, (performance.now() - tFirst) / 1000);
        controller.enqueue(
          sseChunk('done', {
            replica,
            ttft_ms: ttftMs,
            decode_tps: Math.round((tokenCount / totalSec) * 10) / 10,
            total_tokens: tokenCount,
            elapsed_ms: Math.round(performance.now() - tSend),
            mode: 'mock',
          }),
        );
        controller.close();
        return;
      }

      try {
        const upstream = await fetch(`${vllmUrl!.replace(/\/$/, '')}/v1/chat/completions`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(vllmKey ? { Authorization: `Bearer ${vllmKey}` } : {}),
          },
          body: JSON.stringify({
            model: vllmModel,
            temperature: 0.4,
            max_tokens: 420,
            stream: true,
            stream_options: { include_usage: true, continuous_usage_stats: true },
            messages: [
              { role: 'system', content: systemPrompt },
              { role: 'user', content: question },
            ],
          }),
          signal: AbortSignal.timeout(90_000),
        });

        const replica = upstream.headers.get('x-replica') || 'gpu0';
        if (!upstream.ok || !upstream.body) {
          controller.enqueue(sseChunk('error', { message: `vLLM upstream HTTP ${upstream.status}` }));
          controller.close();
          return;
        }

        const reader = upstream.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let sentMeta = false;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line.startsWith('data:')) continue;
            const payload = line.slice(5).trim();
            if (payload === '[DONE]') continue;
            try {
              const ev = JSON.parse(payload) as {
                choices?: Array<{ delta?: { content?: string } }>;
                usage?: { completion_tokens?: number };
              };
              const delta = ev.choices?.[0]?.delta?.content;
              if (ev.usage?.completion_tokens) {
                tokenCount = Math.max(tokenCount, ev.usage.completion_tokens);
              }
              if (delta) {
                const now = performance.now();
                if (tFirst === null) {
                  tFirst = now;
                  sentMeta = true;
                  controller.enqueue(
                    sseChunk('meta', {
                      replica,
                      ttft_ms: Math.round(tFirst - tSend),
                      mode: 'live-2x4090',
                      model: vllmModel,
                    }),
                  );
                }
                tokenCount = Math.max(tokenCount + 1, ev.usage?.completion_tokens ?? tokenCount + 1);
                const decodeSec = Math.max(0.01, (now - tFirst) / 1000);
                controller.enqueue(
                  sseChunk('token', {
                    text: delta,
                    tokens: tokenCount,
                    tps: Math.round((tokenCount / decodeSec) * 10) / 10,
                  }),
                );
              }
            } catch {
              // ignore malformed partial SSE JSON
            }
          }
        }

        if (!sentMeta) {
          controller.enqueue(sseChunk('meta', { replica, ttft_ms: Math.round(performance.now() - tSend), mode: 'live-2x4090', model: vllmModel }));
        }
        const endNow = performance.now();
        const ttftMs = tFirst ? Math.round(tFirst - tSend) : Math.round(endNow - tSend);
        const decodeSec = tFirst ? Math.max(0.01, (endNow - tFirst) / 1000) : 0.01;
        controller.enqueue(
          sseChunk('done', {
            replica,
            ttft_ms: ttftMs,
            decode_tps: Math.round((tokenCount / decodeSec) * 10) / 10,
            total_tokens: tokenCount,
            elapsed_ms: Math.round(endNow - tSend),
            mode: 'live-2x4090',
          }),
        );
      } catch (err) {
        controller.enqueue(sseChunk('error', { message: err instanceof Error ? err.message : 'stream failed' }));
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
