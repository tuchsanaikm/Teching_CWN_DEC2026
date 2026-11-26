// Top bar of every logged-in page (DESIGN 7.4). Server Component.
import Link from 'next/link';
import type { SessionUser } from '@/lib/auth';
import { ROLE_LABELS } from '@/lib/views';
import { menuFor } from '@/components/server/session';
import LogoutButton from '@/components/LogoutButton';

export default function NavBar({ user }: { user: SessionUser }) {
  const m = menuFor(user);
  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-navy-950/95 text-white backdrop-blur-md shadow-lg">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-3 text-white no-underline group">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/images/logo-sitesafe.png"
            alt="SiteSafe Inspect"
            className="h-9 w-9 rounded-xl border border-cyan-400/30 object-cover shadow-md shadow-cyan-500/10 transition group-hover:scale-105"
          />
          <div className="leading-tight">
            <div className="flex items-center gap-2">
              <span className="text-base font-bold tracking-tight text-white">SiteSafe Inspect</span>
              <span className="hidden sm:inline-flex items-center rounded-full border border-amber-400/30 bg-amber-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-300">
                2× RTX 4090 LB
              </span>
            </div>
            <div className="text-[11px] text-slate-400">AI PPE Safety Control Center</div>
          </div>
        </Link>

        <nav className="flex flex-wrap items-center gap-1 sm:ml-4">
          {m.upload && (
            <Link
              href="/upload"
              data-testid="nav-upload"
              className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-200 no-underline transition hover:bg-white/10 hover:text-white"
            >
              อัปโหลดรูป
            </Link>
          )}
          {m.photos && (
            <Link
              href="/photos"
              data-testid="nav-photos"
              className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-200 no-underline transition hover:bg-white/10 hover:text-white"
            >
              รูปทั้งหมด
            </Link>
          )}
          {m.problems && (
            <Link
              href="/photos/problems"
              data-testid="nav-problems"
              className="rounded-lg px-3 py-1.5 text-sm font-medium text-amber-200 no-underline transition hover:bg-amber-500/15 hover:text-amber-100"
            >
              รูปที่มีปัญหา
            </Link>
          )}
          {m.report && (
            <Link
              href="/reports/daily"
              data-testid="nav-report"
              className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-200 no-underline transition hover:bg-white/10 hover:text-white"
            >
              รายงานรายวัน
            </Link>
          )}
          {m.telemetry && (
            <Link
              href="/telemetry"
              data-testid="nav-telemetry"
              className="inline-flex items-center gap-1.5 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-1.5 text-sm font-semibold text-cyan-300 no-underline transition hover:bg-cyan-500/20 hover:text-cyan-200"
            >
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              GPU Telemetry
            </Link>
          )}
        </nav>

        <div className="ml-auto flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-2 rounded-xl border border-slate-700/80 bg-slate-900/90 px-3 py-1.5">
            <div className="flex flex-col text-right leading-tight">
              <strong data-testid="nav-user-name" className="text-slate-100 text-xs font-semibold">
                {user.full_name}
              </strong>
              <div className="flex items-center justify-end gap-1.5 text-[11px] text-slate-400">
                <span data-testid="nav-user-role" data-role={user.role}>
                  {ROLE_LABELS[user.role]}
                </span>
                <span>·</span>
                <span data-testid="nav-user-site" data-site={user.site_code ?? ''} className="text-cyan-300 font-medium">
                  {user.site_name ?? 'ทุกไซต์'}
                </span>
              </div>
            </div>
          </div>
          <LogoutButton />
        </div>
      </div>
    </header>
  );
}
