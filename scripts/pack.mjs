// pack.mjs : fabrique le contexte à coller dans un LLM de discussion (sans accès au dépôt).
//
//   node scripts/pack.mjs r2          pack complet du rôle (début de conversation)      -> context/r2.md
//   node scripts/pack.mjs r2 --diff   seulement les fichiers modifiés depuis le dernier pack -> context/r2-diff.md
//   node scripts/pack.mjs r2 --diff <ref>   ... depuis un commit donné (ex. HEAD~3, origin/main)
//
// Le pack complet contient CLAUDE.md, la dernière passation, les notes du rôle, ses fichiers et les
// contrats qu'il lit. Il n'inclut jamais le cahier (.tex, .pdf), les fichiers de verrouillage ni les
// fixtures de développement : ils coûtent beaucoup de tokens et n'aident pas à coder.

import { execFileSync, spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'

const COMMON = ['CLAUDE.md', 'docs/passation.md']

const ROLES = {
  r1: [
    'backend/**', 'scripts/**', 'tests/**', 'pyproject.toml', 'Dockerfile',
    'experiments/**', 'frontend/src/lib/views.ts',
  ],
  r2: [
    'experiments/**', 'backend/methods/**',
    'backend/engine/method_contract.py', 'backend/engine/laws.py', 'backend/engine/aggregators.py',
    'backend/engine/schema.py', 'tests/test_experiments.py', 'tests/test_method_contract.py',
    'tests/conftest.py', 'pyproject.toml',
  ],
  r3: [
    'frontend/src/**', 'frontend/package.json', 'frontend/vite.config.ts', 'frontend/scripts/**',
    'scripts/gen_types.sh', 'backend/contracts.py',
  ],
  r4: [
    'frontend/src/App.svelte', 'frontend/src/components/_Modele.svelte',
    'frontend/src/components/home/**', 'frontend/src/components/summary/**',
    'frontend/src/components/ImportView.svelte',
    'frontend/src/lib/calibration.ts', 'frontend/src/lib/roles.ts', 'frontend/src/lib/views.ts',
    'frontend/src/lib/types.gen.ts', 'frontend/src/styles/**', 'frontend/src/fixtures/**',
    'frontend/package.json', 'tests/test_loader.py', 'backend/engine/loader.py',
    'experiments/regression_lineaire.yaml',
  ],
}

const ALWAYS_IGNORE = [
  'docs/*.pdf', 'docs/*.tex', '**/uv.lock', '**/package-lock.json', '**/*.svg', '**/*.png',
  'frontend/src/dev/**', 'repomix-output.*', 'context/**', '**/node_modules/**', '**/.gitkeep',
]

const [role, flag, ref] = process.argv.slice(2)
if (!ROLES[role]) {
  console.error('Usage : node scripts/pack.mjs <r1|r2|r3|r4> [--diff [ref]]')
  process.exit(1)
}

mkdirSync('context', { recursive: true })
const lastFile = `context/.last-${role}`
const head = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
const repomix = ['-y', 'repomix@1.19.0', '--style', 'markdown', '--no-file-summary', '--ignore', ALWAYS_IGNORE.join(',')]

let result
if (flag === '--diff') {
  const since = ref ?? (existsSync(lastFile) ? readFileSync(lastFile, 'utf8').trim() : null)
  if (!since) {
    console.error(`Aucun pack précédent pour ${role} : lancez d'abord « node scripts/pack.mjs ${role} », ou donnez un commit.`)
    process.exit(1)
  }
  // Fichiers modifiés depuis `since`, commités ou non, qui existent encore.
  const changed = new Set([
    ...execFileSync('git', ['diff', '--name-only', since], { encoding: 'utf8' }).split('\n'),
    ...execFileSync('git', ['ls-files', '--others', '--exclude-standard'], { encoding: 'utf8' }).split('\n'),
  ])
  const files = [...changed].filter((f) => f && existsSync(f))
  if (files.length === 0) {
    console.log(`Rien n'a changé depuis ${since.slice(0, 7)}.`)
    process.exit(0)
  }
  const out = `context/${role}-diff.md`
  result = spawnSync('npx', [...repomix, '--stdin', '--no-directory-structure', '-o', out], {
    input: files.join('\n'), stdio: ['pipe', 'inherit', 'inherit'], shell: true,
  })
  console.log(`\n${out} : fichiers modifiés depuis ${since.slice(0, 7)}.`)
} else {
  const include = [...COMMON, `docs/notes/${role}.md`, ...ROLES[role]].join(',')
  const out = `context/${role}.md`
  result = spawnSync('npx', [...repomix, '--include', `"${include}"`, '-o', out], { stdio: 'inherit', shell: true })
  console.log(`\n${out} : pack complet de ${role}.`)
}

if (result.status === 0) writeFileSync(lastFile, head)
process.exit(result.status ?? 1)
