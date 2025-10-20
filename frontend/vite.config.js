import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// frontend/vite.config.js
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/plan': 'http://localhost:8000',
      '/plan_stream': 'http://localhost:8000',
    },
  },
});