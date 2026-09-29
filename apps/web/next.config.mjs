/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep review builds independent from an actively running development server.
  distDir: process.env.CANDIDATEX_DIST_DIR || '.next',
  reactStrictMode: true,
  poweredByHeader: false,
  output: process.env.STANDALONE_BUILD === 'true' ? 'standalone' : undefined,
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://127.0.0.1:8000/api/v1/:path*',
      },
    ];
  },
};


export default nextConfig;
