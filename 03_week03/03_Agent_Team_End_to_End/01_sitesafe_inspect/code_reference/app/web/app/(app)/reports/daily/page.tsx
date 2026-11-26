// /reports/daily — daily report per site, computed live (FR-15–FR-17, BR-04, BR-07).
import Link from 'next/link';
import Forbidden from '@/components/Forbidden';
import { can, requireUser } from '@/components/server/session';
import { siteScope } from '@/lib/access';
import { now, todayBangkok } from '@/lib/clock';
import { dailyReport } from '@/lib/report';
import { addDays, isValidDateString } from '@/lib/rules';

export const dynamic = 'force-dynamic';

export default async function DailyReportPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const user = await requireUser();
  if (!can(user, 'report.view') || !can(user, 'report.view', siteScope(user))) return <Forbidden />;

  const sp = await searchParams;
  const asked = typeof sp.date === 'string' ? sp.date : '';
  const badDate = asked !== '' && !isValidDateString(asked);
  const date = asked !== '' && !badDate ? asked : todayBangkok();
  const report = await dailyReport(user, date, now());

  const totalTaken = report.sites.reduce((acc, s) => acc + s.taken, 0);
  const totalFail = report.sites.reduce((acc, s) => acc + s.fail, 0);
  const redCount = report.sites.filter((s) => s.red).length;
  const totalEdited = report.sites.reduce((acc, s) => acc + s.edited, 0);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 m-0">รายงานความปลอดภัยรายวัน</h1>
          <p className="text-sm text-slate-500 mt-1 m-0">
            รายงานของวันที่ <strong data-testid="report-shown-date" className="text-slate-800">{report.date}</strong> คำนวณจากข้อมูลล่าสุดทุกครั้งที่เปิดหน้า (เกณฑ์สีแดง &lt; 90.00%)
          </p>
        </div>
        <span
          className={`badge text-sm px-4 py-1.5 ${report.ready ? 'ready' : 'intraday'}`}
          data-testid="report-ready-badge"
          data-ready={report.ready ? 'true' : 'false'}
        >
          {report.ready_label}
        </span>
      </div>

      <form className="card flex flex-wrap items-end gap-3" method="get" action="/reports/daily">
        <Link className="button secondary" href={`/reports/daily?date=${addDays(date, -1)}`} data-testid="report-prev-day">
          ← วันก่อนหน้า
        </Link>
        <label className="flex flex-col gap-1 text-xs font-semibold text-slate-600">
          วันที่รายงาน
          <input type="date" name="date" defaultValue={date} data-testid="report-date" key={date} />
        </label>
        <button type="submit" data-testid="report-apply">
          ดูรายงาน
        </button>
        <Link className="button secondary" href={`/reports/daily?date=${addDays(date, 1)}`} data-testid="report-next-day">
          วันถัดไป →
        </Link>
      </form>

      {badDate && (
        <p className="error" role="alert" data-testid="report-error">
          วันที่ต้องอยู่ในรูปแบบ YYYY-MM-DD จึงแสดงรายงานของวันนี้แทน
        </p>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs font-medium text-slate-500">รูปที่ถ่ายทั้งหมด</div>
          <div className="mt-1 text-2xl font-bold text-slate-900 tabular-nums">{totalTaken.toLocaleString()}</div>
        </div>
        <div className="rounded-2xl border border-red-200 bg-red-50/70 p-4 shadow-sm">
          <div className="text-xs font-medium text-red-700">รูปไม่ผ่านเกณฑ์</div>
          <div className="mt-1 text-2xl font-bold text-red-700 tabular-nums">{totalFail.toLocaleString()}</div>
        </div>
        <div className={`rounded-2xl border p-4 shadow-sm ${redCount > 0 ? 'border-red-400 bg-red-600 text-white' : 'border-emerald-200 bg-emerald-50/70 text-emerald-800'}`}>
          <div className={`text-xs font-medium ${redCount > 0 ? 'text-red-100' : 'text-emerald-700'}`}>ไซต์ต่ำกว่าเกณฑ์ 90%</div>
          <div className="mt-1 text-2xl font-bold tabular-nums">{redCount} ไซต์</div>
        </div>
        <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-4 shadow-sm">
          <div className="text-xs font-medium text-amber-800">รูปที่ถูกแก้ผลโดยคน</div>
          <div className="mt-1 text-2xl font-bold text-amber-800 tabular-nums">{totalEdited}</div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="data">
          <thead>
            <tr>
              <th>ไซต์</th>
              <th className="num">จำนวนรูปที่ถ่าย</th>
              <th className="num">จำนวนรูปไม่ผ่าน</th>
              <th className="num">จำนวนคนไม่ใส่หมวก</th>
              <th className="num">อัตราผ่าน (%)</th>
              <th>สถานะไซต์</th>
              <th className="num">รูปที่ถูกแก้ผล</th>
              <th className="num">รูปที่ตรวจไม่สำเร็จ</th>
            </tr>
          </thead>
          <tbody>
            {report.sites.map((s) => {
              const code = s.site.code;
              const barPct = s.pass_rate === null ? 0 : Math.max(0, Math.min(100, s.pass_rate));
              return (
                <tr
                  key={code}
                  className={s.red ? 'red' : undefined}
                  data-testid={`report-row-${code}`}
                  data-red={s.red ? 'true' : 'false'}
                >
                  <td>
                    <strong className="text-slate-900">{s.site.name}</strong>{' '}
                    <span className="text-xs font-mono text-slate-500">({code})</span>
                    {s.pass_rate !== null && (
                      <div className="mt-1.5 h-1.5 w-32 overflow-hidden rounded-full bg-slate-200">
                        <div
                          className={`h-full rounded-full ${s.red ? 'bg-red-600' : 'bg-emerald-500'}`}
                          style={{ width: `${barPct}%` }}
                        />
                      </div>
                    )}
                  </td>
                  <td className="num font-semibold" data-testid={`report-taken-${code}`}>{s.taken}</td>
                  <td className="num font-semibold" data-testid={`report-fail-${code}`}>{s.fail}</td>
                  <td className="num font-semibold" data-testid={`report-h-${code}`}>{s.h_total}</td>
                  <td
                    className="num font-bold text-base"
                    data-testid={`report-rate-${code}`}
                    data-rate={s.pass_rate === null ? '' : String(s.pass_rate)}
                  >
                    {s.pass_rate_text}
                  </td>
                  <td data-testid={`report-red-${code}`} data-red={s.red ? 'true' : 'false'}>
                    {s.red ? (
                      <span className="badge red">ต่ำกว่าเกณฑ์</span>
                    ) : (
                      <span className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800">
                        ปกติ
                      </span>
                    )}
                  </td>
                  <td className="num" data-testid={`report-edited-${code}`}>{s.edited}</td>
                  <td className="num" data-testid={`report-failed-${code}`}>{s.failed}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
