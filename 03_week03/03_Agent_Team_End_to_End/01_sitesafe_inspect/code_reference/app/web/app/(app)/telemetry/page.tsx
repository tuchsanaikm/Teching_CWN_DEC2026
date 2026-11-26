// /telemetry — LAB 6 Multi-GPU NGINX least_conn + Micro-batching Telemetry Dashboard
import Forbidden from '@/components/Forbidden';
import TelemetryDashboard from '@/components/TelemetryDashboard';
import { can, requireUser } from '@/components/server/session';

export const dynamic = 'force-dynamic';

export default async function TelemetryPage() {
  const user = await requireUser();
  if (!can(user, 'telemetry.view')) return <Forbidden />;
  return <TelemetryDashboard />;
}
