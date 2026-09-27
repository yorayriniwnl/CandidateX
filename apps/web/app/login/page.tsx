import type { Metadata } from 'next';
import { PlatformHeader } from '../../components/navigation/PlatformHeader';
import { StudioFooter } from '../../components/studio/StudioFooter';
import { LoginClient } from './LoginClient';
import styles from './login.module.css';

export const metadata: Metadata = {
  title: 'Sign In | CandidateX — Capability Intelligence',
  description: 'Secure access to CandidateX candidate capability graphs, role calibrations, and verifiable interview probes.',
};

export default function LoginPage() {
  return (
    <div className={styles.loginSurface}>
      <PlatformHeader surface="login" />
      <LoginClient />
      <div className="w-[min(1360px,calc(100%-80px))] mx-auto pb-10">
        <StudioFooter />
      </div>
    </div>
  );
}
