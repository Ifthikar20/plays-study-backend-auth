# Production Dockerfile for PlayStudy Backend (Django)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Collect static files
RUN python manage.py collectstatic --noinput 2>/dev/null || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)"

# Run migrations, seed demo, then start gunicorn
CMD ["sh", "-c", "python manage.py migrate --run-syncdb && python seed_demo.py && gunicorn playstudy.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120"]
