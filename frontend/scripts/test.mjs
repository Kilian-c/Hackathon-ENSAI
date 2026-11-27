// Lance Vitest depuis un chemin dont la lettre de lecteur est en majuscule (C: et non c:).
// Sous Windows, VS Code ouvre parfois le terminal en « c:\... » : Vitest charge alors deux fois
// le même module et tous les tests échouent avec « Cannot read properties of undefined (reading 'config') ».
import { spawnSync } from 'node:child_process'

const cwd = process.cwd().replace(/^[a-z]:/, (d) => d.toUpperCase())
const r = spawnSync('npx', ['vitest', 'run', ...process.argv.slice(2)], { cwd, stdio: 'inherit', shell: true })
process.exit(r.status ?? 1)
