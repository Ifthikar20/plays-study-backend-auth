#!/bin/bash

# Comprehensive script to fix ALL placeholders in task definition
# This includes account IDs, IAM roles, and ML service configuration

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="playstudy-cluster"
ML_SERVICE="playstudy-ml-service"
BACKEND_SERVICE="playstudy-backend-service"

echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}  PlayStudy Task Definition Fix${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""

# Step 1: Get AWS Account ID
echo -e "${GREEN}[1/8]${NC} Getting AWS Account ID..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$ACCOUNT_ID" ]; then
    echo -e "${RED}ERROR:${NC} Could not get AWS Account ID"
    exit 1
fi
echo -e "${GREEN}✓${NC} Account ID: $ACCOUNT_ID"

# Step 2: Get current task definition to extract role ARNs
echo -e "${GREEN}[2/8]${NC} Getting current task definition..."
CURRENT_TASK_DEF=$(aws ecs describe-services \
    --cluster $ECS_CLUSTER \
    --services $BACKEND_SERVICE \
    --region $AWS_REGION \
    --query 'services[0].taskDefinition' \
    --output text 2>/dev/null || echo "")

if [ -z "$CURRENT_TASK_DEF" ] || [ "$CURRENT_TASK_DEF" == "None" ]; then
    echo -e "${YELLOW}Warning:${NC} Could not get current task definition."
    echo "Using default role names..."
    EXECUTION_ROLE="arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskExecutionRole"
    TASK_ROLE="arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskRole"
else
    echo -e "${GREEN}✓${NC} Current task definition: $CURRENT_TASK_DEF"

    # Get the actual role ARNs from the current task definition
    EXECUTION_ROLE=$(aws ecs describe-task-definition \
        --task-definition $CURRENT_TASK_DEF \
        --region $AWS_REGION \
        --query 'taskDefinition.executionRoleArn' \
        --output text 2>/dev/null || echo "arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskExecutionRole")

    TASK_ROLE=$(aws ecs describe-task-definition \
        --task-definition $CURRENT_TASK_DEF \
        --region $AWS_REGION \
        --query 'taskDefinition.taskRoleArn' \
        --output text 2>/dev/null || echo "arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskRole")
fi

echo -e "${GREEN}✓${NC} Execution Role: $EXECUTION_ROLE"
echo -e "${GREEN}✓${NC} Task Role: $TASK_ROLE"

# Step 3: Get ML service private IP
echo -e "${GREEN}[3/8]${NC} Getting ML service task..."
TASK_ARN=$(aws ecs list-tasks \
    --cluster $ECS_CLUSTER \
    --service-name $ML_SERVICE \
    --region $AWS_REGION \
    --query 'taskArns[0]' \
    --output text 2>/dev/null || echo "")

if [ -z "$TASK_ARN" ] || [ "$TASK_ARN" == "None" ]; then
    echo -e "${YELLOW}Warning:${NC} ML service task not found. Using placeholder."
    ML_PRIVATE_IP="ML_SERVICE_IP"
    echo "  You'll need to update ML_SERVICE_URL manually after ML service is running."
else
    echo -e "${GREEN}[4/8]${NC} Getting ML service private IP..."
    ML_PRIVATE_IP=$(aws ecs describe-tasks \
        --cluster $ECS_CLUSTER \
        --tasks $TASK_ARN \
        --region $AWS_REGION \
        --query 'tasks[0].attachments[0].details[?name==`privateIPv4Address`].value' \
        --output text 2>/dev/null || echo "ML_SERVICE_IP")

    if [ "$ML_PRIVATE_IP" == "ML_SERVICE_IP" ]; then
        echo -e "${YELLOW}Warning:${NC} Could not get ML service IP. Using placeholder."
    else
        echo -e "${GREEN}✓${NC} ML Service Private IP: $ML_PRIVATE_IP"
    fi
fi

# Step 4: Get environment values from current task definition
echo -e "${GREEN}[5/8]${NC} Getting current environment variables..."
if [ ! -z "$CURRENT_TASK_DEF" ] && [ "$CURRENT_TASK_DEF" != "None" ]; then
    aws ecs describe-task-definition \
        --task-definition $CURRENT_TASK_DEF \
        --region $AWS_REGION \
        --query 'taskDefinition.containerDefinitions[0].environment' \
        --output json > /tmp/current-env.json 2>/dev/null || echo "[]" > /tmp/current-env.json

    # Extract current values (if they exist and aren't placeholders)
    DATABASE_URL=$(jq -r '.[] | select(.name=="DATABASE_URL") | .value' /tmp/current-env.json 2>/dev/null || echo "")
    REDIS_URL=$(jq -r '.[] | select(.name=="REDIS_URL") | .value' /tmp/current-env.json 2>/dev/null || echo "")
    ALLOWED_ORIGINS=$(jq -r '.[] | select(.name=="ALLOWED_ORIGINS") | .value' /tmp/current-env.json 2>/dev/null || echo "")

    echo -e "${GREEN}✓${NC} Extracted environment variables from current task"
