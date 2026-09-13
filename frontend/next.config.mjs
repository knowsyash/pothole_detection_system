/** @type {import('next').NextConfig} */
const backendBase = process.env.NEXT_PUBLIC_API_URL 
  ? process.env.NEXT_PUBLIC_API_URL.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '')
  : 'https://pothole-detection-system-mseo.onrender.com';

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
