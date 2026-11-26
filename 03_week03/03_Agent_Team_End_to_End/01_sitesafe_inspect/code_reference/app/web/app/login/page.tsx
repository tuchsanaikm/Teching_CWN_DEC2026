// /login — split-screen industrial safety AI sign-in page
import { redirect } from 'next/navigation';
import LoginForm from '@/components/LoginForm';
import { currentUser, homePathFor, safeNextPath } from '@/components/server/session';

export const dynamic = 'force-dynamic';

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  const next = safeNextPath(sp.next);
  const user = await currentUser();
  if (user) redirect(next ?? homePathFor(user));

  return (
    <div className="min-h-screen bg-navy-950 text-white lg:grid lg:grid-cols-12">
      <div className="relative hidden lg:col-span-7 lg:flex lg:flex-col lg:justify-between overflow-hidden p-10">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/images/hero-sitesafe.png"
          alt="SiteSafe Inspect Control Center"
          className="absolute inset-0 h-full w-full object-cover opacity-80"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-navy-950/95 via-navy-950/75 to-navy-950/25" />
        <div className="relative z-10 flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/images/logo-sitesafe.png"
            alt="SiteSafe Inspect"
            className="h-12 w-12 rounded-2xl border border-cyan-400/40 shadow-lg"
          />
          <div>
            <div className="text-xl font-bold tracking-tight">SiteSafe Inspect</div>
            <div className="text-xs text-cyan-300 font-medium">Thai Munkong Construction · AI PPE Safety Platform</div>
          </div>
        </div>

        <div className="relative z-10 max-w-xl space-y-5">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-400/30 bg-amber-500/15 px-3.5 py-1 text-xs font-semibold text-amber-300">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            Powered by 2× RTX 4090 · 8× FastAPI Micro-batching · NGINX Least Connections
          </div>
          <h1 className="text-4xl font-bold leading-tight tracking-tight text-white">
            ตรวจจับความปลอดภัยหน้างานก่อสร้างแบบเรียลไทม์
          </h1>
          <p className="text-base leading-relaxed text-slate-300">
            อัปโหลดภาพจากหน้างาน 3 ไซต์พร้อมกันได้สูงสุด 50 รูปต่อรอบ ระบบ AI YOLO11s ตรวจจับหมวกนิรภัยและเสื้อสะท้อนแสง
            พร้อมคัดแยกภาพที่มีความเสี่ยงและสรุปรายงานรายวันตามเกณฑ์ความปลอดภัย 90% ทันที
          </p>
          <div className="grid grid-cols-3 gap-4 pt-2">
            <div className="rounded-2xl border border-white/10 bg-navy-900/80 p-4 backdrop-blur">
              <div className="text-2xl font-bold text-cyan-300">2× 4090</div>
              <div className="text-xs text-slate-400 mt-1">8 FastAPI Micro-batch Workers</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-navy-900/80 p-4 backdrop-blur">
              <div className="text-2xl font-bold text-amber-300">≤ 30 วิ</div>
              <div className="text-xs text-slate-400 mt-1">SLO รอผลภาระปกติ p95</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-navy-900/80 p-4 backdrop-blur">
              <div className="text-2xl font-bold text-emerald-300">90.00%</div>
              <div className="text-xs text-slate-400 mt-1">เกณฑ์แจ้งเตือนรายวัน (BR-04)</div>
            </div>
          </div>
        </div>

        <div className="relative z-10 text-xs text-slate-400">
          SiteSafe Inspect · Role-Based Access Control (Supervisor · Safety Manager · Executive)
        </div>
      </div>

      <main className="flex min-h-screen items-center justify-center p-6 lg:col-span-5 bg-slate-950/90">
        <div className="w-full max-w-md rounded-3xl border border-slate-800 bg-white p-8 text-slate-900 shadow-2xl">
          <div className="flex flex-col items-center text-center mb-6">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              className="h-16 w-16 rounded-2xl border border-slate-200 shadow-md mb-3"
              src="/images/logo-sitesafe.png"
              alt="SiteSafe Inspect"
            />
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">เข้าสู่ระบบ SiteSafe Inspect</h1>
            <p className="text-sm text-slate-500 mt-1">ศูนย์ควบคุมความปลอดภัยอุปกรณ์ป้องกันส่วนบุคคล</p>
          </div>
          <LoginForm next={next} />
        </div>
      </main>
    </div>
  );
}
