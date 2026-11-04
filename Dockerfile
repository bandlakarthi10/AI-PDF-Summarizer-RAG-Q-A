# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /build

COPY frontend/package*.json ./
RUN npm ci --prefer-offline --no-audit

COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies (build-essential for compiling, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy source code and configuration
COPY backend /app/backend

# Copy built frontend assets from stage 1
COPY --from=frontend-builder /build/dist /app/frontend/dist

# Production environment settings
ENV PYTHONPATH=/app/backend
ENV APP_ENV=production
ENV DATA_DIR=/app/data

EXPOSE 8000

# Health check to ensure service is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]
