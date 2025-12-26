# ML Recommendations Feature Flag

## Overview

You can now **temporarily disable ML-based recommendations** using the `ENABLE_ML_RECOMMENDATIONS` environment variable.

When disabled, the system gracefully falls back to **popular games** (based on ratings and likes).

---

## Configuration

### Environment Variable

```bash
ENABLE_ML_RECOMMENDATIONS=true   # Default: ML recommendations enabled
ENABLE_ML_RECOMMENDATIONS=false  # ML recommendations disabled, use fallback
```

---

## How It Works

### When ML is **ENABLED** (default):
1. Analyzes user's play history
2. Calls internal ML service
3. Returns personalized recommendations using content-based filtering
4. If ML service fails, automatically falls back to popular games

### When ML is **DISABLED**:
1. Skips ML service entirely
2. Returns popular games user hasn't played
3. Popularity = `rating × likes`
4. No ML dependencies required

---

## Usage

### Local Development (Docker Compose)

**Disable ML:**
```bash
# Set environment variable
export ENABLE_ML_RECOMMENDATIONS=false

# Start services
docker-compose up
```

**Or set in docker-compose.yml:**
```yaml
environment:
  ENABLE_ML_RECOMMENDATIONS: "false"
```

### Local Development (Python)

```bash
export ENABLE_ML_RECOMMENDATIONS=false
./run-local.sh
```

### AWS ECS Deployment

**Disable ML temporarily:**
```bash
cd deploy
export ENABLE_ML_RECOMMENDATIONS=false
export ML_SERVICE_URL="http://dummy:8001"  # Not needed when disabled
./deploy.sh
```

**Enable ML (default):**
```bash
cd deploy
export ENABLE_ML_RECOMMENDATIONS=true
export ML_SERVICE_URL="http://172.31.x.x:8001"  # Actual ML service IP
./deploy.sh
```

---

## Testing

### Test with ML Enabled

```bash
# Start both services
docker-compose up

# Test endpoint
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/recommendations/similar?limit=6"
```

**Response:** Personalized ML-based recommendations

### Test with ML Disabled

```bash
# Disable ML
export ENABLE_ML_RECOMMENDATIONS=false
docker-compose up

# Test endpoint
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/recommendations/similar?limit=6"
```

**Response:** Popular games (fallback)

---

## API Behavior

All endpoints respect the `ENABLE_ML_RECOMMENDATIONS` flag:

### `GET /api/recommendations/similar`

**ML Enabled:**
```json
[
  {
    "id": 15,
    "title": "Calculus Challenge",
    "category": "Math",
    "difficulty": "Hard",
    ...
  }
]
```
*← Similar to games you played*

**ML Disabled:**
```json
[
  {
    "id": 8,
    "title": "Physics Quest",
    "category": "Science",
    "difficulty": "Medium",
    ...
  }
]
```
*← Popular games you haven't played*

### `GET /api/recommendations/similar/explained`

**ML Enabled:**
```json
[
  {
    "game": { ... },
    "reason": "Similar to Algebra Quiz (same category: Math)",
    "similarity_score": 0.87
  }
]
```

**ML Disabled:**
```json
[
  {
    "game": { ... },
    "reason": "Popular game with high ratings",
    "similarity_score": 0.0
  }
]
```

### `GET /api/recommendations/favorites`

Always works the same (doesn't use ML service).

---

## Use Cases

### 1. **Testing Without ML Service**
```bash
# Test backend without starting ML service
export ENABLE_ML_RECOMMENDATIONS=false
uvicorn app.main:app --reload
```

### 2. **Gradual Rollout**
```bash
# Deploy backend first with ML disabled
export ENABLE_ML_RECOMMENDATIONS=false
./deploy.sh

# Later, deploy ML service and enable
export ENABLE_ML_RECOMMENDATIONS=true
./deploy.sh
```

### 3. **ML Service Maintenance**
```bash
# Temporarily disable during ML service updates
aws ecs update-service \
  --cluster playstudy-cluster \
  --service playstudy-backend-service \
  --task-definition playstudy-backend-task:X \
  --force-new-deployment
# (with ENABLE_ML_RECOMMENDATIONS=false in task definition)
```

### 4. **Cost Optimization**
```bash
# Disable ML service during low-traffic periods
export ENABLE_ML_RECOMMENDATIONS=false
```

---

## Fallback Logic

When ML is disabled or fails, the system uses this fallback strategy:

```python
# Fallback algorithm
def get_fallback_recommendations(user_id, limit):
    1. Get all active games
    2. Exclude games user already played
    3. Sort by popularity: rating × likes
    4. Return top N games
```

**Example:**
- User played: Game A, Game B, Game C
- All games: A, B, C, D, E, F, G
- Popularity scores:
  - D: 4.5 × 234 = 1053
  - E: 4.8 × 189 = 907
  - F: 4.2 × 312 = 1310
  - G: 3.9 × 456 = 1778
- **Returns:** [G, F, D, E]

---

## Monitoring

Check current status:

```bash
# Check if ML is enabled
curl http://localhost:8000/api/recommendations/health

# Response includes ML service status
{
  "status": "healthy",
  "ml_service": {
    "status": "healthy",
    "service": "ml-recommendation"
  }
}
```

If ML is disabled, health endpoint will show:
```json
{
  "status": "degraded",
  "ml_service": "unavailable",
  "error": "Connection refused"
}
```

But recommendations will still work (using fallback).

---

## Best Practices

1. **Always test locally first:**
   ```bash
   ENABLE_ML_RECOMMENDATIONS=false docker-compose up
   ```

2. **Use feature flag during deployment:**
   - Deploy backend with ML disabled
   - Deploy ML service
   - Re-deploy backend with ML enabled

3. **Monitor logs for fallback usage:**
   ```bash
   # Look for fallback warnings
   aws logs tail /ecs/playstudy-backend --filter "fallback" --follow
   ```

4. **Keep fallback simple:**
   - Popular games work for all users
   - No personalization = no ML needed
   - Fast and reliable

---

## Summary

| Configuration | ML Service Needed? | Recommendations | Performance |
|--------------|-------------------|-----------------|-------------|
| `ENABLE_ML_RECOMMENDATIONS=true` | ✓ Yes | Personalized | Higher latency |
| `ENABLE_ML_RECOMMENDATIONS=false` | ✗ No | Popular games | Lower latency |
| ML enabled but service down | ✗ No | Popular games (auto-fallback) | Lower latency |

**Default:** `ENABLE_ML_RECOMMENDATIONS=true` (ML enabled)
