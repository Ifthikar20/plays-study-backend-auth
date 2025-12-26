#!/bin/bash

# Fix IAM roles in task definition and update ML service URL
# This script gets the correct role ARNs from the running task definition

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="playstudy-cluster"
ML_SERVICE="playstudy-ml-service"
BACKEND_SERVICE="playstudy-backend-service"

echo -e "${GREEN}[1/6]${NC} Getting current task definition roles..."
CURRENT_TASK_DEF=$(aws ecs describe-services \
    --cluster $ECS_CLUSTER \
    --services $BACKEND_SERVICE \
    --region $AWS_REGION \
    --query 'services[0].taskDefinition' \
    --output text)

echo "Current task definition: $CURRENT_TASK_DEF"

# Get the actual role ARNs from the current task definition
EXECUTION_ROLE=$(aws ecs describe-task-definition \
    --task-definition $CURRENT_TASK_DEF \
    --region $AWS_REGION \
    --query 'taskDefinition.executionRoleArn' \
    --output text)

TASK_ROLE=$(aws ecs describe-task-definition \
    --task-definition $CURRENT_TASK_DEF \
    --region $AWS_REGION \
    --query 'taskDefinition.taskRoleArn' \
    --output text)

echo -e "${GREEN}✓${NC} Execution Role: $EXECUTION_ROLE"
echo -e "${GREEN}✓${NC} Task Role: $TASK_ROLE"

echo -e "${GREEN}[2/6]${NC} Getting ML service task ARN..."
TASK_ARN=$(aws ecs list-tasks \
    --cluster $ECS_CLUSTER \
    --service-name $ML_SERVICE \
    --region $AWS_REGION \
    --query 'taskArns[0]' \
    --output text)

if [ -z "$TASK_ARN" ] || [ "$TASK_ARN" == "None" ]; then
    echo -e "${YELLOW}ERROR:${NC} ML service task not found. Is it running?"
    exit 1
fi

echo -e "${GREEN}[3/6]${NC} Getting ML service private IP..."
ML_PRIVATE_IP=$(aws ecs describe-tasks \
    --cluster $ECS_CLUSTER \
    --tasks $TASK_ARN \
    --region $AWS_REGION \
    --query 'tasks[0].attachments[0].details[?name==`privateIPv4Address`].value' \
    --output text)

if [ -z "$ML_PRIVATE_IP" ]; then
    echo -e "${YELLOW}ERROR:${NC} Could not get ML service private IP"
    exit 1
fi

echo -e "${GREEN}✓${NC} ML Service Private IP: $ML_PRIVATE_IP"

echo -e "${GREEN}[4/6]${NC} Updating task definition file..."
# Create a copy with all placeholders replaced
cp ecs-task-definition.json ecs-task-definition-temp.json

# Replace ML_SERVICE_IP with actual IP
sed -i.bak "s|ML_SERVICE_IP|$ML_PRIVATE_IP|g" ecs-task-definition-temp.json

# Replace role ARNs
sed -i.bak "s|\"executionRoleArn\": \".*\"|\"executionRoleArn\": \"$EXECUTION_ROLE\"|g" ecs-task-definition-temp.json
sed -i.bak "s|\"taskRoleArn\": \".*\"|\"taskRoleArn\": \"$TASK_ROLE\"|g" ecs-task-definition-temp.json

# Remove backup files
rm -f ecs-task-definition-temp.json.bak

echo -e "${GREEN}[5/6]${NC} Registering new task definition with AWS ECS..."
NEW_TASK_DEF=$(aws ecs register-task-definition \
    --cli-input-json file://ecs-task-definition-temp.json \
    --region $AWS_REGION \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo -e "${GREEN}✓${NC} New task definition: $NEW_TASK_DEF"

echo -e "${GREEN}[6/6]${NC} Updating backend service to use new task definition..."
aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service $BACKEND_SERVICE \
    --task-definition $NEW_TASK_DEF \
    --force-new-deployment \
    --region $AWS_REGION \
    --no-cli-pager

echo ""
echo -e "${GREEN}✅ Task definition updated successfully!${NC}"
echo -e "${GREEN}✓${NC} ML_SERVICE_URL is now: http://$ML_PRIVATE_IP:8001"
echo -e "${GREEN}✓${NC} IAM roles updated from running task definition"
echo ""
echo "The backend service is being redeployed with the updated configuration."
echo ""
echo "Monitor deployment status with:"
echo "aws ecs describe-services --cluster $ECS_CLUSTER --services $BACKEND_SERVICE --region $AWS_REGION"
echo ""
echo "Clean up temporary file:"
echo "rm ecs-task-definition-temp.json"
