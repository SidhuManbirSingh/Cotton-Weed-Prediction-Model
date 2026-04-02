import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Listen on all IP addresses (required for Docker)
    port: 3000,
    proxy: {
      '/api': process.env.BACKEND_URL || 'http://localhost:5000',
    },
  },
})
