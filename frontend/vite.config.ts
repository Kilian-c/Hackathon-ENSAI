import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig, loadEnv } from 'vite'

// En local, /api est relayé vers le moteur FastAPI (port 8000).
// En ligne, l'adresse du moteur est lue dans VITE_API_URL par lib/executor.ts,
// celle de Supabase dans VITE_SUPABASE_URL et VITE_SUPABASE_ANON_KEY par lib/share.ts.

// Cible du relais local. 127.0.0.1 plutôt que localhost : sous Windows, « localhost » est d'abord
// essayé en IPv6 (::1), où uvicorn n'écoute pas par défaut, et chaque requête perdait environ 2 s.
// Pour une autre cible (autre port, autre machine, moteur en IPv6) : API_PROXY_TARGET, dans
// frontend/.env ou au lancement (API_PROXY_TARGET=http://localhost:9000 npm run dev).
const DEFAULT_PROXY_TARGET = 'http://127.0.0.1:8000'

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = (env.API_PROXY_TARGET || DEFAULT_PROXY_TARGET).replace(/\/$/, '')
  if (command === 'serve') {
    const how = env.API_PROXY_TARGET ? 'réglé par API_PROXY_TARGET' : 'par défaut ; API_PROXY_TARGET pour changer'
    console.info(`\n  Crash-Test : /api relayé vers ${target} (${how})\n`)
  }

  return {
    plugins: [svelte()],
    server: {
      // L'écran Import lit deux YAML d'exemple dans ../experiments (lib/importPrompt.ts).
      fs: { allow: ['..'] },
      proxy: {
        '/api': {
          target,
          configure: (proxy) => {
            // Moteur injoignable : un message qui dit quoi faire, plutôt qu'une pile d'erreurs.
            let warned = 0
            proxy.on('error', (err: NodeJS.ErrnoException) => {
              const now = Date.now()
              if (now - warned < 10_000) return // un seul message toutes les 10 s
              warned = now
              console.warn(
                `\n  Crash-Test : le moteur ne répond pas sur ${target} (${err.code ?? err.message}).\n` +
                  '  Lancez-le : uv run uvicorn backend.main:app --reload --port 8000\n' +
                  '  S’il tourne ailleurs, indiquez son adresse dans API_PROXY_TARGET (frontend/.env).\n',
              )
            })
          },
        },
      },
    },
  }
})
