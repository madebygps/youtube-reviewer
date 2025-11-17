import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // Listen on all network interfaces
    strictPort: true,
    watch: {
      usePolling: true  // Required for file watching in some environments
    },
    proxy: {
      // Proxy API calls to the app service
      '/api': {
        target: process.env.services__app__https__0 || process.env.services__app__http__0 || 'http://localhost:8000',
        changeOrigin: true
      },
      // Proxy insights generation endpoint
      '/generateinsights': {
        target: process.env.services__app__https__0 || process.env.services__app__http__0 || 'http://localhost:8000',
        changeOrigin: true
      },
      // Proxy WebSocket connections
      '/ws': {
        target: process.env.services__app__https__0 || process.env.services__app__http__0 || 'http://localhost:8000',
        changeOrigin: true,
        ws: true
      },
      // Proxy health check endpoint
      '/health': {
        target: process.env.services__app__https__0 || process.env.services__app__http__0 || 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
