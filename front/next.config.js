/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    // Type checking is handled by separate script
    ignoreBuildErrors: false,
  },
  eslint: {
    // ESLint checking is handled by separate script
    ignoreDuringBuilds: false,
  },
  env: {
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE,
    NEXT_PUBLIC_WS_BASE: process.env.NEXT_PUBLIC_WS_BASE,
    NEXT_PUBLIC_ADMIN_TOKEN: process.env.NEXT_PUBLIC_ADMIN_TOKEN,
  },
  images: {
    remotePatterns: [],
  },
  // Experimental features to fix module issues
  experimental: {
    esmExternals: true,
  },
  // Webpack configuration
  webpack: (config, { isServer, dev }) => {
    // Fix for 'exports is not defined' error
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
        crypto: false,
        stream: false,
        url: false,
        zlib: false,
        http: false,
        https: false,
        assert: false,
        os: false,
        path: false,
      };
    }

    // Fix module resolution issues
    config.resolve.extensionAlias = {
      '.js': ['.js', '.ts', '.tsx'],
      '.jsx': ['.jsx', '.tsx'],
    };

    // Disable chunk splitting in development to avoid the exports issue
    if (dev) {
      config.optimization.splitChunks = false;
    } else {
      // Only use chunk splitting in production with safer settings
      config.optimization.splitChunks = {
        chunks: 'all',
        minSize: 20000,
        maxSize: 244000,
        cacheGroups: {
          default: {
            minChunks: 2,
            priority: -20,
            reuseExistingChunk: true,
          },
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            priority: -10,
            chunks: 'all',
            enforce: true,
          },
        },
      };
    }

    return config;
  },
  // Security headers
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;