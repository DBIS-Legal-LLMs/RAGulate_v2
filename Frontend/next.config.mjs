import packageJson from './package.json' with { type: 'json' };

/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  env: {
    // the build label from CI (APP_VERSION), else the package.json version
    NEXT_PUBLIC_APP_VERSION: process.env.APP_VERSION || packageJson.version,
  },
}

export default nextConfig
