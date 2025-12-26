#!/bin/bash

# Script to create ECS Task Definition and Service for PlayStudy Backend
# Run this from the deploy directory after pushing your Docker image to ECR

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
ECR_REPOSITORY="${PROJECT_NAME}-backend"
TASK_FAMILY="${PROJECT_NAME}-backend"

# Validate AWS_ACCOUNT_ID
if [ -z "$AWS_ACCOUNT_ID" ]; then
    print_error "AWS_ACCOUNT_ID is not set. Please set it first:"
    echo "export AWS_ACCOUNT_ID=817977750104"
    exit 1
fi

print_info "Starting ECS Service Setup for PlayStudy Backend"
echo "Region: $AWS_REGION"
echo "Account: $AWS_ACCOUNT_ID"
echo ""

# Get Database and Redis endpoints
print_step "Retrieving database endpoints..."
DB_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier ${PROJECT_NAME}-db \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text \
    --region $AWS_REGION)

REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters \
    --cache-cluster-id ${PROJECT_NAME}-redis \
    --show-cache-node-info \
    --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
    --output text \
    --region $AWS_REGION)

print_info "Database: $DB_ENDPOINT"
print_info "Redis: $REDIS_ENDPOINT"
echo ""

# Get DB password
DB_PASSWORD_FILE=~/playstudy-db-password.txt
if [ ! -f "$DB_PASSWORD_FILE" ]; then
    print_error "Database password file not found: $DB_PASSWORD_FILE"
    print_error "Please create this file with your database password"
    exit 1
fi
DB_PASSWORD=$(cat $DB_PASSWORD_FILE)

# Get security groups
print_step "Getting security group IDs..."
ECS_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=${PROJECT_NAME}-ecs-tasks" \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region $AWS_REGION)

ALB_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=${PROJECT_NAME}-alb" \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region $AWS_REGION)

print_info "ECS Security Group: $ECS_SG_ID"
print_info "ALB Security Group: $ALB_SG_ID"
echo ""

# Get VPC and Subnets
print_step "Getting VPC and subnet information..."
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=isDefault,Values=true" \
    --query 'Vpcs[0].VpcId' \
    --output text \
    --region $AWS_REGION)

SUBNETS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'Subnets[*].SubnetId' \
    --output text \
    --region $AWS_REGION)

# Convert to array
SUBNET_ARRAY=($SUBNETS)
print_info "VPC: $VPC_ID"
print_info "Subnets: ${SUBNET_ARRAY[0]}, ${SUBNET_ARRAY[1]} (using first 2)"
echo ""

# Create IAM Execution Role
print_step "Creating IAM execution role..."
EXECUTION_ROLE_NAME="${PROJECT_NAME}-ecs-execution-role"

cat > /tmp/ecs-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
    --role-name $EXECUTION_ROLE_NAME \
    --assume-role-policy-document file:///tmp/ecs-trust-policy.json \
    2>/dev/null || print_warning "Execution role already exists"

aws iam attach-role-policy \
    --role-name $EXECUTION_ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
    2>/dev/null || true

# Create Secrets Manager access policy
cat > /tmp/ecs-secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:${PROJECT_NAME}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
EOF

SECRETS_POLICY_NAME="${PROJECT_NAME}-secrets-access"
aws iam create-policy \
    --policy-name $SECRETS_POLICY_NAME \
    --policy-document file:///tmp/ecs-secrets-policy.json \
    2>/dev/null || print_warning "Secrets policy already exists"

aws iam attach-role-policy \
    --role-name $EXECUTION_ROLE_NAME \
    --policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${SECRETS_POLICY_NAME} \
    2>/dev/null || true

EXECUTION_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${EXECUTION_ROLE_NAME}"
print_info "✅ Execution Role: $EXECUTION_ROLE_ARN"
echo ""

# Create Task Role
print_step "Creating IAM task role..."
TASK_ROLE_NAME="${PROJECT_NAME}-ecs-task-role"

aws iam create-role \
    --role-name $TASK_ROLE_NAME \
    --assume-role-policy-document file:///tmp/ecs-trust-policy.json \
    2>/dev/null || print_warning "Task role already exists"

TASK_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${TASK_ROLE_NAME}"
print_info "✅ Task Role: $TASK_ROLE_ARN"
echo ""

# Wait for IAM roles to propagate
print_info "Waiting for IAM roles to propagate (10 seconds)..."
sleep 10

# Create CloudWatch Log Group
print_step "Creating CloudWatch log group..."
aws logs create-log-group \
    --log-group-name "/ecs/${PROJECT_NAME}-backend" \
    --region $AWS_REGION \
    2>/dev/null || print_warning "Log group already exists"

aws logs put-retention-policy \
    --log-group-name "/ecs/${PROJECT_NAME}-backend" \
    --retention-in-days 7 \
    --region $AWS_REGION \
    2>/dev/null || true

print_info "✅ CloudWatch log group created"
echo ""

# Register Task Definition
print_step "Registering ECS task definition..."

ECR_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:latest"

# Check if secrets exist, if not use environment variables
SECRET_KEY_ARN="arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:${PROJECT_NAME}/secret-key"
FIELD_ENCRYPTION_KEY_ARN="arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:${PROJECT_NAME}/field-encryption-key"
ANTHROPIC_KEY_ARN="arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:${PROJECT_NAME}/anthropic-api-key"

