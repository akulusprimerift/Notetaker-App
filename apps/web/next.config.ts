import type { NextConfig } from 'next';
const config: NextConfig = {
  agentRules: false,
  devIndicators: false,
  poweredByHeader: false,
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${process.env.API_ORIGIN ?? 'http://127.0.0.1:8010'}/:path*` }];
  },
  async headers() {
    return [{ source: '/:path*', headers: [
      { key:'X-Content-Type-Options', value:'nosniff' },
      { key:'Referrer-Policy', value:'same-origin' },
      { key:'X-Frame-Options', value:'DENY' },
      { key:'Permissions-Policy', value:'camera=(), geolocation=()' }
    ] }];
  }
};
export default config;
