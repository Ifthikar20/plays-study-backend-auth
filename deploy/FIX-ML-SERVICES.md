# Fix ML Services - Task Definition Placeholder Issue

## Problem

The ECS service is failing with the error:
```
failed to normalize image reference "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/playstudy-backend:latest"
```

This happens because the task definition file (`ecs-task-definition.json`) contains placeholder values like `YOUR_ACCOUNT_ID` that need to be replaced with actual values.

## Root Cause

The `ecs-task-definition.json` file has multiple placeholders:
- ✗ `YOUR_ACCOUNT_ID` in the ECR image URI (line 12)
- ✗ `YOUR_ACCOUNT_ID` in IAM role ARNs (lines 7-8)
- ✗ `YOUR_ACCOUNT_ID` in all secrets ARNs (lines 61, 65, 69, 73, 77, 81, 85)
- ✗ `ML_SERVICE_IP` in ML_SERVICE_URL (line 51)
- ⚠️  Other environment variables may need updating depending on your setup

## Solution

Use the new `fix-all-placeholders.sh` script which automatically:

1. ✓ Detects your AWS Account ID
2. ✓ Extracts correct IAM roles from the running task definition
3. ✓ Gets the ML service private IP address
4. ✓ Preserves existing environment variables (DATABASE_URL, REDIS_URL, ALLOWED_ORIGINS)
5. ✓ Replaces all placeholders in the task definition
6. ✓ Registers the updated task definition with ECS
7. ✓ Updates the service to use the new task definition

## Quick Fix

### Run from the deploy directory:

```bash
cd /path/to/plays-study-backend-auth/deploy
./fix-all-placeholders.sh
```

The script will:
- Automatically detect your AWS account ID (817977750104)
- Fix all `YOUR_ACCOUNT_ID` placeholders
- Get the ML service IP and update ML_SERVICE_URL
- Preserve your existing database, Redis, and CORS configurations
- Register and deploy the fixed task definition

## What Gets Fixed

### Before:
```json
{
  "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/playstudy-backend:latest",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "environment": [
    {
      "name": "ML_SERVICE_URL",
      "value": "http://ML_SERVICE_IP:8001"
    }
  ],
  "secrets": [
    {
      "name": "SECRET_KEY",
      "valueFrom": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT_ID:secret:playstudy/secret-key"
    }
  ]
}
```

### After:
```json
{
  "image": "817977750104.dkr.ecr.us-east-1.amazonaws.com/playstudy-backend:latest",
  "executionRoleArn": "arn:aws:iam::817977750104:role/ecsTaskExecutionRole",
  "environment": [
    {
      "name": "ML_SERVICE_URL",
      "value": "http://10.0.1.123:8001"
    }
  ],
  "secrets": [
    {
      "name": "SECRET_KEY",
      "valueFrom": "arn:aws:secretsmanager:us-east-1:817977750104:secret:playstudy/secret-key"
    }
  ]
}
```

## Monitoring

After running the script, monitor the deployment:

```bash
# Watch service status
aws ecs describe-services \
    --cluster playstudy-cluster \
    --services playstudy-backend-service \
    --region us-east-1 \
    --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Events:events[0:3]}' \
    --output table

# Check task logs
aws logs tail /ecs/playstudy-backend --follow

# Verify ML service is accessible
aws ecs list-tasks \
    --cluster playstudy-cluster \
    --service-name playstudy-ml-service \
    --region us-east-1
```

## Expected Results

After running the fix:
- ✓ Tasks should start successfully (no more "failed to normalize image" errors)
- ✓ runningCount should increase to 1
- ✓ Service status should remain "ACTIVE"
- ✓ Health checks should pass after ~60 seconds

## Troubleshooting

### If ML service IP is not found:

The script will use a placeholder. After the ML service is running:
```bash
./update-ml-service-url.sh
```

### If you need to update other environment variables:

Check the current running configuration:
```bash
aws ecs describe-task-definition \
    --task-definition playstudy-backend:5 \
    --query 'taskDefinition.containerDefinitions[0].environment' \
    --output table
```

Then update specific variables using the dedicated scripts:
- `update-database-url.sh` - For DATABASE_URL
- `update-cors-origins.sh` - For ALLOWED_ORIGINS
- `update-ml-service-url.sh` - For ML_SERVICE_URL

### If tasks still fail to start:

1. Check the CloudWatch logs:
   ```bash
   aws logs tail /ecs/playstudy-backend --follow
   ```

2. Verify the ECR repository exists:
   ```bash
   aws ecr describe-repositories \
       --repository-names playstudy-backend \
       --region us-east-1
   ```

3. Check if the image exists:
   ```bash
   aws ecr describe-images \
       --repository-name playstudy-backend \
       --region us-east-1
   ```

## Cleanup

After successful deployment:
```bash
rm ecs-task-definition-temp.json
```

## Additional Notes

- The script preserves your existing environment configuration
- IAM roles are extracted from the current running task definition
- All AWS Secrets Manager references are automatically updated
- The original `ecs-task-definition.json` file is not modified (updates go to temp file)
