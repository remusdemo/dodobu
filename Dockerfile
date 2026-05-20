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
COPY db/ db/
COPY start.sh .
COPY worker.py .
RUN chmod +x start.sh

EXPOSE 5000

CMD ["./start.sh"]
