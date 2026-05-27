# Single-image deploy: build the React app, copy it into backend/static/,
# install Python deps, run Alembic on boot, serve FastAPI on $PORT.
# FastAPI's StaticFiles mount in app/main.py serves the bundle at /,
# API routes live under /api/*. One service, one URL, no CORS in prod.

# --- Stage 1: build the React frontend ---
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# Build args let Railway inject the publishable key at build time. Vite
# inlines VITE_ vars into the bundle, so they must exist during `npm run build`.
ARG VITE_CLERK_PUBLISHABLE_KEY
ARG VITE_API_URL=""
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# --- Stage 2: Python backend + bundled frontend ---
FROM python:3.12-slim AS runtime

# Don't run as root.
RUN useradd --create-home --shell /bin/bash app
WORKDIR /app

# System deps for psycopg's binary wheels — small, just need libpq's friends.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
# Frontend build artifacts go where main.py's StaticFiles expects them.
COPY --from=frontend-build /app/frontend/dist ./backend/static

WORKDIR /app/backend
USER app

ENV PYTHONUNBUFFERED=1
ENV APP_ENV=prod

# Railway sets $PORT. Run migrations first, then the app.
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
