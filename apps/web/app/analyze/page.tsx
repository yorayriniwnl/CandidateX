import { redirect } from 'next/navigation';
import { LiveEvaluation } from '../../components/evidence-os/LiveEvaluation';
import { getSessionFromRequest } from '../../lib/session';

export default async function AnalyzePage() {
  const session = await getSessionFromRequest();

  if (!session) {
    redirect('/login?redirect=%2Fanalyze');
  }

  return <LiveEvaluation />;
}
