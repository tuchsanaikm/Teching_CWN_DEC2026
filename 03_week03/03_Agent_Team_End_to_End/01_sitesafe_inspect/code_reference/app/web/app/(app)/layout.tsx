import type { ReactNode } from 'react';
import NavBar from '@/components/NavBar';
import { requireUser } from '@/components/server/session';

export const dynamic = 'force-dynamic';

export default async function AppLayout({ children }: { children: ReactNode }) {
  const user = await requireUser();
  return (
    <div className="min-h-screen flex flex-col bg-slate-100">
      <NavBar user={user} />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">{children}</main>
    </div>
  );
}
