// pack.mjs : fabrique le contexte à coller dans un LLM de discussion (sans accès au dépôt).
//
//   node scripts/pack.mjs r2            pack hybride (par défaut)                       -> context/r2.md
//                                       A. CLAUDE.md, passation, notes et fichiers du rôle, EN ENTIER
//                                       B. tout le reste du dépôt, COMPRESSÉ (signatures, types, docstrings)
//   node scripts/pack.mjs r2 --full     tout le dépôt en entier (si la fenêtre du LLM le permet)
//   node scripts/pack.mjs r2 --diff     seulement les fichiers modifiés depuis le dernier pack -> context/r2-diff.md
//   node scripts/pack.mjs r2 --diff <ref>   ... depuis un commit donné (ex. HEAD~3, origin/main)
//
// Ce qui est exclu de tout export (cahier, fichiers de verrouillage, images...) est dans .repomixignore.

import { execFileSync, spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'

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
    'scripts/gen_types.sh', 'backend/contracts.py', 'experiments/regression_lineaire.yaml',
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

// Partie B seulement : configuration sans intérêt pour écrire du code cohérent.
const B_IGNORE = [
  '.gitignore', '**/.gitignore', '.gitattributes', '.python-version', '.repomixignore', 'README.md',
  'frontend/tsconfig*.json', 'frontend/svelte.config.js', 'frontend/index.html', '**/*.test.ts',
  '**/__init__.py',
]

const HEADER = (role, mode) => `# Contexte du dépôt Crash-Test pour ${role.toUpperCase()} (${mode})

Généré par \`node scripts/pack.mjs\` au commit ${head.slice(0, 7)}. Consignes pour l'assistant :
- Lis CLAUDE.md en entier : il fixe les règles, les formats et ce que chaque rôle a le droit de modifier.
- Partie A : les fichiers de mon rôle, complets. Ce sont les seuls que tu modifies.
- Partie B : le reste du dépôt, compressé (signatures, types, docstrings ; les corps de fonctions sont omis,
  signalés par ⋮----). Sers-t'en pour rester cohérent avec l'existant (noms, types, formats). Ne réécris
  jamais un fichier de la partie B : si tu as besoin de son contenu complet, demande-le-moi.
- Si une modification d'un fichier d'un autre rôle te semble nécessaire, dis-le au lieu de la faire.

`

const [role, flag, ref] = process.argv.slice(2)
if (!ROLES[role]) {
  console.error('Usage : node scripts/pack.mjs <r1|r2|r3|r4> [--full | --diff [ref]]')
  process.exit(1)
}

mkdirSync('context', { recursive: true })
const lastFile = `context/.last-${role}`
const head = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
const base = ['-y', 'repomix@1.19.0', '--style', 'markdown', '--no-file-summary', '--quiet']
const own = [...COMMON, `docs/notes/${role}.md`, ...ROLES[role]]

function repomix(args, input) {
  // Une seule chaîne de commande : npx a besoin d'un shell sous Windows (les arguments n'ont pas d'espace).
  const r = spawnSync(['npx', ...base, ...args].join(' '), {
    input, stdio: [input ? 'pipe' : 'ignore', 'inherit', 'inherit'], shell: true,
  })
  if (r.status !== 0) process.exit(r.status ?? 1)
}

function finish(out, label) {
  writeFileSync(lastFile, head)
  const text = readFileSync(out, 'utf8')
  // Estimation grossière : environ 3,5 caractères par token pour du code et du français.
  console.log(`${out} : ${label}, environ ${Math.round(text.length / 3500)} 000 tokens.`)
}

if (flag === '--diff') {
  const since = ref ?? (existsSync(lastFile) ? readFileSync(lastFile, 'utf8').trim() : null)
  if (!since) {
    console.error(`Aucun pack précédent pour ${role} : lancez d'abord « node scripts/pack.mjs ${role} », ou donnez un commit.`)
    process.exit(1)
  }
  const changed = new Set([
    ...execFileSync('git', ['diff', '--name-only', since], { encoding: 'utf8' }).split('\n'),
    ...execFileSync('git', ['ls-files', '--others', '--exclude-standard'], { encoding: 'utf8' }).split('\n'),
  ])
  const files = [...changed].filter((f) => f && existsSync(f) && !f.startsWith('context/'))
  if (files.length === 0) {
    console.log(`Rien n'a changé depuis ${since.slice(0, 7)}.`)
    process.exit(0)
  }
  const out = `context/${role}-diff.md`
  repomix(['--stdin', '--no-directory-structure', '-o', out], files.join('\n'))
  finish(out, `fichiers modifiés depuis ${since.slice(0, 7)} (complets)`)
} else if (flag === '--full') {
  const out = `context/${role}.md`
  repomix(['-o', out])
  writeFileSync(out, HEADER(role, 'dépôt complet').replace(/- Partie A[\s\S]*?- Si une/, '- Tout le dépôt est en entier ; ne modifie que les fichiers de mon rôle (CLAUDE.md, section 3).\n- Si une') + readFileSync(out, 'utf8'))
  finish(out, 'dépôt complet')
} else {
  const out = `context/${role}.md`
  const a = `context/.${role}-a.md`
  const b = `context/.${role}-b.md`
  repomix(['--include', `"${own.join(',')}"`, '--no-directory-structure', '-o', a])
  repomix(['--compress', '--ignore', `"${[...own, ...B_IGNORE].join(',')}"`, '-o', b])
  writeFileSync(
    out,
    HEADER(role, 'hybride') +
      '\n---\n\n# PARTIE A : fichiers du rôle, complets\n\n' + readFileSync(a, 'utf8') +
      '\n---\n\n# PARTIE B : reste du dépôt, compressé\n\n' + readFileSync(b, 'utf8'),
  )
  rmSync(a)
  rmSync(b)
  finish(out, 'pack hybride (rôle complet, reste compressé)')
}
