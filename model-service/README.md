# PlayStudy ML Recommendation Service

**INTERNAL SERVICE - NOT EXPOSED TO PUBLIC INTERNET**

This service handles machine learning-based game recommendations using content-based filtering with cosine similarity.

## Architecture

```
┌─────────────────────┐         ┌──────────────────────┐
│  FastAPI App        │────────▶│  ML Service          │
│  (Main Backend)     │  HTTP   │  (Internal Only)     │
│  Port 8000          │         │  Port 8001           │
│  Public Facing      │         │  VPC Private Only    │
└─────────────────────┘         └──────────────────────┘
         │
         │
         ▼
┌─────────────────────┐
│  Application Load   │
│  Balancer (ALB)     │
│  Public Internet    │
└─────────────────────┘
```

## Security Model

- **ML Service**: Only accessible from backend service within VPC
- **Main Backend**: Accessible via ALB from internet
- **Database/Redis**: Accessible from backend only

## Deployment Steps

### 1. Deploy ML Service First

```bash
cd model-service

# Set AWS account ID
export AWS_ACCOUNT_ID=817977750104

# Build and push ML service image
./deploy-ml-service.sh

# Create ECS service (first time only)
./create-ml-ecs-service.sh
```

### 2. Get ML Service Private IP

After ML service is deployed, get its private IP:

```bash
# Get task ARN
TASK_ARN=$(aws ecs list-tasks \
    --cluster playstudy-cluster \
    --service-name playstudy-ml-service \
    --region us-east-1 \
    --query 'taskArns[0]' \
    --output text)

# Get private IP
ML_SERVICE_IP=$(aws ecs describe-tasks \
    --cluster playstudy-cluster \
    --tasks $TASK_ARN \
    --region us-east-1 \
    --query 'tasks[0].attachments[0].details[?name==`privateIPv4Address`].value' \
    --output text)

echo "ML Service IP: $ML_SERVICE_IP"
```

### 3. Update Main Backend with ML Service URL

```bash
cd ../deploy

# Set ML service URL
export ML_SERVICE_URL="http://${ML_SERVICE_IP}:8001"

# Deploy main backend (will include ML_SERVICE_URL)
./deploy.sh
```

### 4. Verify Communication

Check that backend can reach ML service:

```bash
# Check ML service health from backend
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://playstudy-alb-1732754070.us-east-1.elb.amazonaws.com/api/recommendations/health
```

Expected response:
```json
{
  "status": "healthy",
  "ml_service": {
    "status": "healthy",
    "service": "ml-recommendation"
  }
}
```

## API Endpoints (Internal)

The ML service exposes these endpoints (only accessible from main backend):

### `POST /recommend`

**Request:**
```json
{
  "user_play_history": [
    {"game_id": 1, "play_count": 5},
    {"game_id": 3, "play_count": 2}
  ],
  "all_games": [
    {
      "id": 1,
      "category": "Math",
      "difficulty": "hard",
      "estimated_time": 15,
      "xp_reward": 100,
      "rating": 4.5,
      "likes": 234,
      "title": "Algebra Quiz"
    }
  ],
  "limit": 6
}
```

**Response:**
```json
{
  "game_ids": [5, 8, 12, 15, 18, 22],
  "scores": [0.87, 0.85, 0.82, 0.80, 0.78, 0.75],
  "explanations": [
    "Similar to Algebra Quiz (same category: Math)",
    "Similar to Algebra Quiz (same difficulty: hard)",
    ...
  ]
}
```

### `GET /health`

Health check endpoint for ECS.

**Response:**
```json
{
  "status": "healthy",
  "service": "ml-recommendation"
}
```

## Scaling

The ML service can be scaled independently:

```bash
aws ecs update-service \
    --cluster playstudy-cluster \
    --service playstudy-ml-service \
    --desired-count 2 \
    --region us-east-1
```

## Resource Allocation

- **CPU**: 512 (0.5 vCPU)
- **Memory**: 1024 MB (1 GB)

Adjust in `create-ml-ecs-service.sh` if needed for more complex models.

## Monitoring

View logs:

```bash
aws logs tail /ecs/playstudy-ml-service --follow --region us-east-1
```

## Future Enhancements

- Add AWS Cloud Map (Service Discovery) for automatic DNS resolution
- Use Application Load Balancer for ML service (if multiple instances)
- Add request caching in Redis
- Implement collaborative filtering
- Add A/B testing framework
