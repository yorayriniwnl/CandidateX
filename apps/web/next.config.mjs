/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep review builds independent from an actively running development server.
  distDir: process.env.CANDIDATEX_DIST_DIR || '.next',
  reactStrictMode: true,
  poweredByHeader: false,
  output: process.env.STANDALONE_BUILD === 'true' ? 'standalone' : undefined,
};

export default nextConfig;
