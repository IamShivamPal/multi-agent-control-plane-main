# Multi-Agent CI/CD System - Production Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs \
    logs/dev \
    logs/stage \
    logs/prod \
    logs/dev/performance \
    insightflow \
    apps/registry \
    orchestrator \
    core \
    agents \
    dashboard \
    samples

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379

# Expose ports
EXPOSE 8501 8080 5000

# Health check (default for main service)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/app/logs') else 1)"

# Default command - Flask API server with Gunicorn
# Note: render.yaml startCommand will override this with proper port binding
CMD ["gunicorn", "wsgi:app", "--workers", "1", "--timeout", "120"]