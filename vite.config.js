import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
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
      '/v1': 'http://confidant:80',
      '/healthcheck': 'http://confidant:80',
      '/loggedout': 'http://confidant:80',
      '/custom': 'http://confidant:80',
    },
  },
  resolve: {
    alias: {
      // Compatibility with the old /components/ path
      '/components': resolve(__dirname, 'node_modules'),
      // Add other aliases if needed
    },
  },
});
