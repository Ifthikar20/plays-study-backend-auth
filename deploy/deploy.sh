#!/bin/bash

# AWS ECS Deployment Script for PlayStudy Card Dashboard
# This script automates the deployment of the backend to AWS ECS

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID}"
ECR_REPOSITORY="playstudy-backend"
ECS_CLUSTER="playstudy-cluster"
ECS_SERVICE="playstudy-backend-service"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate required environment variables
if [ -z "$AWS_ACCOUNT_ID" ]; then
    print_error "AWS_ACCOUNT_ID is not set. Please set it first:"
    echo "export AWS_ACCOUNT_ID=123456789012"
    exit 1
fi

print_info "Starting deployment to AWS ECS..."
print_info "Region: $AWS_REGION"
print_info "Account: $AWS_ACCOUNT_ID"
print_info "Image Tag: $IMAGE_TAG"

# Step 1: Login to ECR
print_info "Logging in to Amazon ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Step 2: Build Docker image
print_info "Building Docker image..."
cd ../backend
docker build -t $ECR_REPOSITORY:$IMAGE_TAG .

# Step 3: Tag image for ECR
print_info "Tagging image for ECR..."
docker tag $ECR_REPOSITORY:$IMAGE_TAG \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG

# Step 4: Push to ECR
print_info "Pushing image to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG

# Step 5: Update ECS service
print_info "Updating ECS service..."
aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service $ECS_SERVICE \
    --force-new-deployment \
    --region $AWS_REGION

# Step 6: Wait for deployment to complete
print_info "Waiting for deployment to stabilize..."
aws ecs wait services-stable \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE \
    --region $AWS_REGION

print_info "✅ Deployment completed successfully!"
print_info "Check service status:"
echo "aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION"
