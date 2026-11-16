import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendUrl = process.env.BACKEND_URL || 'http://localhost:5000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Listen on all IP addresses (required for Docker)
    port: 3000,
    proxy: {
      '/api': backendUrl,
      '/presets': backendUrl,
      '/samples': backendUrl,
      '/Final_Report.pdf': backendUrl,
    },
  },
})
