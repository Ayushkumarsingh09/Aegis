import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/quant-api': { target: 'http://localhost:8090', rewrite: p => p.replace(/^\/quant-api/, '') },
      '/exchange-api': { target: 'http://localhost:9080', rewrite: p => p.replace(/^\/exchange-api/, '') },
    },
  },
})
