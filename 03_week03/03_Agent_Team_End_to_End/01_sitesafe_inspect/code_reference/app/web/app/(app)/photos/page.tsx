import Forbidden from '@/components/Forbidden';
import PhotoList from '@/components/PhotoList';
import { photoListProps } from '@/components/server/photo-filters';
import { can, requireUser } from '@/components/server/session';

export const dynamic = 'force-dynamic';

export default async function PhotosPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const user = await requireUser();
  if (!can(user, 'photo.view')) return <Forbidden />;
  const { key, ...props } = await photoListProps(user, await searchParams);
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 m-0">รูปหน้างานทั้งหมด</h1>
        <p className="text-sm text-slate-500 mt-1 m-0">ค้นหาและตรวจสอบประวัติภาพหน้างานพร้อมผลตรวจ YOLO11s และข้อมูล GPU Upstream</p>
      </div>
      <PhotoList key={key} mode="all" {...props} />
    </div>
  );
}
