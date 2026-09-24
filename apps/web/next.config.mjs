/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  output: process.env.STANDALONE_BUILD === 'true' ? 'standalone' : undefined,
  async redirects() {
    if (process.env.NODE_ENV !== 'production') return [];
    return ['/', '/analyze', '/hr', '/workspace'].map((source) => ({
      source,
      destination: '/research-demo',
      permanent: false,
    }));
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=(), browsing-topics=()',
          },
        ],
      },
    ];
  },
};

export default nextConfig;
