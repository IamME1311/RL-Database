import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath, URL } from 'node:url';

// The backend session is an httpOnly cookie. If the SPA were served from :5173
// and the API from :8000 those are cross-origin, and the cookie would be subject
// to SameSite/third-party-cookie rules. Proxying /api through the dev server
// makes everything same-origin, so dev behaves exactly like a same-domain
// production deploy and no SameSite=None juggling is needed.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000',
        changeOrigin: false, // keep Host so the backend sets cookies for our origin
      },
    },
  },
});
