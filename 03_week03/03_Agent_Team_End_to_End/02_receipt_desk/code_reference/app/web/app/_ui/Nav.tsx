'use client';
/**
 * Executive sticky navigation bar — shows only links allowed for the user's role.
 * Preserves ALL existing data-testids + adds nav-copilot & nav-telemetry.
 */
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import LogoutButton from './LogoutButton';
import OverdueBadge from './OverdueBadge';
import { canOpen } from './roles';
import type { PagePath, PageUser } from './roles';

const LINKS: { path: PagePath; testid: string; label: string }[] = [
  { path: '/upload', testid: 'nav-upload', label: 'อัปโหลดชุด' },
  { path: '/batches', testid: 'nav-batches', label: 'ชุดใบเสร็จ' },
  { path: '/receipts', testid: 'nav-receipts', label: 'รายการใบ' },
  { path: '/unreadable', testid: 'nav-unreadable', label: 'อ่านไม่ได้' },
  { path: '/overdue', testid: 'nav-overdue', label: 'ค้างเกินกำหนด' },
  { path: '/reports', testid: 'nav-reports', label: 'สรุปรายเดือน' },
  { path: '/insights', testid: 'nav-insights', label: 'เวลาตรวจ · GPU' },
  { path: '/copilot', testid: 'nav-copilot', label: 'AI Copilot' },
  { path: '/telemetry', testid: 'nav-telemetry', label: 'LAB 7 Telemetry' },
  { path: '/portal', testid: 'nav-portal', label: 'ใบเสร็จของร้าน' },
];

export default function Nav({ user }: { user: PageUser }) {
  const pathname = usePathname() || '';
  return (
    <header className="nav">
      <Link href="/" className="brand">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/images/logo-receiptdesk.png" alt="ReceiptDesk" width={32} height={32} />
        <span className="flex items-center gap-2">
          <span>ReceiptDesk</span>
          <span className="text-[10px] font-bold tracking-wider uppercase px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
            LAB 7 vLLM
          </span>
        </span>
      </Link>
      <nav>
        {LINKS.filter((l) => canOpen(user.role, l.path)).map((l) => {
          const active = pathname === l.path || pathname.startsWith(`${l.path}/`);
          return (
            <Link key={l.path} href={l.path} data-testid={l.testid} className={active ? 'nav-active' : undefined}>
              {l.label}
              {l.path === '/overdue' ? <OverdueBadge /> : null}
            </Link>
          );
        })}
      </nav>
      <div className="who">
        <span data-testid="nav-user-name" className="font-semibold text-white">
          {user.displayName}
        </span>
        <span className="role" data-testid="nav-user-role" data-role={user.role}>
          {user.roleLabel}
          {user.clientName ? ` · ${user.clientName}` : ''}
        </span>
        <LogoutButton />
      </div>
    </header>
  );
}
