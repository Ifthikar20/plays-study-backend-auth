# Update ML Service URL in ECS Task Definition

## Problem
The current ECS task definition has a placeholder `ML_SERVICE_IP` instead of the actual ML service private IP address. This means the backend cannot communicate with the ML recommendation service.

## Solution

### Option 1: Automated Script (Recommended)

Run the provided script from the `deploy/` directory:

```bash
cd deploy
./update-ml-service-url.sh
```

This script will:
1. Get the ML service's private IP address
2. Update the task definition with the real IP
3. Register the new task definition with AWS ECS
4. Update the backend service to use the new task definition
5. Trigger a new deployment

### Option 2: Manual Steps

If you prefer to do it manually:

**Step 1: Get ML Service Private IP**
```bash
# Get the ML service task ARN
TASK_ARN=$(aws ecs list-tasks \
    --cluster playstudy-cluster \
    --service-name playstudy-ml-service \
    --region us-east-1 \
    --query 'taskArns[0]' \
    --output text)

# Get the private IP
ML_IP=$(aws ecs describe-tasks \
    --cluster playstudy-cluster \
    --tasks $TASK_ARN \
    --region us-east-1 \
    --query 'tasks[0].attachments[0].details[?name==`privateIPv4Address`].value' \
    --output text)

echo "ML Service IP: $ML_IP"
```

**Step 2: Update task definition file**
```bash
# Replace ML_SERVICE_IP with actual IP
sed "s/ML_SERVICE_IP/$ML_IP/g" ecs-task-definition.json > ecs-task-definition-updated.json
```

**Step 3: Register new task definition**
```bash
aws ecs register-task-definition \
    --cli-input-json file://ecs-task-definition-updated.json \
    --region us-east-1
```

**Step 4: Update backend service**
```bash
aws ecs update-service \
    --cluster playstudy-cluster \
    --service playstudy-backend-service \
    --task-definition playstudy-backend:5 \
    --force-new-deployment \
    --region us-east-1
```

## Verification

After running the update, verify the new task definition has the ML_SERVICE_URL:

```bash
# Check the latest task definition
aws ecs describe-task-definition \
    --task-definition playstudy-backend \
    --region us-east-1 \
    --query 'taskDefinition.containerDefinitions[0].environment[?name==`ML_SERVICE_URL`]'
```

You should see output like:
```json
[
    {
        "name": "ML_SERVICE_URL",
        "value": "http://10.0.1.123:8001"
    }
]
```

## Test ML Recommendations

Once deployed, test the ML recommendation endpoints:

```bash
# Get auth token first
TOKEN="your-jwt-token"

# Test ML health check
curl -H "Authorization: Bearer $TOKEN" \
    https://your-domain.com/api/recommendations/health

# Get recommendations
curl -H "Authorization: Bearer $TOKEN" \
    https://your-domain.com/api/recommendations/similar
```

## Why This Is Needed

The ML recommendation service runs on a **private IP within the VPC**. It's not exposed to the public internet for security reasons. The backend service needs to know this private IP to make internal HTTP requests to the ML service for generating game recommendations.

Without this configuration:
- ML recommendation endpoints will fail
- The system will fall back to basic popularity-based recommendations
- You'll see "ML service unavailable" errors in logs

With this configuration:
- ML-powered personalized recommendations work
- The backend can call the ML service internally
- Users get better game recommendations based on their play history
