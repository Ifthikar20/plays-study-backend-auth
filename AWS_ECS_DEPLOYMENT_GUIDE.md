# AWS ECS Deployment Guide - PlayStudy Card Dashboard

Complete step-by-step guide to deploy the PlayStudy application to AWS using ECS Fargate, RDS PostgreSQL, and ElastiCache Redis.

**Estimated Time:** 2-3 hours
**Estimated Cost:** $485-715/month for 10,000 users (see COST_ANALYSIS.md)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Local Development Setup](#local-development-setup)
4. [AWS Infrastructure Setup](#aws-infrastructure-setup)
5. [Database Setup (RDS PostgreSQL)](#database-setup-rds-postgresql)
6. [Cache Setup (ElastiCache Redis)](#cache-setup-elasticache-redis)
7. [Secrets Management](#secrets-management)
8. [Container Deployment (ECS Fargate)](#container-deployment-ecs-fargate)
9. [Load Balancer Setup (ALB)](#load-balancer-setup-alb)
10. [Frontend Deployment (S3 + CloudFront)](#frontend-deployment-s3--cloudfront)
11. [DNS Setup (Route53)](#dns-setup-route53)
12. [CI/CD Pipeline](#cicd-pipeline)
13. [Monitoring & Logging](#monitoring--logging)
14. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools
- AWS Account with billing enabled
- AWS CLI v2 ([Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html))
- Docker Desktop ([Install Guide](https://docs.docker.com/get-docker/))
- Node.js 18+ ([Install Guide](https://nodejs.org/))
- Git

### AWS Permissions Required
Your IAM user needs these permissions:
- `AmazonECS_FullAccess`
- `AmazonEC2ContainerRegistryFullAccess`
- `AmazonRDSFullAccess`
- `ElastiCacheFullAccess`
- `AWSCloudFormationFullAccess`
- `IAMFullAccess` (to create roles)
- `SecretsManagerReadWrite`

### Install AWS CLI
```bash
# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version
```

### Configure AWS CLI
```bash
aws configure

# Enter your credentials:
AWS Access Key ID: YOUR_ACCESS_KEY
AWS Secret Access Key: YOUR_SECRET_KEY
Default region name: us-east-1
Default output format: json
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Route53 (DNS)                              │
│                   your-domain.com                            │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
┌────────▼────────┐  ┌──▼──────────────────────────────────┐
│  CloudFront CDN │  │  Application Load Balancer (HTTPS)  │
│  (Frontend)     │  │  api.your-domain.com                │
│  React/Vite     │  └──┬──────────────────────────────────┘
└─────────────────┘     │
                        │
         ┌──────────────┼──────────────┐
         │              │              │
┌────────▼────────┐ ┌──▼────────┐ ┌──▼────────┐
│ ECS Fargate    │ │  Fargate  │ │  Fargate  │
│ Container 1    │ │Container 2│ │Container 3│
│ (Backend API)  │ │ (Backend) │ │ (Backend) │
└────────┬────────┘ └──┬────────┘ └──┬────────┘
         │             │              │
         └─────────────┼──────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
┌────────▼──────────┐     ┌──────────▼────────┐
│  RDS PostgreSQL   │     │  ElastiCache      │
│  db.t4g.small     │     │  Redis            │
│  Multi-AZ         │     │  cache.t4g.small  │
└───────────────────┘     └───────────────────┘
```

---

## Local Development Setup

### 1. Clone Repository
```bash
git clone https://github.com/Ifthikar20/playstudy-card-dash.git
cd playstudy-card-dash
```

### 2. Test with Docker Compose
```bash
# Start all services (PostgreSQL, Redis, Backend, Frontend)
docker-compose up -d

# Check logs
docker-compose logs -f backend

# Access services
# Frontend: http://localhost:5173
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/api/docs

# Stop services
docker-compose down

# Clean up volumes
docker-compose down -v
```

### 3. Verify Local Setup
```bash
# Test backend health
curl http://localhost:8000/health

# Should return: {"status":"healthy","environment":"development"}
```

---

## AWS Infrastructure Setup

### Option 1: Automated Setup (Recommended)
```bash
cd deploy

# Make scripts executable
chmod +x setup-infrastructure.sh deploy.sh

# Set your AWS account ID
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=us-east-1

# Run infrastructure setup
./setup-infrastructure.sh
```

This creates:
- ✅ ECR repository for Docker images
- ✅ ECS cluster (Fargate)
- ✅ Security groups for ECS, RDS, Redis
- ✅ CloudWatch log group

### Option 2: Manual Setup
Follow the manual steps below.

---

## Database Setup (RDS PostgreSQL)

### 1. Create DB Subnet Group
```bash
# Get subnet IDs from your VPC
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=YOUR_VPC_ID" \
  --query 'Subnets[*].SubnetId' \
  --output table

# Create subnet group
aws rds create-db-subnet-group \
  --db-subnet-group-name playstudy-db-subnet \
  --db-subnet-group-description "Subnet group for PlayStudy database" \
  --subnet-ids subnet-xxx subnet-yyy \
  --region us-east-1
```

### 2. Create RDS Instance
```bash
# Generate a secure password
DB_PASSWORD=$(openssl rand -base64 32)
echo "Save this password: $DB_PASSWORD"

# Create PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier playstudy-db \
  --db-instance-class db.t4g.small \
  --engine postgres \
  --engine-version 15.4 \
  --master-username playstudy_admin \
  --master-user-password "$DB_PASSWORD" \
  --allocated-storage 20 \
  --storage-type gp3 \
  --storage-encrypted \
  --vpc-security-group-ids sg-YOUR_RDS_SG_ID \
  --db-subnet-group-name playstudy-db-subnet \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:04:00-sun:05:00" \
  --no-publicly-accessible \
  --enable-cloudwatch-logs-exports '["postgresql"]' \
  --region us-east-1
```

### 3. Wait for Database to Be Available
```bash
# This takes about 10-15 minutes
aws rds wait db-instance-available \
  --db-instance-identifier playstudy-db \
  --region us-east-1

# Get database endpoint
DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier playstudy-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text \
  --region us-east-1)

echo "Database Endpoint: $DB_ENDPOINT"
```

### 4. Create Database Schema
```bash
# Connect to database (from EC2 instance in same VPC or via bastion)
psql -h $DB_ENDPOINT -U playstudy_admin -d postgres

# Create database
CREATE DATABASE playstudy_db;
\q
```

---

## Cache Setup (ElastiCache Redis)

### 1. Create Redis Subnet Group
```bash
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name playstudy-redis-subnet \
  --cache-subnet-group-description "Subnet group for PlayStudy Redis" \
  --subnet-ids subnet-xxx subnet-yyy \
  --region us-east-1
```

### 2. Create Redis Cluster
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id playstudy-redis \
  --cache-node-type cache.t4g.small \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1 \
  --security-group-ids sg-YOUR_REDIS_SG_ID \
  --cache-subnet-group-name playstudy-redis-subnet \
  --preferred-maintenance-window "sun:05:00-sun:06:00" \
  --region us-east-1
```

### 3. Get Redis Endpoint
```bash
# Wait for cluster to be available (5-10 minutes)
aws elasticache wait cache-cluster-available \
  --cache-cluster-id playstudy-redis \
  --region us-east-1

# Get endpoint
REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters \
  --cache-cluster-id playstudy-redis \
  --show-cache-node-info \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
  --output text \
  --region us-east-1)

echo "Redis Endpoint: $REDIS_ENDPOINT"
```

---

## Secrets Management

### 1. Generate Encryption Keys
```bash
# Secret key for JWT
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Field encryption key
FIELD_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

echo "SECRET_KEY: $SECRET_KEY"
echo "FIELD_ENCRYPTION_KEY: $FIELD_ENCRYPTION_KEY"
```

### 2. Store Secrets in AWS Secrets Manager
```bash
# Secret key
aws secretsmanager create-secret \
  --name playstudy/secret-key \
  --secret-string "$SECRET_KEY" \
  --region us-east-1

# Field encryption key
aws secretsmanager create-secret \
  --name playstudy/field-encryption-key \
  --secret-string "$FIELD_ENCRYPTION_KEY" \
  --region us-east-1

# Anthropic API key
aws secretsmanager create-secret \
  --name playstudy/anthropic-api-key \
  --secret-string "YOUR_ANTHROPIC_API_KEY" \
  --region us-east-1

# DeepSeek API key
aws secretsmanager create-secret \
  --name playstudy/deepseek-api-key \
  --secret-string "YOUR_DEEPSEEK_API_KEY" \
  --region us-east-1

# OpenAI API key
aws secretsmanager create-secret \
  --name playstudy/openai-api-key \
  --secret-string "YOUR_OPENAI_API_KEY" \
  --region us-east-1

# Google Cloud API key
aws secretsmanager create-secret \
  --name playstudy/google-cloud-api-key \
  --secret-string "YOUR_GOOGLE_CLOUD_API_KEY" \
  --region us-east-1

# reCAPTCHA secret key
aws secretsmanager create-secret \
  --name playstudy/recaptcha-secret-key \
  --secret-string "YOUR_RECAPTCHA_SECRET_KEY" \
  --region us-east-1
```

### 3. Create IAM Role for ECS Task Execution
```bash
# Create trust policy
cat > ecs-task-execution-trust-policy.json <<EOF
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

# Create role
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://ecs-task-execution-trust-policy.json

# Attach AWS managed policy
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create inline policy for Secrets Manager access
cat > ecs-secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT_ID:secret:playstudy/*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-name SecretsManagerAccess \
  --policy-document file://ecs-secrets-policy.json
```

---

## Container Deployment (ECS Fargate)

### 1. Update Task Definition
```bash
cd deploy

# Edit ecs-task-definition.json and replace:
# - YOUR_ACCOUNT_ID with your AWS account ID
# - DB_HOST with your RDS endpoint
# - DB_PASS with your database password
# - REDIS_HOST with your Redis endpoint
# - Update allowed origins with your domain
```

### 2. Build and Push Docker Image
```bash
# Set variables
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=us-east-1
export ECR_REPOSITORY=playstudy-backend
export IMAGE_TAG=latest

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build image
cd ../backend
docker build -t $ECR_REPOSITORY:$IMAGE_TAG .

# Tag for ECR
docker tag $ECR_REPOSITORY:$IMAGE_TAG \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG
```

### 3. Register Task Definition
```bash
cd ../deploy

# Register task definition
aws ecs register-task-definition \
  --cli-input-json file://ecs-task-definition.json \
  --region us-east-1
```

### 4. Create ECS Service
```bash
# Create service
aws ecs create-service \
  --cluster playstudy-cluster \
  --service-name playstudy-backend-service \
  --task-definition playstudy-backend:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-YOUR_ECS_SG_ID],assignPublicIp=ENABLED}" \
  --region us-east-1

# Wait for service to stabilize
aws ecs wait services-stable \
  --cluster playstudy-cluster \
  --services playstudy-backend-service \
  --region us-east-1
```

---

## Load Balancer Setup (ALB)

### 1. Create Application Load Balancer
```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name playstudy-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-YOUR_ALB_SG_ID \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4 \
  --region us-east-1

# Get ALB ARN
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names playstudy-alb \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text \
  --region us-east-1)
```

### 2. Create Target Group
```bash
aws elbv2 create-target-group \
  --name playstudy-backend-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id YOUR_VPC_ID \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --matcher HttpCode=200 \
  --region us-east-1

# Get Target Group ARN
TG_ARN=$(aws elbv2 describe-target-groups \
  --names playstudy-backend-tg \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text \
  --region us-east-1)
```

### 3. Request SSL Certificate (ACM)
```bash
# Request certificate for your domain
aws acm request-certificate \
  --domain-name api.your-domain.com \
  --subject-alternative-names '*.your-domain.com' \
  --validation-method DNS \
  --region us-east-1

# Follow email or DNS validation process
# Get certificate ARN after validation
```

### 4. Create HTTPS Listener
```bash
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:us-east-1:YOUR_ACCOUNT_ID:certificate/YOUR_CERT_ID \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN \
  --region us-east-1
```

### 5. Update ECS Service with Load Balancer
```bash
aws ecs update-service \
  --cluster playstudy-cluster \
  --service playstudy-backend-service \
  --load-balancers targetGroupArn=$TG_ARN,containerName=playstudy-backend,containerPort=8000 \
  --region us-east-1
```

---

## Frontend Deployment (S3 + CloudFront)

### 1. Create S3 Bucket
```bash
BUCKET_NAME="playstudy-frontend-$(date +%s)"

aws s3 mb s3://$BUCKET_NAME --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled
```

### 2. Build Frontend
```bash
cd ..

# Update API URL in .env.production
cat > .env.production <<EOF
VITE_API_URL=https://api.your-domain.com/api
EOF

# Install dependencies and build
npm install
npm run build
```

### 3. Upload to S3
```bash
aws s3 sync dist/ s3://$BUCKET_NAME/ --delete
```

### 4. Create CloudFront Distribution
```bash
# Create distribution
aws cloudfront create-distribution \
  --origin-domain-name $BUCKET_NAME.s3.amazonaws.com \
  --default-root-object index.html

# Get distribution ID
DIST_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[0].DomainName=='$BUCKET_NAME.s3.amazonaws.com'].Id" \
  --output text)

echo "CloudFront Distribution: $DIST_ID"
```

### 5. Configure Custom Error Pages
```bash
# Create error pages configuration
cat > error-pages.json <<EOF
{
  "CustomErrorResponses": {
    "Items": [
      {
        "ErrorCode": 404,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 300
      },
      {
        "ErrorCode": 403,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 300
      }
    ]
  }
}
EOF

# Update distribution
aws cloudfront update-distribution \
  --id $DIST_ID \
  --custom-error-responses file://error-pages.json
```

---

## DNS Setup (Route53)

### 1. Create Hosted Zone (if needed)
```bash
aws route53 create-hosted-zone \
  --name your-domain.com \
  --caller-reference $(date +%s)
```

### 2. Create DNS Records
```bash
# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names playstudy-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

# Get CloudFront domain
CF_DOMAIN=$(aws cloudfront get-distribution \
  --id $DIST_ID \
  --query 'Distribution.DomainName' \
  --output text)

# Create A record for API
# (Use AWS Console or CLI to create A record alias to ALB)

# Create A record for frontend
# (Use AWS Console or CLI to create A record alias to CloudFront)
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS ECS

on:
  push:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: playstudy-backend
  ECS_CLUSTER: playstudy-cluster
  ECS_SERVICE: playstudy-backend-service
  CONTAINER_NAME: playstudy-backend

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: Build, tag, and push image to Amazon ECR
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          cd backend
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

      - name: Deploy to Amazon ECS
        run: |
          aws ecs update-service \
            --cluster ${{ env.ECS_CLUSTER }} \
            --service ${{ env.ECS_SERVICE }} \
            --force-new-deployment

      - name: Wait for service stability
        run: |
          aws ecs wait services-stable \
            --cluster ${{ env.ECS_CLUSTER }} \
            --services ${{ env.ECS_SERVICE }}

      - name: Deploy frontend to S3
        run: |
          npm ci
          npm run build
          aws s3 sync dist/ s3://your-bucket-name/ --delete

      - name: Invalidate CloudFront cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"
```

### Set GitHub Secrets
```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
CLOUDFRONT_DISTRIBUTION_ID
```

---

## Monitoring & Logging

### CloudWatch Dashboards
```bash
# View logs
aws logs tail /ecs/playstudy-backend --follow

# Create CloudWatch dashboard
# (Use AWS Console)
```

### Set Up Alarms
```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name playstudy-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=ClusterName,Value=playstudy-cluster Name=ServiceName,Value=playstudy-backend-service
```

---

## Troubleshooting

### ECS Task Fails to Start
```bash
# Check task logs
aws ecs describe-tasks \
  --cluster playstudy-cluster \
  --tasks TASK_ARN \
  --region us-east-1

# View CloudWatch logs
aws logs tail /ecs/playstudy-backend --follow
```

### Database Connection Issues
```bash
# Test from ECS task
aws ecs execute-command \
  --cluster playstudy-cluster \
  --task TASK_ARN \
  --container playstudy-backend \
  --interactive \
  --command "/bin/bash"

# Inside container
psql -h DB_ENDPOINT -U playstudy_admin -d playstudy_db
```

### Common Issues

**Issue:** Task fails with "CannotPullContainerError"
**Solution:** Check ECR permissions and image exists

**Issue:** 502 Bad Gateway
**Solution:** Check health check path and security groups

**Issue:** Database timeout
**Solution:** Verify security group allows traffic from ECS tasks

---

## Cost Optimization

1. **Use Spot instances for dev:** Save 70% on compute
2. **Right-size instances:** Monitor and adjust based on usage
3. **Enable S3 lifecycle policies:** Archive old data
4. **Use CloudFront caching:** Reduce origin requests
5. **Set log retention:** 7 days for dev, 30 days for prod

---

## Next Steps

1. ✅ Set up monitoring and alerts
2. ✅ Configure auto-scaling policies
3. ✅ Enable WAF for security
4. ✅ Set up database backups
5. ✅ Implement blue-green deployments
6. ✅ Add custom domain and SSL

---

## Support

- AWS Documentation: https://docs.aws.amazon.com/
- Issues: https://github.com/Ifthikar20/playstudy-card-dash/issues
- Cost Calculator: https://calculator.aws/

---

**Production Ready:** This guide provides a complete, production-ready deployment on AWS ECS with all security best practices.

**Estimated Setup Time:** 2-3 hours
**Monthly Cost:** $485-715 for 10,000 users (see COST_ANALYSIS.md)
