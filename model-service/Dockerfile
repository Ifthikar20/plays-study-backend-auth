# Internal ML Recommendation Service
# NOT exposed to public internet

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app /app/app

# Expose internal port (only accessible within VPC)
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/health')"

# Run service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
