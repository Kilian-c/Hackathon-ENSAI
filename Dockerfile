# Crash-Test : une seule image (interface + moteur) pour Hugging Face Spaces (sdk: docker).
# Le moteur sert l'interface construite sur / et l'API sur /api (backend/main.py, mount_frontend) :
# une seule adresse, aucun CORS à régler. Guide : frontend/DEPLOIEMENT.md, section « Hugging Face Spaces ».
#
#   docker build -t crash-test --build-arg VITE_SUPABASE_URL=... --build-arg VITE_SUPABASE_ANON_KEY=... .
#   docker run --rm -p 7860:7860 crash-test        puis http://127.0.0.1:7860/

# --- 1. Interface (Svelte + Vite) -------------------------------------------------------------------
FROM node:24-slim AS interface
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# L'écran Import lit deux YAML d'exemple dans ../experiments au moment du build.
COPY experiments/ /app/experiments/
# Partage Supabase (facultatif) : adresse du projet et clé PUBLIQUE (anon ou sb_publishable_...), jamais la
# clé service_role. Sur Hugging Face : Settings > Variables (passées au build). Vides : partage grisé.
ARG VITE_SUPABASE_URL=""
ARG VITE_SUPABASE_ANON_KEY=""
# VITE_API_URL vide : l'interface appelle /api sur le même serveur.
ENV VITE_API_URL="" \
    VITE_SUPABASE_URL=${VITE_SUPABASE_URL} \
    VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY}
RUN npm run build

# --- 2. Moteur (FastAPI, NumPy, SciPy) ----------------------------------------------------------------
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv

# OMP_NUM_THREADS=1 et apparentés : calcul déterministe (CLAUDE.md, section 6).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PORT=7860

# Hugging Face lance le conteneur avec l'utilisateur 1000.
RUN useradd --create-home --uid 1000 user
WORKDIR /app

# Dépendances d'abord (couche en cache tant que uv.lock ne change pas), sans les outils de développement.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/ backend/
COPY experiments/ experiments/
COPY --from=interface /app/frontend/dist frontend/dist
RUN chown -R user:user /app

USER user
ENV PATH="/app/.venv/bin:${PATH}"
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"7860\")}/api/health', timeout=4)" || exit 1

# Un seul processus : le cache du moteur et le registre des imports sont en mémoire.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860} --proxy-headers --forwarded-allow-ips='*'"]