cat > /tmp/task-definition.json <<EOF
{
  "family": "${TASK_FAMILY}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "${EXECUTION_ROLE_ARN}",
  "taskRoleArn": "${TASK_ROLE_ARN}",
  "containerDefinitions": [
    {
      "name": "${PROJECT_NAME}-backend",
      "image": "${ECR_IMAGE}",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "DATABASE_URL", "value": "postgresql://playstudy_admin:${DB_PASSWORD}@${DB_ENDPOINT}:5432/postgres?sslmode=require"},
        {"name": "REDIS_URL", "value": "redis://${REDIS_ENDPOINT}:6379/0"},
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "CORS_ORIGINS", "value": "*"},
        {"name": "SECRET_KEY", "value": "your-secret-key-change-in-production"},
        {"name": "FIELD_ENCRYPTION_KEY", "value": "your-encryption-key-change-in-production"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/${PROJECT_NAME}-backend",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

TASK_DEF_ARN=$(aws ecs register-task-definition \
    --cli-input-json file:///tmp/task-definition.json \
    --region $AWS_REGION \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

print_info "✅ Task Definition: $TASK_DEF_ARN"
echo ""

# Create Application Load Balancer
print_step "Creating/Getting Application Load Balancer..."

ALB_NAME="${PROJECT_NAME}-alb"
ALB_ARN=$(aws elbv2 describe-load-balancers \
    --names $ALB_NAME \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text \
    --region $AWS_REGION 2>/dev/null || echo "")

if [ -z "$ALB_ARN" ] || [ "$ALB_ARN" == "None" ]; then
    print_info "Creating new ALB..."
    ALB_ARN=$(aws elbv2 create-load-balancer \
        --name $ALB_NAME \
        --subnets ${SUBNET_ARRAY[0]} ${SUBNET_ARRAY[1]} \
        --security-groups $ALB_SG_ID \
        --scheme internet-facing \
        --type application \
        --region $AWS_REGION \
        --query 'LoadBalancers[0].LoadBalancerArn' \
        --output text)
    print_info "Waiting for ALB to become active..."
    sleep 30
else
    print_warning "ALB already exists"
fi

ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $ALB_ARN \
    --query 'LoadBalancers[0].DNSName' \
    --output text \
    --region $AWS_REGION)

print_info "✅ ALB DNS: $ALB_DNS"
echo ""

# Create Target Group
print_step "Creating target group..."

TG_NAME="${PROJECT_NAME}-tg"
TG_ARN=$(aws elbv2 describe-target-groups \
    --names $TG_NAME \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text \
    --region $AWS_REGION 2>/dev/null || echo "")

if [ -z "$TG_ARN" ] || [ "$TG_ARN" == "None" ]; then
    TG_ARN=$(aws elbv2 create-target-group \
        --name $TG_NAME \
        --protocol HTTP \
        --port 8000 \
        --vpc-id $VPC_ID \
        --target-type ip \
        --health-check-enabled \
        --health-check-path /health \
        --health-check-interval-seconds 30 \
        --health-check-timeout-seconds 5 \
        --healthy-threshold-count 2 \
        --unhealthy-threshold-count 3 \
        --region $AWS_REGION \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text)
else
    print_warning "Target group already exists"
fi

print_info "✅ Target Group: $TG_ARN"
echo ""

# Create ALB Listener
print_step "Creating ALB listener..."

LISTENER_ARN=$(aws elbv2 describe-listeners \
    --load-balancer-arn $ALB_ARN \
    --query 'Listeners[?Port==`80`].ListenerArn' \
    --output text \
    --region $AWS_REGION 2>/dev/null || echo "")

if [ -z "$LISTENER_ARN" ] || [ "$LISTENER_ARN" == "None" ]; then
    aws elbv2 create-listener \
        --load-balancer-arn $ALB_ARN \
        --protocol HTTP \
        --port 80 \
        --default-actions Type=forward,TargetGroupArn=$TG_ARN \
        --region $AWS_REGION \
        > /dev/null
    print_info "✅ Listener created"
else
    print_warning "Listener already exists"
fi
echo ""

# Create ECS Service
print_step "Creating ECS service..."

SERVICE_EXISTS=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $AWS_REGION \
    --query 'services[0].status' \
    --output text 2>/dev/null || echo "")

if [ "$SERVICE_EXISTS" == "ACTIVE" ]; then
    print_warning "Service already exists, updating..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --task-definition $TASK_FAMILY \
        --force-new-deployment \
        --region $AWS_REGION \
        > /dev/null
else
    aws ecs create-service \
        --cluster $CLUSTER_NAME \
        --service-name $SERVICE_NAME \
        --task-definition $TASK_FAMILY \
        --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_ARRAY[0]},${SUBNET_ARRAY[1]}],securityGroups=[$ECS_SG_ID],assignPublicIp=ENABLED}" \
        --load-balancers "targetGroupArn=$TG_ARN,containerName=${PROJECT_NAME}-backend,containerPort=8000" \
        --region $AWS_REGION \
        > /dev/null
fi

print_info "✅ ECS Service created/updated"
echo ""

# Wait for service to stabilize
print_step "Waiting for service to become stable (this may take 3-5 minutes)..."
aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $AWS_REGION

print_info "✅ Service is stable!"
echo ""

# Display final information
echo "========================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "========================================="
echo ""
echo "Application URL: http://$ALB_DNS"
echo ""
echo "Service Details:"
echo "  Cluster: $CLUSTER_NAME"
echo "  Service: $SERVICE_NAME"
echo "  Task Definition: $TASK_FAMILY"
echo ""
echo "Database:"
echo "  RDS: $DB_ENDPOINT"
echo "  Redis: $REDIS_ENDPOINT"
echo ""
echo "Next Steps:"
echo "  1. Test health: curl http://$ALB_DNS/health"
echo "  2. View logs: aws logs tail /ecs/${PROJECT_NAME}-backend --follow"
echo "  3. Check service: aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME"
echo ""
echo "⚠️  IMPORTANT: Update SECRET_KEY and FIELD_ENCRYPTION_KEY in task definition for production!"
echo "========================================="
