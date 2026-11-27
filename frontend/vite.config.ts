import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

// En local, /api est relayé vers le moteur FastAPI (port 8000).
// En ligne, l'adresse du moteur est lue dans VITE_API_URL par lib/executor.ts,
// celle de Supabase dans VITE_SUPABASE_URL et VITE_SUPABASE_ANON_KEY par lib/share.ts.
export default defineConfig({
  plugins: [svelte()],
  server: {
    // L'écran Import lit deux YAML d'exemple dans ../experiments (lib/importPrompt.ts).
    fs: { allow: ['..'] },
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
