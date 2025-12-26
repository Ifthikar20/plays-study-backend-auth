#!/bin/bash

# Script to update ALLOWED_ORIGINS in ECS task definition
# This adds the ALB endpoint to the allowed origins

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID}"
PROJECT_NAME="playstudy"
CLUSTER_NAME="${PROJECT_NAME}-cluster"
SERVICE_NAME="${PROJECT_NAME}-backend-service"
TASK_FAMILY="${PROJECT_NAME}-backend"
ALB_DNS="playstudy-alb-1732754070.us-east-1.elb.amazonaws.com"

# Validate AWS_ACCOUNT_ID
if [ -z "$AWS_ACCOUNT_ID" ]; then
    print_error "AWS_ACCOUNT_ID is not set. Please set it first:"
    echo "export AWS_ACCOUNT_ID=817977750104"
    exit 1
fi

print_info "Updating ALLOWED_ORIGINS with ALB endpoint..."
echo ""

# Get current task definition
print_step "Retrieving current task definition..."
TASK_DEF_ARN=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $AWS_REGION \
    --query 'services[0].taskDefinition' \
    --output text)

if [ -z "$TASK_DEF_ARN" ] || [ "$TASK_DEF_ARN" == "None" ]; then
    print_error "Could not find task definition for service $SERVICE_NAME"
    exit 1
fi

print_info "Current task definition: $TASK_DEF_ARN"

# Get the full task definition
print_step "Downloading task definition..."
aws ecs describe-task-definition \
    --task-definition $TASK_DEF_ARN \
    --region $AWS_REGION \
    --query 'taskDefinition' \
    > /tmp/current-task-def.json

# Check if ALLOWED_ORIGINS or CORS_ORIGINS exists
CURRENT_ORIGINS=$(cat /tmp/current-task-def.json | \
    jq -r '.containerDefinitions[0].environment[] | select(.name=="ALLOWED_ORIGINS" or .name=="CORS_ORIGINS") | .value')

ORIGIN_VAR_NAME=$(cat /tmp/current-task-def.json | \
    jq -r '.containerDefinitions[0].environment[] | select(.name=="ALLOWED_ORIGINS" or .name=="CORS_ORIGINS") | .name')

print_info "Current origins variable: $ORIGIN_VAR_NAME"
print_info "Current value: $CURRENT_ORIGINS"

# Set new origins value (include localhost for development)
NEW_ORIGINS="http://localhost:8080,http://${ALB_DNS},https://${ALB_DNS}"

print_info "New ALLOWED_ORIGINS: $NEW_ORIGINS"
echo ""

# Create new task definition with updated ALLOWED_ORIGINS
print_step "Creating new task definition revision..."

# Update or add ALLOWED_ORIGINS and remove CORS_ORIGINS if it exists
cat /tmp/current-task-def.json | \
    jq --arg new_origins "$NEW_ORIGINS" \
    '(.containerDefinitions[0].environment |= map(select(.name != "CORS_ORIGINS" and .name != "ALLOWED_ORIGINS"))) |
     (.containerDefinitions[0].environment += [{"name": "ALLOWED_ORIGINS", "value": $new_origins}])' | \
    jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)' \
    > /tmp/new-task-def.json

# Register new task definition
NEW_TASK_DEF_ARN=$(aws ecs register-task-definition \
    --cli-input-json file:///tmp/new-task-def.json \
    --region $AWS_REGION \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

print_info "✅ New task definition: $NEW_TASK_DEF_ARN"
echo ""

# Update service to use new task definition
print_step "Updating ECS service..."
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --task-definition $TASK_FAMILY \
    --force-new-deployment \
    --region $AWS_REGION \
    > /dev/null

print_info "✅ Service updated successfully!"
echo ""

# Wait for deployment to complete
print_step "Waiting for service to stabilize (this may take 3-5 minutes)..."
aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $AWS_REGION

print_info "✅ Deployment complete!"
echo ""
echo "========================================="
echo "ALLOWED_ORIGINS Update Summary:"
echo "========================================="
echo ""
echo "Old: $CURRENT_ORIGINS"
echo "New: $NEW_ORIGINS"
echo ""
echo "Your API is now accessible at:"
echo "  http://${ALB_DNS}"
echo "  https://${ALB_DNS}"
echo ""
echo "Test endpoints:"
echo "  Health: curl http://${ALB_DNS}/health"
echo "  Root:   curl http://${ALB_DNS}/"
echo ""
echo "========================================="
