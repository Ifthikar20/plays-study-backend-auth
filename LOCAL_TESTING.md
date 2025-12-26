# Local Testing Guide

Test the recommendation system locally before deploying to AWS.

## Option 1: Docker Compose (Recommended)

**Runs everything:** Postgres, Redis, ML Service, Backend

```bash
# Start all services
docker-compose up --build

# In another terminal, run tests
./test-recommendations.sh
```

**Services:**
- Main Backend: http://localhost:8000
- ML Service: http://localhost:8001 (internal)
- Postgres: localhost:5432
- Redis: localhost:6379
- API Docs: http://localhost:8000/docs

**Stop services:**
```bash
docker-compose down
```

## Option 2: Run Without Docker

**Prerequisites:** Python 3.11+, Postgres, Redis running locally

```bash
# Install dependencies and run both services
./run-local.sh
```

This will:
1. Install main backend dependencies
2. Install ML service dependencies
3. Start ML service on port 8001
4. Start main backend on port 8000

**Manual setup (if script doesn't work):**

```bash
# Terminal 1: Start ML Service
cd model-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2: Start Main Backend
export ML_SERVICE_URL="http://localhost:8001"
export DATABASE_URL="postgresql://playstudy_user:dev_password_change_in_production@localhost:5432/playstudy_db"
export REDIS_URL="redis://localhost:6379/0"
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Testing

### 1. Quick Health Check

```bash
# ML Service
curl http://localhost:8001/health

# Backend
curl http://localhost:8000/health

# Backend → ML Service Integration
curl http://localhost:8000/api/recommendations/health
```

### 2. Run Full Test Suite

```bash
./test-recommendations.sh
```

This tests:
- ✓ ML service health
- ✓ Backend health
- ✓ ML service direct calls
- ✓ Backend to ML service integration
- ✓ End-to-end recommendations (requires JWT token)

### 3. Test ML Service Directly

```bash
curl -X POST http://localhost:8001/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_play_history": [
      {"game_id": 1, "play_count": 5}
    ],
    "all_games": [
      {
        "id": 1, "category": "Math", "difficulty": "hard",
        "estimated_time": 15, "xp_reward": 100,
        "rating": 4.5, "likes": 234, "title": "Algebra Quiz"
      },
      {
        "id": 2, "category": "Math", "difficulty": "medium",
        "estimated_time": 10, "xp_reward": 80,
        "rating": 4.3, "likes": 189, "title": "Geometry Basics"
      }
    ],
    "limit": 1
  }'
```

**Expected response:**
```json
{
  "game_ids": [2],
  "scores": [0.85],
  "explanations": ["Similar to Algebra Quiz (same category: Math)"]
}
```

### 4. Test Via Main Backend (Requires Auth)

First, create a user and login:

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "testpass123"
  }'

# Login
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }' | jq -r '.access_token')

echo "JWT Token: $TOKEN"
```

Then test recommendations:

```bash
# Get similar games
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/recommendations/similar?limit=6"

# Get with explanations
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/recommendations/similar/explained?limit=6"

# Get user's favorites
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/recommendations/favorites?limit=5"
```

## View Logs

**Docker Compose:**
```bash
# All logs
docker-compose logs -f

# Just ML service
docker-compose logs -f ml-service

# Just backend
docker-compose logs -f backend
```

**Without Docker:**
```bash
# ML service logs
tail -f /tmp/ml-service.log

# Backend logs (in terminal where it's running)
```

## Troubleshooting

### ML Service not responding
```bash
# Check if running
curl http://localhost:8001/health

# Check Docker container
docker-compose ps ml-service

# View logs
docker-compose logs ml-service
```

### Backend can't reach ML Service
```bash
# Test integration
curl http://localhost:8000/api/recommendations/health

# Should show:
# {"status": "healthy", "ml_service": {"status": "healthy", ...}}
```

### "503 ML service unavailable"
- Make sure ML service is running on port 8001
- Check ML_SERVICE_URL environment variable is set correctly
- Verify network connectivity between services

## Next Steps

Once local testing passes:

1. ✓ Verify all tests pass with `./test-recommendations.sh`
2. ✓ Test with real user data from your database
3. ✓ Deploy to AWS using deployment scripts
4. ✓ Update frontend to call the new endpoints
