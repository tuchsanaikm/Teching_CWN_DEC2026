import { notFound } from 'next/navigation';
import Forbidden from '@/components/Forbidden';
import PhotoDetail from '@/components/PhotoDetail';
import { can, requireUser } from '@/components/server/session';
import { findPhotoInScope } from '@/lib/photo-query';
import { RESULTS, RESULT_LABELS } from '@/lib/rules';

export const dynamic = 'force-dynamic';

export default async function PhotoPage({ params }: { params: Promise<{ id: string }> }) {
  const user = await requireUser();
  if (!can(user, 'photo.view')) return <Forbidden />;
  const { id } = await params;
  const photo = await findPhotoInScope(user, id);
  if (!photo || !can(user, 'photo.view', photo.site_id)) notFound();
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 m-0">รายละเอียดการตรวจความปลอดภัย</h1>
        <p className="text-sm text-slate-500 mt-1 m-0">
          ตรวจสอบกรอบตำแหน่งอุปกรณ์ป้องกันส่วนบุคคล ข้อมูลคลัสเตอร์ GPU และบันทึกประวัติการแก้ผล
        </p>
      </div>
      <PhotoDetail
        photoId={photo.id}
        resultOptions={RESULTS.map((r) => ({ value: r, label: RESULT_LABELS[r] }))}
      />
    </div>
  );
}
