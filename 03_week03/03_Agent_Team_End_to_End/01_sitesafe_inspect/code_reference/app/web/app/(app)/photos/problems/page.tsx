import Forbidden from '@/components/Forbidden';
import PhotoList from '@/components/PhotoList';
import { photoListProps } from '@/components/server/photo-filters';
import { can, requireUser } from '@/components/server/session';

export const dynamic = 'force-dynamic';

export default async function ProblemsPage({
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
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 m-0">รูปที่มีปัญหาความปลอดภัย</h1>
        <p className="text-sm text-slate-500 mt-1 m-0">
          แสดงเฉพาะรูปที่ผลล่าสุดเป็น “{props.resultLabels.FAIL}” และ “{props.resultLabels.WARN}” เพื่อสั่งการแก้ไขหน้างานได้ทันที
        </p>
      </div>
      <PhotoList key={key} mode="problems" {...props} />
    </div>
  );
}
