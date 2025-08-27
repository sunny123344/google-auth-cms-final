const nextConfig = {
  reactStrictMode: true,
  images: { unoptimized: true },
  env: { NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:4000" }
};
module.exports = nextConfig;
