import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    root: process.cwd(),
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_INTERNAL_URL ?? "http://api:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
