/** `/copilot` — Live SSE Streaming Accounting Copilot (all 4 logged-in roles) */
import Forbidden from '../_ui/Forbidden';
import { PAGE_ROLES, requirePageUser } from '../_ui/session';
import CopilotView from './CopilotView';

export const dynamic = 'force-dynamic';

export default async function CopilotPage() {
  const { user, allowed } = await requirePageUser(PAGE_ROLES['/copilot'], '/copilot');
  if (!allowed) return <Forbidden user={user} page="AI Copilot" />;
  return (
    <main className="page">
      <CopilotView role={user.role} displayName={user.displayName} clientName={user.clientName} />
    </main>
  );
}
