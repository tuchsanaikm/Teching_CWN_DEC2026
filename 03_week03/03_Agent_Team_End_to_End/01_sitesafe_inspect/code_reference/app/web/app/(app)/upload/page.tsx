// /upload — supervisor uploads many photos at once (FR-01–FR-03, BR-05, BR-06).
import Forbidden from '@/components/Forbidden';
import UploadForm from '@/components/UploadForm';
import { can, requireUser } from '@/components/server/session';
import {
  FILE_TOO_LARGE_MESSAGE,
  MAX_FILE_MB,
  MAX_PHOTOS_PER_UPLOAD,
  TOO_FEW_PHOTOS_MESSAGE,
  TOO_MANY_PHOTOS_MESSAGE,
  uploadLimits,
} from '@/lib/rules';

export const dynamic = 'force-dynamic';

export default async function UploadPage() {
  const user = await requireUser();
  if (!can(user, 'upload.create')) return <Forbidden />;
  const limits = uploadLimits();
  return (
    <div className="space-y-6">
      <section className="relative overflow-hidden rounded-3xl bg-navy-950 text-white shadow-xl border border-slate-800">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/images/hero-sitesafe.png"
          alt="SiteSafe AI Control Center"
          className="absolute inset-0 h-full w-full object-cover opacity-55"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-navy-950 via-navy-950/85 to-navy-950/35" />
        <div className="relative z-10 p-6 sm:p-8 flex flex-col gap-3 max-w-2xl">
          <div className="inline-flex w-fit items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-500/15 px-3 py-1 text-xs font-semibold text-cyan-200">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            2× RTX 4090 · 8× FastAPI Micro-batch · NGINX Least Connections
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white m-0">
            อัปโหลดรูปหน้างาน · {user.site_name}
          </h1>
          <p className="text-sm text-slate-300 m-0">
            ไซต์: <strong className="text-amber-300">{user.site_name}</strong> · ส่งได้ครั้งละไม่เกิน{' '}
            <strong className="text-white">{MAX_PHOTOS_PER_UPLOAD} รูป</strong> · ไฟล์ JPG หรือ PNG ขนาดไม่เกิน{' '}
            <strong className="text-white">{MAX_FILE_MB} MB</strong> ต่อรูป
          </p>
        </div>
      </section>

      <UploadForm
        limits={limits}
        messages={{
          tooFew: TOO_FEW_PHOTOS_MESSAGE,
          tooMany: TOO_MANY_PHOTOS_MESSAGE,
          tooLarge: FILE_TOO_LARGE_MESSAGE,
        }}
      />
    </div>
  );
}
