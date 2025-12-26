#!/bin/bash

# Deploy ML Recommendation Service to AWS ECS
# This service is INTERNAL ONLY - not exposed to public internet

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID}"
ECR_REPOSITORY="playstudy-ml-service"
ECS_CLUSTER="playstudy-cluster"
ECS_SERVICE="playstudy-ml-service"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Validate
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${YELLOW}ERROR:${NC} AWS_ACCOUNT_ID is not set"
    echo "export AWS_ACCOUNT_ID=123456789012"
    exit 1
fi

echo -e "${GREEN}[INFO]${NC} Deploying ML Service (Internal Only)"
echo -e "${GREEN}[INFO]${NC} Region: $AWS_REGION"
echo -e "${GREEN}[INFO]${NC} Account: $AWS_ACCOUNT_ID"

# Step 1: Create ECR repository if doesn't exist
echo -e "${GREEN}[INFO]${NC} Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION

# Step 2: Login to ECR
echo -e "${GREEN}[INFO]${NC} Logging in to Amazon ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Step 3: Build Docker image
echo -e "${GREEN}[INFO]${NC} Building ML service Docker image..."
docker build --platform linux/amd64 -t $ECR_REPOSITORY:$IMAGE_TAG .

# Step 4: Tag image
echo -e "${GREEN}[INFO]${NC} Tagging image for ECR..."
docker tag $ECR_REPOSITORY:$IMAGE_TAG \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG

# Step 5: Push to ECR
echo -e "${GREEN}[INFO]${NC} Pushing image to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG

echo -e "${GREEN}✅ ML service image pushed to ECR${NC}"
echo ""
echo "Next steps:"
echo "1. Create ECS task definition and service (if not exists)"
echo "2. Update main app with ML_SERVICE_URL environment variable"
echo "3. Deploy main app"
