import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [
      // Metabase JavaScript, CSS and assets
      {
        source: "/app/:path*",
        destination: "http://localhost:3001/app/:path*",
      },
      // Metabase APIs
      {
        source: "/api/session/:path*",
        destination: "http://localhost:3001/api/session/:path*",
      },
      {
        source: "/api/session",
        destination: "http://localhost:3001/api/session",
      },
      {
        source: "/api/user/:path*",
        destination: "http://localhost:3001/api/user/:path*",
      },
      {
        source: "/api/setting/:path*",
        destination: "http://localhost:3001/api/setting/:path*",
      },
      {
        source: "/api/database/:path*",
        destination: "http://localhost:3001/api/database/:path*",
      },
      {
        source: "/api/collection/:path*",
        destination: "http://localhost:3001/api/collection/:path*",
      },
      {
        source: "/api/card/:path*",
        destination: "http://localhost:3001/api/card/:path*",
      },
      {
        source: "/api/dashboard/:path*",
        destination: "http://localhost:3001/api/dashboard/:path*",
      },
      {
        source: "/api/table/:path*",
        destination: "http://localhost:3001/api/table/:path*",
      },
      {
        source: "/api/search/:path*",
        destination: "http://localhost:3001/api/search/:path*",
      },
      {
        source: "/api/timeline/:path*",
        destination: "http://localhost:3001/api/timeline/:path*",
      },
      {
        source: "/api/activity/:path*",
        destination: "http://localhost:3001/api/activity/:path*",
      },
      {
        source: "/api/bookmark/:path*",
        destination: "http://localhost:3001/api/bookmark/:path*",
      },
      {
        source: "/api/dataset/:path*",
        destination: "http://localhost:3001/api/dataset/:path*",
      },
    ];
  },
};

export default nextConfig;
