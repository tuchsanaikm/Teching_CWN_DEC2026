'use client';

import { useState, type FormEvent } from 'react';

export default function LoginForm({ next }: { next: string | null }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ email, password }),
      });
      if (res.ok) {
        window.location.assign(next ?? '/');
        return;
      }
      const body = (await res.json().catch(() => null)) as { message?: string } | null;
      setError(body?.message ?? 'เข้าสู่ระบบไม่สำเร็จ');
    } catch {
      setError('เชื่อมต่อระบบไม่ได้ กรุณาลองใหม่');
    }
    setBusy(false);
  }

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4">
      <label className="block space-y-1.5">
        <span className="text-sm font-semibold text-slate-700">อีเมล</span>
        <input
          data-testid="login-email"
          type="email"
          name="email"
          autoComplete="username"
          placeholder="เช่น sup.a@sitesafe.test"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full"
        />
      </label>
      <label className="block space-y-1.5">
        <span className="text-sm font-semibold text-slate-700">รหัสผ่าน</span>
        <input
          data-testid="login-password"
          type="password"
          name="password"
          autoComplete="current-password"
          placeholder="••••••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full"
        />
      </label>
      {error && (
        <p className="error" role="alert" data-testid="login-error">
          {error}
        </p>
      )}
      <button
        data-testid="login-submit"
        type="submit"
        disabled={busy}
        className="w-full py-2.5 text-base font-bold bg-gradient-to-r from-sky-600 to-cyan-600 hover:from-sky-700 hover:to-cyan-700 shadow-md"
      >
        {busy ? 'กำลังเข้าสู่ระบบ…' : 'เข้าสู่ระบบ'}
      </button>
    </form>
  );
}
