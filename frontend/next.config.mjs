/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/static/evidence/:path*',
        destination: 'http://localhost:8000/static/evidence/:path*',
      },
    ];
  },
};

export default nextConfig;
