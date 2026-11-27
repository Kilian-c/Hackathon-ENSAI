#!/usr/bin/env bash
# gen_types.sh : backend/contracts.py + ExperimentSpec (schema.py) -> frontend/src/lib/types.gen.ts (R3).
#
#   bash scripts/gen_types.sh           régénère types.gen.ts
#   bash scripts/gen_types.sh --check   échoue si types.gen.ts n'est plus à jour (pour les tests et la CI)
#
# À relancer après toute modification de contracts.py ou schema.py, et à commiter avec elle.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/frontend/src/lib/types.gen.ts"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

BANNER='/**
 * FICHIER GÉNÉRÉ par scripts/gen_types.sh depuis backend/contracts.py et backend/engine/schema.py.
 * Ne pas modifier à la main : modifiez le contrat Python, puis relancez « bash scripts/gen_types.sh ».
 */'

(cd "$ROOT" && uv run --quiet python scripts/export_schema.py "$TMP/schema.json")
(cd "$ROOT/frontend" && npx --no-install json2ts \
  --input "$TMP/schema.json" \
  --output "$TMP/body.ts" \
  --unreachableDefinitions \
  --maxItems=-1 \
  --bannerComment "")
# Le bandeau est ajouté ici : json2ts tronque les bandeaux sur plusieurs lignes.
{ printf '%s\n\n' "$BANNER"; cat "$TMP/body.ts"; } > "$TMP/types.gen.ts"

if [[ "${1:-}" == "--check" ]]; then
  if ! diff -q "$OUT" "$TMP/types.gen.ts" > /dev/null 2>&1; then
    echo "types.gen.ts n'est plus à jour : lancez « bash scripts/gen_types.sh » et commitez le résultat." >&2
    exit 1
  fi
  echo "types.gen.ts est à jour."
else
  cp "$TMP/types.gen.ts" "$OUT"
  echo "Généré : frontend/src/lib/types.gen.ts"
fi
