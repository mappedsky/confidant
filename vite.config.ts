import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import type { Proxy } from 'http-proxy';

// Rewrite any bare http://localhost/ redirects from the backend to port 3000
// so OIDC/logout redirects land back on the Vite dev server.
function rewriteLocalhostRedirects(proxy: Proxy) {
  proxy.on('proxyRes', (proxyRes) => {
    const location = proxyRes.headers['location'];
    if (location && /^http:\/\/localhost(\/|$)/.test(location)) {
      proxyRes.headers['location'] = location.replace(
        /^http:\/\/localhost\b/,
        'http://localhost:3000',
      );
    }
  });
}

const backendTarget = 'http://confidant:80';

export default defineConfig({
  plugins: [react()],
  root: 'confidant/public',
  base: '/',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'confidant/public/index.html'),
      },
    },
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/application/o': { target: 'http://authentik-server:9000' },
      '/v1': { target: backendTarget, configure: rewriteLocalhostRedirects },
      '/healthcheck': { target: backendTarget, configure: rewriteLocalhostRedirects },
      '/loggedout': { target: backendTarget, configure: rewriteLocalhostRedirects },
      '/custom': { target: backendTarget, configure: rewriteLocalhostRedirects },
    },
  },
});
