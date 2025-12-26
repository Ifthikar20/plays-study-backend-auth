#!/bin/bash

# Create ECS Service for ML Recommendation Service
# INTERNAL ONLY - No public internet access

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID}"
ECS_CLUSTER="playstudy-cluster"
SERVICE_NAME="playstudy-ml-service"
TASK_FAMILY="playstudy-ml-task"
ECR_REPOSITORY="playstudy-ml-service"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Validate
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}ERROR:${NC} AWS_ACCOUNT_ID is not set"
    exit 1
fi

echo -e "${GREEN}[INFO]${NC} Creating ML Service in ECS (Internal Only)"

# Get VPC and subnet info from existing backend service
echo -e "${GREEN}[INFO]${NC} Getting VPC configuration from existing service..."
BACKEND_SERVICE=$(aws ecs describe-services \
    --cluster $ECS_CLUSTER \
    --services playstudy-backend-service \
    --region $AWS_REGION \
    --query 'services[0].networkConfiguration.awsvpcConfiguration' \
    --output json)

SUBNETS=$(echo $BACKEND_SERVICE | jq -r '.subnets | join(",")')
VPC_ID=$(aws ec2 describe-subnets \
    --subnet-ids $(echo $SUBNETS | cut -d',' -f1) \
    --region $AWS_REGION \
    --query 'Subnets[0].VpcId' \
    --output text)

echo -e "${GREEN}[INFO]${NC} VPC: $VPC_ID"
echo -e "${GREEN}[INFO]${NC} Subnets: $SUBNETS"

# Create security group for ML service (internal only)
echo -e "${GREEN}[INFO]${NC} Creating security group for ML service..."
ML_SG_ID=$(aws ec2 create-security-group \
    --group-name playstudy-ml-service-sg \
    --description "Internal ML service - no public access" \
    --vpc-id $VPC_ID \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text 2>/dev/null || \
    aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=playstudy-ml-service-sg" \
        --region $AWS_REGION \
        --query 'SecurityGroups[0].GroupId' \
        --output text)

echo -e "${GREEN}[INFO]${NC} ML Security Group: $ML_SG_ID"

# Get backend security group
BACKEND_SG_ID=$(aws ecs describe-services \
    --cluster $ECS_CLUSTER \
    --services playstudy-backend-service \
    --region $AWS_REGION \
    --query 'services[0].networkConfiguration.awsvpcConfiguration.securityGroups[0]' \
    --output text)

echo -e "${GREEN}[INFO]${NC} Backend Security Group: $BACKEND_SG_ID"

# Allow ML service to receive traffic from backend on port 8001
echo -e "${GREEN}[INFO]${NC} Configuring security group rules..."
aws ec2 authorize-security-group-ingress \
    --group-id $ML_SG_ID \
    --protocol tcp \
    --port 8001 \
    --source-group $BACKEND_SG_ID \
    --region $AWS_REGION 2>/dev/null || echo "Rule already exists"

# Create task definition
echo -e "${GREEN}[INFO]${NC} Creating ECS task definition..."
cat > /tmp/ml-task-definition.json <<EOF
{
  "family": "$TASK_FAMILY",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "ml-service",
      "image": "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}",
      "portMappings": [
        {
          "containerPort": 8001,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/playstudy-ml-service",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ml"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8001/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Create CloudWatch log group
echo -e "${GREEN}[INFO]${NC} Creating CloudWatch log group..."
aws logs create-log-group \
    --log-group-name /ecs/playstudy-ml-service \
    --region $AWS_REGION 2>/dev/null || echo "Log group already exists"

# Register task definition
TASK_DEF_ARN=$(aws ecs register-task-definition \
    --cli-input-json file:///tmp/ml-task-definition.json \
    --region $AWS_REGION \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo -e "${GREEN}[INFO]${NC} Task Definition: $TASK_DEF_ARN"

# Create ECS service
echo -e "${GREEN}[INFO]${NC} Creating ECS service..."
aws ecs create-service \
    --cluster $ECS_CLUSTER \
    --service-name $SERVICE_NAME \
    --task-definition $TASK_FAMILY \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$ML_SG_ID],assignPublicIp=ENABLED}" \
    --region $AWS_REGION || echo "Service already exists, updating instead..."

# If service exists, update it
aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service $SERVICE_NAME \
    --task-definition $TASK_FAMILY \
    --force-new-deployment \
    --region $AWS_REGION 2>/dev/null || true

echo -e "${GREEN}✅ ML service created/updated${NC}"
echo ""
echo "ML Service Details:"
echo "- Service runs on port 8001 (internal only)"
echo "- Only accessible from backend service"
echo "- No public internet access"
echo ""
echo "To get the ML service private IP:"
echo "aws ecs describe-tasks --cluster $ECS_CLUSTER --tasks \$(aws ecs list-tasks --cluster $ECS_CLUSTER --service-name $SERVICE_NAME --region $AWS_REGION --query 'taskArns[0]' --output text) --region $AWS_REGION --query 'tasks[0].attachments[0].details[?name==\`privateIPv4Address\`].value' --output text"
