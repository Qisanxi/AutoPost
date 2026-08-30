import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: false,  // Disable source maps in production for security
  },
  server: {
    port: 5173,
    strictPort: true,
  },
})
