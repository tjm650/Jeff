import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  basePath: process.env.NODE_ENV === 'production' ? '/Jeff' : '',
  assetPrefix: process.env.NODE_ENV === 'production' ? '/Jeff/' : '',
  images: {
    unoptimized: true
  },
  // Optional: Add if you're using TypeScript strict mode
  typescript: {
    ignoreBuildErrors: false,
  },
  // Optional: Add if you're using ESLint
  eslint: {
    ignoreDuringBuilds: false,
  }
};

export default nextConfig;
