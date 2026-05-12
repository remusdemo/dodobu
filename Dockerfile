# ---- Stage 1: Frontend build ----
FROM node:20-alpine AS frontend

WORKDIR /build
COPY frontend/package*.json .
RUN npm ci
COPY frontend/ .
RUN npm run build

# ---- Stage 2: Python runtime ----
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY --from=frontend /build/dist frontend/dist/

EXPOSE 5000

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} backend.app:app"]
