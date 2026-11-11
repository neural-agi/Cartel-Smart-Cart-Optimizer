import type { NextConfig } from "next";

const backendInternalUrl = process.env.BACKEND_INTERNAL_URL;

// Vercel has no Docker network. Fail the build explicitly instead of silently
// rewriting /api traffic to the local-compose hostname.
if (process.env.VERCEL && !backendInternalUrl) {
  throw new Error(
    "BACKEND_INTERNAL_URL must be set to the public Render backend origin for Vercel builds.",
  );
}

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    root: process.cwd(),
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendInternalUrl ?? "http://api:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
