#!/bin/bash

# AWS Infrastructure Setup Script for PlayStudy Card Dashboard
# This script creates all necessary AWS resources for ECS deployment

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="playstudy"
CLUSTER_NAME="${PROJECT_NAME}-cluster"
SERVICE_NAME="${PROJECT_NAME}-backend-service"
ECR_REPO_NAME="${PROJECT_NAME}-backend"
DB_NAME="${PROJECT_NAME}_db"
DB_USERNAME="playstudy_admin"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

print_info "Setting up AWS infrastructure for PlayStudy..."

# Step 1: Create ECR Repository
print_info "Creating ECR repository..."
aws ecr create-repository \
    --repository-name $ECR_REPO_NAME \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 \
    2>/dev/null || print_warning "ECR repository already exists"

# Step 2: Create ECS Cluster
print_info "Creating ECS cluster..."
aws ecs create-cluster \
    --cluster-name $CLUSTER_NAME \
    --region $AWS_REGION \
    --capacity-providers FARGATE FARGATE_SPOT \
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
    2>/dev/null || print_warning "ECS cluster already exists"

# Step 3: Create CloudWatch Log Group
print_info "Creating CloudWatch log group..."
aws logs create-log-group \
    --log-group-name /ecs/${PROJECT_NAME}-backend \
    --region $AWS_REGION \
    2>/dev/null || print_warning "Log group already exists"

aws logs put-retention-policy \
    --log-group-name /ecs/${PROJECT_NAME}-backend \
    --retention-in-days 7 \
    --region $AWS_REGION

# Step 4: Get Default VPC (or create one)
print_info "Getting VPC information..."
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=isDefault,Values=true" \
    --query 'Vpcs[0].VpcId' \
    --output text \
    --region $AWS_REGION)

if [ "$VPC_ID" == "None" ] || [ -z "$VPC_ID" ]; then
    print_error "No default VPC found. Please create a VPC first."
    exit 1
fi

print_info "Using VPC: $VPC_ID"

# Step 5: Get Subnets
print_info "Getting subnet information..."
SUBNETS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'Subnets[*].SubnetId' \
    --output text \
    --region $AWS_REGION)

print_info "Using subnets: $SUBNETS"

# Step 6: Create Security Group for ECS Tasks
print_info "Creating security group for ECS tasks..."
SG_NAME="${PROJECT_NAME}-ecs-tasks-sg"
ECS_SG_ID=$(aws ec2 create-security-group \
    --group-name $SG_NAME \
    --description "Security group for PlayStudy ECS tasks" \
    --vpc-id $VPC_ID \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text 2>/dev/null) || \
    ECS_SG_ID=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=$SG_NAME" \
        --query 'SecurityGroups[0].GroupId' \
        --output text \
        --region $AWS_REGION)

print_info "ECS Security Group: $ECS_SG_ID"

# Add inbound rules
aws ec2 authorize-security-group-ingress \
    --group-id $ECS_SG_ID \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION \
    2>/dev/null || print_warning "Ingress rule already exists"

# Step 7: Create Security Group for RDS
print_info "Creating security group for RDS..."
RDS_SG_NAME="${PROJECT_NAME}-rds-sg"
RDS_SG_ID=$(aws ec2 create-security-group \
    --group-name $RDS_SG_NAME \
    --description "Security group for PlayStudy RDS database" \
    --vpc-id $VPC_ID \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text 2>/dev/null) || \
    RDS_SG_ID=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=$RDS_SG_NAME" \
        --query 'SecurityGroups[0].GroupId' \
        --output text \
        --region $AWS_REGION)

print_info "RDS Security Group: $RDS_SG_ID"

# Allow ECS tasks to connect to RDS
aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG_ID \
    --protocol tcp \
    --port 5432 \
    --source-group $ECS_SG_ID \
    --region $AWS_REGION \
    2>/dev/null || print_warning "RDS ingress rule already exists"

# Step 8: Create Security Group for Redis
print_info "Creating security group for Redis..."
REDIS_SG_NAME="${PROJECT_NAME}-redis-sg"
REDIS_SG_ID=$(aws ec2 create-security-group \
    --group-name $REDIS_SG_NAME \
    --description "Security group for PlayStudy Redis cache" \
    --vpc-id $VPC_ID \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text 2>/dev/null) || \
    REDIS_SG_ID=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=$REDIS_SG_NAME" \
        --query 'SecurityGroups[0].GroupId' \
        --output text \
        --region $AWS_REGION)

print_info "Redis Security Group: $REDIS_SG_ID"

# Allow ECS tasks to connect to Redis
aws ec2 authorize-security-group-ingress \
    --group-id $REDIS_SG_ID \
    --protocol tcp \
    --port 6379 \
    --source-group $ECS_SG_ID \
    --region $AWS_REGION \
    2>/dev/null || print_warning "Redis ingress rule already exists"

print_info "✅ Infrastructure setup complete!"
echo ""
print_info "Summary:"
echo "  VPC ID: $VPC_ID"
echo "  Subnets: $SUBNETS"
echo "  ECS Cluster: $CLUSTER_NAME"
echo "  ECR Repository: $ECR_REPO_NAME"
echo "  ECS Security Group: $ECS_SG_ID"
echo "  RDS Security Group: $RDS_SG_ID"
echo "  Redis Security Group: $REDIS_SG_ID"
echo ""
print_info "Next steps:"
echo "  1. Create RDS database (see AWS_ECS_DEPLOYMENT_GUIDE.md)"
echo "  2. Create ElastiCache Redis cluster"
echo "  3. Store secrets in AWS Secrets Manager"
echo "  4. Update ECS task definition with actual values"
echo "  5. Deploy using ./deploy.sh"
