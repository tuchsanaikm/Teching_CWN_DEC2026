import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';

export const metadata: Metadata = {
  title: 'SiteSafe Inspect · AI PPE Safety & Multi-GPU Control Center',
  description: 'ระบบตรวจอุปกรณ์ความปลอดภัยหน้างานก่อสร้างด้วย YOLO11s และคลัสเตอร์ 2× RTX 4090 Micro-batching + NGINX Least Connections',
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="th">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600;700&family=Sarabun:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-slate-100 text-slate-900">{children}</body>
    </html>
  );
}
