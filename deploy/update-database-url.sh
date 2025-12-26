#!/bin/bash

# Script to update DATABASE_URL in ECS task definition with SSL requirement
# This fixes the "no encryption" database connection error

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

# Validate AWS_ACCOUNT_ID
if [ -z "$AWS_ACCOUNT_ID" ]; then
    print_error "AWS_ACCOUNT_ID is not set. Please set it first:"
    echo "export AWS_ACCOUNT_ID=817977750104"
    exit 1
fi

print_info "Updating DATABASE_URL with SSL requirement..."
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

# Extract the current DATABASE_URL
CURRENT_DB_URL=$(cat /tmp/current-task-def.json | \
    jq -r '.containerDefinitions[0].environment[] | select(.name=="DATABASE_URL") | .value')

print_info "Current DATABASE_URL: $CURRENT_DB_URL"

# Check if SSL is already configured
if [[ "$CURRENT_DB_URL" == *"sslmode=require"* ]]; then
    print_warning "DATABASE_URL already has sslmode=require configured!"
    echo ""
    print_info "Current configuration is correct. No update needed."
    exit 0
fi

# Add SSL parameter
if [[ "$CURRENT_DB_URL" == *"?"* ]]; then
    # Already has query parameters, append with &
    NEW_DB_URL="${CURRENT_DB_URL}&sslmode=require"
else
    # No query parameters, add with ?
    NEW_DB_URL="${CURRENT_DB_URL}?sslmode=require"
fi

print_info "New DATABASE_URL: $NEW_DB_URL"
echo ""

# Create new task definition with updated DATABASE_URL
print_step "Creating new task definition revision..."

# Update the DATABASE_URL in the JSON
cat /tmp/current-task-def.json | \
    jq --arg new_url "$NEW_DB_URL" \
    '(.containerDefinitions[0].environment[] | select(.name=="DATABASE_URL") | .value) = $new_url' | \
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
echo "DATABASE_URL Update Summary:"
echo "========================================="
echo ""
echo "Old: $CURRENT_DB_URL"
echo "New: $NEW_DB_URL"
echo ""
echo "The database connection should now work with SSL encryption."
echo ""
echo "Check container logs:"
echo "  aws logs tail /ecs/${PROJECT_NAME}-backend --follow --region $AWS_REGION"
echo ""
echo "========================================="
