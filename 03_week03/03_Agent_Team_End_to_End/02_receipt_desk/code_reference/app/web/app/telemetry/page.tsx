/** `/telemetry` — LAB 7 vLLM Serving Telemetry & 2x RTX 4090 Benchmark Dashboard */
import Forbidden from '../_ui/Forbidden';
import { PAGE_ROLES, requirePageUser } from '../_ui/session';
import TelemetryView from './TelemetryView';

export const dynamic = 'force-dynamic';

export default async function TelemetryPage() {
  const { user, allowed } = await requirePageUser(PAGE_ROLES['/telemetry'], '/telemetry');
  if (!allowed) return <Forbidden user={user} page="LAB 7 Telemetry" />;
  return (
    <main className="page">
      <TelemetryView />
    </main>
  );
}
