#!/bin/bash

# Fix database and Redis configuration in ECS task definition
# This resolves the "DB_HOST" placeholder error

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="playstudy-cluster"
BACKEND_SERVICE="playstudy-backend-service"

echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}  Database Configuration Fix${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""

# Step 1: Get RDS endpoint
echo -e "${GREEN}[1/6]${NC} Getting RDS database endpoint..."
DB_ENDPOINT=$(aws rds describe-db-instances \
    --region $AWS_REGION \
    --query 'DBInstances[?contains(DBInstanceIdentifier, `playstudy`)].Endpoint.Address' \
    --output text 2>/dev/null || echo "")

if [ -z "$DB_ENDPOINT" ]; then
    echo -e "${RED}ERROR:${NC} Could not find RDS database instance"
    echo "Looking for any RDS instances..."
    aws rds describe-db-instances \
        --region $AWS_REGION \
        --query 'DBInstances[].DBInstanceIdentifier' \
        --output table
    exit 1
fi

echo -e "${GREEN}✓${NC} Database endpoint: $DB_ENDPOINT"

# Step 2: Get Redis endpoint
echo -e "${GREEN}[2/6]${NC} Getting ElastiCache Redis endpoint..."
REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters \
    --region $AWS_REGION \
    --show-cache-node-info \
    --query 'CacheClusters[?contains(CacheClusterId, `playstudy`)].CacheNodes[0].Endpoint.Address' \
    --output text 2>/dev/null || echo "")

if [ -z "$REDIS_ENDPOINT" ]; then
    echo -e "${YELLOW}Warning:${NC} Could not find Redis cluster"
    echo "Using placeholder for Redis..."
    REDIS_ENDPOINT="REDIS_HOST"
else
    echo -e "${GREEN}✓${NC} Redis endpoint: $REDIS_ENDPOINT"
fi

# Step 3: Get database password
echo -e "${GREEN}[3/6]${NC} Getting database password..."
DB_PASSWORD_FILE=~/playstudy-db-password.txt

if [ ! -f "$DB_PASSWORD_FILE" ]; then
    echo -e "${YELLOW}Warning:${NC} Database password file not found: $DB_PASSWORD_FILE"
    echo ""
    echo "Please enter the database password for user 'playstudy_admin':"
    read -s DB_PASSWORD

    if [ -z "$DB_PASSWORD" ]; then
        echo -e "${RED}ERROR:${NC} Password cannot be empty"
        exit 1
    fi

    # Optionally save for future use
    echo ""
    read -p "Save password to $DB_PASSWORD_FILE for future use? (y/n): " SAVE_PASSWORD
    if [ "$SAVE_PASSWORD" == "y" ]; then
        echo "$DB_PASSWORD" > "$DB_PASSWORD_FILE"
        chmod 600 "$DB_PASSWORD_FILE"
        echo -e "${GREEN}✓${NC} Password saved to $DB_PASSWORD_FILE"
    fi
else
    DB_PASSWORD=$(cat "$DB_PASSWORD_FILE")
    echo -e "${GREEN}✓${NC} Password loaded from $DB_PASSWORD_FILE"
fi

# Step 4: Construct connection strings
echo -e "${GREEN}[4/6]${NC} Constructing connection strings..."

# Database URL (using 'postgres' database instead of playstudy_db)
DATABASE_URL="postgresql://playstudy_admin:${DB_PASSWORD}@${DB_ENDPOINT}:5432/postgres?sslmode=require"
echo -e "${GREEN}✓${NC} DATABASE_URL configured"

# Redis URL
if [ "$REDIS_ENDPOINT" != "REDIS_HOST" ]; then
    REDIS_URL="redis://${REDIS_ENDPOINT}:6379/0"
    echo -e "${GREEN}✓${NC} REDIS_URL configured"
else
    REDIS_URL="redis://REDIS_HOST:6379/0"
    echo -e "${YELLOW}⚠${NC} REDIS_URL using placeholder"
fi

# Step 5: Get current task definition and update it
echo -e "${GREEN}[5/6]${NC} Updating task definition..."

CURRENT_TASK_DEF=$(aws ecs describe-services \
    --cluster $ECS_CLUSTER \
    --services $BACKEND_SERVICE \
    --region $AWS_REGION \
    --query 'services[0].taskDefinition' \
    --output text)

echo "Current task definition: $CURRENT_TASK_DEF"

# Get the task definition JSON
aws ecs describe-task-definition \
    --task-definition $CURRENT_TASK_DEF \
    --region $AWS_REGION \
    --query 'taskDefinition' > /tmp/current-task-def.json

# Remove AWS-managed fields
jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)' \
    /tmp/current-task-def.json > /tmp/task-def-clean.json

# Update DATABASE_URL
jq --arg db_url "$DATABASE_URL" \
    '(.containerDefinitions[0].environment[] | select(.name=="DATABASE_URL") | .value) = $db_url' \
    /tmp/task-def-clean.json > /tmp/task-def-updated.json

# Update REDIS_URL
jq --arg redis_url "$REDIS_URL" \
    '(.containerDefinitions[0].environment[] | select(.name=="REDIS_URL") | .value) = $redis_url' \
    /tmp/task-def-updated.json > /tmp/task-def-final.json

echo -e "${GREEN}✓${NC} Task definition updated"

# Register new task definition
NEW_TASK_DEF=$(aws ecs register-task-definition \
    --cli-input-json file:///tmp/task-def-final.json \
    --region $AWS_REGION \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

if [ -z "$NEW_TASK_DEF" ]; then
    echo -e "${RED}ERROR:${NC} Failed to register new task definition"
    exit 1
fi

echo -e "${GREEN}✓${NC} New task definition: $NEW_TASK_DEF"

# Step 6: Update service
echo -e "${GREEN}[6/6]${NC} Updating ECS service..."
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
echo "  • Database: $DB_ENDPOINT"
echo "  • Redis: $REDIS_ENDPOINT"
echo ""
echo "Next steps:"
echo "  1. Wait ~2 minutes for the new task to start"
echo ""
echo "  2. Monitor deployment:"
echo "     aws ecs describe-services \\"
echo "       --cluster $ECS_CLUSTER \\"
echo "       --services $BACKEND_SERVICE \\"
echo "       --region $AWS_REGION \\"
echo "       --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'"
echo ""
echo "  3. Check logs for successful database connection:"
echo "     aws logs tail /ecs/playstudy-backend --follow --region $AWS_REGION"
echo ""
echo "  4. Clean up temporary files:"
echo "     rm /tmp/current-task-def.json /tmp/task-def-*.json"
echo ""
