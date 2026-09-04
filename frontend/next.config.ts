import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["*.trycloudflare.com", "*.loca.lt"],
  async rewrites() {
    return [
      { source: "/chat", destination: "http://localhost:8000/chat" },
      { source: "/chats/:path*", destination: "http://localhost:8000/chats/:path*" },
      { source: "/upload", destination: "http://localhost:8000/upload" },
      { source: "/recommend", destination: "http://localhost:8000/recommend" },
      { source: "/advisor", destination: "http://localhost:8000/advisor" },
    ];
  },
};

export default nextConfig;
