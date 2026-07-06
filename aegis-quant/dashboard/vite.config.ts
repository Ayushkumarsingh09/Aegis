import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 4100,
    proxy: {
      '/api': 'http://localhost:8090',
      '/health': 'http://localhost:8090',
      '/metrics': 'http://localhost:8090',
    },
  },
})
