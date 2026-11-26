/** `/login` — Executive Fintech Split-Screen Login preserving all data-testids */
import { redirect } from 'next/navigation';
import { getPageUser, homeFor } from '../_ui/session';
import LoginForm from './LoginForm';

export const dynamic = 'force-dynamic';

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string | string[] }> }) {
  const user = await getPageUser();
  const sp = await searchParams;
  const next = typeof sp.next === 'string' ? sp.next : '';
  if (user) redirect(homeFor(user.role));
  return (
    <main className="min-h-screen bg-slate-950 flex items-center justify-center p-6">
      <div className="w-full max-w-5xl grid md:grid-cols-12 rounded-2xl overflow-hidden shadow-2xl border border-slate-800 bg-white">
        <div className="md:col-span-7 relative bg-slate-900 text-white p-8 flex flex-col justify-between min-h-[360px]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/images/hero-receiptdesk.png"
            alt="ReceiptDesk AI Workspace"
            className="absolute inset-0 w-full h-full object-cover opacity-65"
          />
          <div className="absolute inset-0 bg-gradient-to-br from-slate-950/90 via-slate-900/75 to-emerald-950/40" />
          <div className="relative z-10 flex items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/images/logo-receiptdesk.png"
              alt="ReceiptDesk"
              width={48}
              height={48}
              data-testid="login-logo"
              className="rounded-xl shadow-lg bg-white p-1"
            />
            <div>
              <div className="text-xl font-extrabold tracking-tight">ReceiptDesk</div>
              <div className="text-xs text-emerald-300 font-semibold">สำนักงานบัญชี ใส่ใจการบัญชี · AI OCR & Copilot</div>
            </div>
          </div>
          <div className="relative z-10 mt-10">
            <div className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-200 border border-emerald-400/30 mb-3">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              ขับเคลื่อนด้วย 2× RTX 4090 · vLLM Continuous Batching + NGINX least_conn
            </div>
            <h1 className="!text-white !text-3xl !font-extrabold leading-tight !m-0">
              อ่านใบเสร็จอัตโนมัติ พร้อมผู้ช่วยบัญชี AI แบบสตรีมสด
            </h1>
            <p className="text-slate-300 text-sm mt-3 leading-relaxed">
              รองรับการอัปโหลดเป็นชุดสูงสุด 100 ใบ ระบบตรวจธงความมั่นใจและผลต่างยอดรวมแบบเรียลไทม์ คิวงานด่วน 4:1 และสรุปรายเดือนส่งออก CSV
            </p>
          </div>
        </div>
        <div className="md:col-span-5 p-8 flex flex-col justify-center bg-slate-50">
          <div className="mb-4">
            <h2 className="text-xl font-bold text-slate-900 m-0">เข้าสู่ระบบ ReceiptDesk</h2>
            <p className="text-sm text-slate-500 mt-1 mb-0">รองรับ 4 บทบาท: พนักงานบัญชี · หัวหน้าทีม · เจ้าของ · ลูกค้าร้านค้า</p>
          </div>
          <LoginForm next={next} />
        </div>
      </div>
    </main>
  );
}
