type BackendEnvironment = {
  NODE_ENV?: string;
  VERCEL?: string;
  CCI_API_URL?: string;
};

export function isSyntheticOnlyDeployment(env: BackendEnvironment = process.env): boolean {
  return env.NODE_ENV === 'production' || Boolean(env.VERCEL?.trim());
}

export function resolveCciBackendUrl(env: BackendEnvironment = process.env): string | null {
  const configuredUrl = env.CCI_API_URL?.trim();
  if (configuredUrl) return configuredUrl.replace(/\/+$/, '');
  if (isSyntheticOnlyDeployment(env)) return null;
  if (env.NODE_ENV === 'development') return 'http://127.0.0.1:8000';
  return null;
}
