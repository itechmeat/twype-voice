/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import { defineConfig } from "vite";

const REACT_PACKAGES = new Set(["react", "react-dom"]);
const LIVEKIT_PACKAGES = new Set(["livekit-client", "@livekit/components-react"]);
const REACT_QUERY_PACKAGES = new Set(["@tanstack/react-query"]);

function getNodeModulePackageName(id: string): string | null {
  const normalizedId = id.replaceAll("\\", "/");
  const [, lastNodeModulePath] = normalizedId.split("/node_modules/").slice(-2);

  if (lastNodeModulePath === undefined) {
    return null;
  }

  const segments = lastNodeModulePath.split("/");

  if (segments[0]?.startsWith("@")) {
    return segments.length >= 2 ? `${segments[0]}/${segments[1]}` : null;
  }

  return segments[0] ?? null;
}

function manualChunks(id: string): string | undefined {
  const packageName = getNodeModulePackageName(id);

  if (packageName === null) {
    return undefined;
  }

  if (REACT_PACKAGES.has(packageName)) {
    return "vendor-react";
  }

  if (LIVEKIT_PACKAGES.has(packageName)) {
    return "vendor-livekit";
  }

  if (REACT_QUERY_PACKAGES.has(packageName)) {
    return "vendor-react-query";
  }

  return undefined;
}

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      injectRegister: null,
      registerType: "prompt",
      strategies: "generateSW",
      manifest: false,
      includeAssets: [
        "manifest.webmanifest",
        "twype-icon.svg",
        "icon-192x192.png",
        "icon-512x512.png",
        "icon-maskable-192x192.png",
        "icon-maskable-512x512.png",
        "apple-touch-icon-180x180.png",
      ],
      workbox: {
        navigateFallback: "index.html",
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith("/api/"),
            handler: "NetworkFirst",
            options: {
              cacheName: "twype-api-runtime",
              networkTimeoutSeconds: 3,
              cacheableResponse: {
                statuses: [200],
              },
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 5,
                purgeOnQuotaError: true,
              },
            },
          },
          {
            urlPattern: ({ url }) => url.pathname.startsWith("/assets/"),
            handler: "CacheFirst",
            options: {
              cacheName: "twype-assets-runtime",
              cacheableResponse: {
                statuses: [200],
              },
              expiration: {
                maxEntries: 64,
                maxAgeSeconds: 60 * 60 * 24 * 30,
                purgeOnQuotaError: true,
              },
            },
          },
        ],
      },
    }),
  ],
  build: {
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks,
      },
    },
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/livekit-signaling/": {
        target: "http://localhost:7880",
        changeOrigin: true,
        ws: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/setupTests.ts",
  },
});
