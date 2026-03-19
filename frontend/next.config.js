/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone', // Para Docker
  env: {
    API_URL: process.env.API_URL || 'http://localhost:8000',
  },
}

module.exports = nextConfig
