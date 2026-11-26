import Forbidden from '@/components/Forbidden';
import BatchStatus from '@/components/BatchStatus';
import { can, requireUser } from '@/components/server/session';
import { STATUS_LABELS } from '@/lib/rules';

export const dynamic = 'force-dynamic';

export default async function BatchPage({ params }: { params: Promise<{ batchId: string }> }) {
  const user = await requireUser();
  if (!can(user, 'upload.view')) return <Forbidden />;
  const { batchId } = await params;
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 m-0">สถานะการตรวจรูปชุดนี้</h1>
        <p className="text-sm text-slate-500 mt-1 m-0">
          กระจายคำขอผ่าน NGINX Least Connections ไปยัง 8 FastAPI Workers บน 2× RTX 4090 พร้อมแสดง batch size และเวลาประมวลผล
        </p>
      </div>
      <BatchStatus batchId={batchId} statusLabels={{ ...STATUS_LABELS }} />
    </div>
  );
}
