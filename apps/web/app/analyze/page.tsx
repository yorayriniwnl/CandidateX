import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { LiveEvaluation } from '../../components/evidence-os/LiveEvaluation';

export default async function AnalyzePage() {
  const cookieStore = await cookies();
  const hasAuth = cookieStore.has('cx_auth') || cookieStore.has('cx_session');

  if (!hasAuth) {
    redirect('/login?redirect=%2Fanalyze');
  }

  return <LiveEvaluation />;
}
