import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/card-maker-natsu/',
  server: {
    port: 9345,
    strictPort: true,
  },
})
