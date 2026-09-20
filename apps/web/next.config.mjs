/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  output: process.env.STANDALONE_BUILD === 'true' ? 'standalone' : undefined,
};

export default nextConfig;