else
    DATABASE_URL=""
    REDIS_URL=""
    ALLOWED_ORIGINS=""
fi

# Step 5: Create updated task definition
echo -e "${GREEN}[6/8]${NC} Creating updated task definition..."
cp ecs-task-definition.json ecs-task-definition-temp.json

# Replace Account ID in all locations
sed -i.bak "s/YOUR_ACCOUNT_ID/${ACCOUNT_ID}/g" ecs-task-definition-temp.json

# Replace IAM roles with actual ARNs
sed -i.bak "s|\"executionRoleArn\": \"[^\"]*\"|\"executionRoleArn\": \"$EXECUTION_ROLE\"|g" ecs-task-definition-temp.json
sed -i.bak "s|\"taskRoleArn\": \"[^\"]*\"|\"taskRoleArn\": \"$TASK_ROLE\"|g" ecs-task-definition-temp.json

# Replace ML service IP
sed -i.bak "s/ML_SERVICE_IP/${ML_PRIVATE_IP}/g" ecs-task-definition-temp.json

# If we have actual values from the running task, use them
if [ ! -z "$DATABASE_URL" ] && [[ ! "$DATABASE_URL" =~ DB_ ]]; then
    echo -e "${GREEN}✓${NC} Using existing DATABASE_URL"
    # Escape special characters for sed
    DATABASE_URL_ESCAPED=$(echo "$DATABASE_URL" | sed 's/[&/\]/\\&/g')
    sed -i.bak "s|\"value\": \"postgresql://DB_USER:DB_PASS@DB_HOST:5432/playstudy_db?sslmode=require\"|\"value\": \"$DATABASE_URL_ESCAPED\"|g" ecs-task-definition-temp.json
fi

if [ ! -z "$REDIS_URL" ] && [[ ! "$REDIS_URL" =~ REDIS_HOST ]]; then
    echo -e "${GREEN}✓${NC} Using existing REDIS_URL"
    REDIS_URL_ESCAPED=$(echo "$REDIS_URL" | sed 's/[&/\]/\\&/g')
    sed -i.bak "s|\"value\": \"redis://REDIS_HOST:6379/0\"|\"value\": \"$REDIS_URL_ESCAPED\"|g" ecs-task-definition-temp.json
fi

if [ ! -z "$ALLOWED_ORIGINS" ] && [[ ! "$ALLOWED_ORIGINS" =~ your-domain ]]; then
    echo -e "${GREEN}✓${NC} Using existing ALLOWED_ORIGINS"
    ALLOWED_ORIGINS_ESCAPED=$(echo "$ALLOWED_ORIGINS" | sed 's/[&/\]/\\&/g')
    sed -i.bak "s|\"value\": \"https://your-domain.com,https://www.your-domain.com\"|\"value\": \"$ALLOWED_ORIGINS_ESCAPED\"|g" ecs-task-definition-temp.json
fi

# Remove backup files
rm -f ecs-task-definition-temp.json.bak
rm -f /tmp/current-env.json

echo -e "${GREEN}✓${NC} Task definition updated with:"
echo "    - Account ID: $ACCOUNT_ID"
echo "    - Execution Role: ${EXECUTION_ROLE##*/}"
echo "    - Task Role: ${TASK_ROLE##*/}"
echo "    - ML Service IP: $ML_PRIVATE_IP"

# Step 6: Register new task definition
echo -e "${GREEN}[7/8]${NC} Registering new task definition with AWS ECS..."
NEW_TASK_DEF=$(aws ecs register-task-definition \
    --cli-input-json file://ecs-task-definition-temp.json \
    --region $AWS_REGION \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

if [ -z "$NEW_TASK_DEF" ]; then
    echo -e "${RED}ERROR:${NC} Failed to register task definition"
    exit 1
fi

echo -e "${GREEN}✓${NC} New task definition: $NEW_TASK_DEF"

# Step 7: Update service
echo -e "${GREEN}[8/8]${NC} Updating backend service..."
aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service $BACKEND_SERVICE \
    --task-definition $NEW_TASK_DEF \
    --force-new-deployment \
    --region $AWS_REGION \
    --no-cli-pager

echo ""
echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}  ✅ SUCCESS!${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""
echo "Updated configuration:"
echo "  • Account ID: $ACCOUNT_ID"
echo "  • ECR Image: ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/playstudy-backend:latest"
echo "  • ML Service: http://${ML_PRIVATE_IP}:8001"
echo ""
echo "Next steps:"
echo "  1. Monitor deployment:"
echo "     aws ecs describe-services --cluster $ECS_CLUSTER --services $BACKEND_SERVICE --region $AWS_REGION"
echo ""
echo "  2. Check task logs if needed:"
echo "     aws logs tail /ecs/playstudy-backend --follow"
echo ""
echo "  3. Clean up temporary file when done:"
echo "     rm ecs-task-definition-temp.json"
echo ""
