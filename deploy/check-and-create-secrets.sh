#!/bin/bash

# Check which secrets exist and create missing ones in AWS Secrets Manager
# This script helps resolve ResourceInitializationError from missing secrets

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

AWS_REGION="${AWS_REGION:-us-east-1}"

# List of required secrets
SECRETS=(
    "playstudy/secret-key"
    "playstudy/field-encryption-key"
    "playstudy/anthropic-api-key"
    "playstudy/deepseek-api-key"
    "playstudy/openai-api-key"
    "playstudy/google-cloud-api-key"
    "playstudy/recaptcha-secret-key"
)

echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}  Secrets Manager Check${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""

MISSING_SECRETS=()
EXISTING_SECRETS=()

echo "Checking secrets in AWS Secrets Manager..."
echo ""

for secret in "${SECRETS[@]}"; do
    # Try to get the secret
    if aws secretsmanager describe-secret \
        --secret-id "$secret" \
        --region $AWS_REGION \
        >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $secret"
        EXISTING_SECRETS+=("$secret")
    else
        echo -e "${RED}✗${NC} $secret (MISSING)"
        MISSING_SECRETS+=("$secret")
    fi
done

echo ""
echo -e "${GREEN}=================================${NC}"

if [ ${#MISSING_SECRETS[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ All secrets exist!${NC}"
    echo ""
    echo "Your ECS tasks should be able to start now."
    exit 0
fi

echo -e "${YELLOW}⚠ Found ${#MISSING_SECRETS[@]} missing secret(s)${NC}"
echo ""

echo "Missing secrets:"
for secret in "${MISSING_SECRETS[@]}"; do
    echo "  - $secret"
done
echo ""

echo -e "${BLUE}Options to fix:${NC}"
echo ""
echo "1. Create secrets with placeholder values (quick fix to get service running)"
echo "2. Create secrets with your actual values (recommended)"
echo "3. Exit and create secrets manually"
echo ""

read -p "Choose option (1/2/3): " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}Creating secrets with placeholder values...${NC}"
        echo ""

        for secret in "${MISSING_SECRETS[@]}"; do
            # Generate a random placeholder value
            PLACEHOLDER_VALUE=$(openssl rand -base64 32)

            # Create the secret
            aws secretsmanager create-secret \
                --name "$secret" \
                --description "Placeholder - UPDATE WITH REAL VALUE" \
                --secret-string "$PLACEHOLDER_VALUE" \
                --region $AWS_REGION \
                >/dev/null

            echo -e "${GREEN}✓${NC} Created: $secret (with placeholder value)"
        done

        echo ""
        echo -e "${GREEN}✅ All secrets created!${NC}"
        echo ""
        echo -e "${YELLOW}IMPORTANT:${NC} Update these secrets with real values:"
        echo ""
        echo "Example commands to update secrets:"
        for secret in "${MISSING_SECRETS[@]}"; do
            echo "  aws secretsmanager update-secret --secret-id $secret --secret-string 'YOUR_ACTUAL_VALUE' --region $AWS_REGION"
        done
        echo ""
        echo "Or use the AWS Console:"
        echo "  https://console.aws.amazon.com/secretsmanager/home?region=$AWS_REGION"
        echo ""
        ;;

    2)
        echo ""
        echo -e "${BLUE}Creating secrets with your values...${NC}"
        echo ""

        for secret in "${MISSING_SECRETS[@]}"; do
            echo -e "${YELLOW}Enter value for ${secret}:${NC}"
            read -s secret_value

            if [ -z "$secret_value" ]; then
                echo -e "${RED}Error: Value cannot be empty${NC}"
                exit 1
            fi

            # Create the secret
            aws secretsmanager create-secret \
                --name "$secret" \
                --description "Created via check-and-create-secrets.sh" \
                --secret-string "$secret_value" \
                --region $AWS_REGION \
                >/dev/null

            echo -e "${GREEN}✓${NC} Created: $secret"
            echo ""
        done

        echo -e "${GREEN}✅ All secrets created with your values!${NC}"
        echo ""
        ;;

    3)
        echo ""
        echo "To create secrets manually:"
        echo ""
        for secret in "${MISSING_SECRETS[@]}"; do
            echo "  aws secretsmanager create-secret \\"
            echo "    --name $secret \\"
            echo "    --secret-string 'YOUR_VALUE' \\"
            echo "    --region $AWS_REGION"
            echo ""
        done
        echo "Or use the AWS Console:"
        echo "  https://console.aws.amazon.com/secretsmanager/home?region=$AWS_REGION"
        exit 0
        ;;

    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}  Next Steps${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""
echo "1. Wait ~30 seconds for AWS to propagate the secrets"
echo ""
echo "2. Force new deployment of the ECS service:"
echo "   aws ecs update-service \\"
echo "     --cluster playstudy-cluster \\"
echo "     --service playstudy-backend-service \\"
echo "     --force-new-deployment \\"
echo "     --region $AWS_REGION"
echo ""
echo "3. Monitor the deployment:"
echo "   aws ecs describe-services \\"
echo "     --cluster playstudy-cluster \\"
echo "     --services playstudy-backend-service \\"
echo "     --region $AWS_REGION \\"
echo "     --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'"
echo ""
