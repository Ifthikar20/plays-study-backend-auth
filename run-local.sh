#!/bin/bash

# Local Development - Run Both Services
# This script runs the ML service and main backend locally for testing

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PlayStudy Local Development${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running from repo root
if [ ! -f "requirements.txt" ]; then
    echo -e "${YELLOW}ERROR:${NC} Run this from the repository root"
    exit 1
fi

# Function to cleanup background processes
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    pkill -P $$ 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${GREEN}[1/4]${NC} Installing main backend dependencies..."
pip install -r requirements.txt -q

echo -e "${GREEN}[2/4]${NC} Installing ML service dependencies..."
pip install -r model-service/requirements.txt -q

echo -e "${GREEN}[3/4]${NC} Starting ML service on port 8001..."
cd model-service
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload > /tmp/ml-service.log 2>&1 &
ML_PID=$!
cd ..

# Wait for ML service to start
echo -n "   Waiting for ML service to be ready"
for i in {1..10}; do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

echo -e "${GREEN}[4/4]${NC} Starting main backend on port 8000..."
export ML_SERVICE_URL="http://localhost:8001"
export DATABASE_URL="${DATABASE_URL:-postgresql://playstudy_admin:yourpassword@localhost:5432/postgres}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export ALLOWED_ORIGINS="http://localhost:8080,http://localhost:3000"
export SECRET_KEY="dev-secret-key"
export FIELD_ENCRYPTION_KEY="dev-encryption-key"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Services Running${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "  Main Backend:  ${GREEN}http://localhost:8000${NC}"
echo -e "  ML Service:    ${GREEN}http://localhost:8001${NC} (internal)"
echo -e "  API Docs:      ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo -e "  ML Service Logs: tail -f /tmp/ml-service.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
