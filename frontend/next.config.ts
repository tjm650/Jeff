import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  basePath: process.env.NODE_ENV === 'production' ? '/Jeff' : '',
  assetPrefix: process.env.NODE_ENV === 'production' ? '/Jeff/' : '',
  images: {
    unoptimized: true
  }
};

export default nextConfig;
