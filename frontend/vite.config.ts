import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

// En local, /api est relayé vers le moteur FastAPI (port 8000).
// En ligne, l'adresse du moteur est lue dans VITE_API_URL par lib/executor.ts.
export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
