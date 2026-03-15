import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "www.partselect.com",
      },
      {
        protocol: "https",
        hostname: "*.partselect.com",
      },
    ],
  },
};

export default nextConfig;
