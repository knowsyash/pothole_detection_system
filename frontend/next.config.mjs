/** @type {import('next').NextConfig} */
const backendBase = process.env.NEXT_PUBLIC_API_URL 
  ? process.env.NEXT_PUBLIC_API_URL.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '')
  : 'http://localhost:8000';

const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  async rewrites() {
    return [
      {
        source: '/static/evidence/:path*',
        destination: `${backendBase}/static/evidence/:path*`,
      },
    ];
  },
};

export default nextConfig;
