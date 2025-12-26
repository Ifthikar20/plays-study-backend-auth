# AWS Secrets Manager Setup Guide

## Problem

ECS tasks fail to start with error:
```
ResourceInitializationError: unable to pull secrets or registry auth:
failed to fetch secret arn:aws:secretsmanager:us-east-1:817977750104:secret:playstudy/recaptcha-secret-key
from secrets manager: ResourceNotFoundException: Secrets Manager can't find the specified secret
```

## Root Cause

The ECS task definition references 7 secrets in AWS Secrets Manager that must exist before tasks can start:

| Secret Name | Purpose | Required |
|------------|---------|----------|
| `playstudy/secret-key` | Django SECRET_KEY for session security | Yes |
| `playstudy/field-encryption-key` | Encryption key for sensitive database fields | Yes |
| `playstudy/anthropic-api-key` | Anthropic Claude API access | Optional* |
| `playstudy/deepseek-api-key` | DeepSeek API access | Optional* |
| `playstudy/openai-api-key` | OpenAI GPT API access | Optional* |
| `playstudy/google-cloud-api-key` | Google Cloud services | Optional* |
| `playstudy/recaptcha-secret-key` | Google reCAPTCHA verification | Optional* |

*Optional secrets still need to exist in Secrets Manager but can have placeholder values if not using those services.

## Quick Fix

### Option 1: Use the automated script (Recommended)

```bash
cd deploy
./check-and-create-secrets.sh
```

The script will:
1. Check which secrets exist
2. List missing secrets
3. Offer to create them with:
   - Placeholder values (quick fix)
   - Your actual values (secure)
   - Manual creation instructions

### Option 2: Create all secrets with placeholders manually

```bash
# Generate random placeholder values and create secrets
aws secretsmanager create-secret \
    --name playstudy/secret-key \
    --secret-string "$(openssl rand -base64 32)" \
    --region us-east-1

aws secretsmanager create-secret \
    --name playstudy/field-encryption-key \
    --secret-string "$(openssl rand -base64 32)" \
    --region us-east-1

aws secretsmanager create-secret \
    --name playstudy/anthropic-api-key \
    --secret-string "placeholder-update-if-needed" \
    --region us-east-1

aws secretsmanager create-secret \
    --name playstudy/deepseek-api-key \
    --secret-string "placeholder-update-if-needed" \
    --region us-east-1

aws secretsmanager create-secret \
    --name playstudy/openai-api-key \
    --secret-string "placeholder-update-if-needed" \
    --region us-east-1

aws secretsmanager create-secret \
    --name playstudy/google-cloud-api-key \
    --secret-string "placeholder-update-if-needed" \
    --region us-east-1

aws secretsmanager create-secret \
    --name playstudy/recaptcha-secret-key \
    --secret-string "placeholder-update-if-needed" \
    --region us-east-1
```

## After Creating Secrets

### 1. Force new deployment

```bash
aws ecs update-service \
    --cluster playstudy-cluster \
    --service playstudy-backend-service \
    --force-new-deployment \
    --region us-east-1
```

### 2. Monitor deployment

```bash
# Check service status
aws ecs describe-services \
    --cluster playstudy-cluster \
    --services playstudy-backend-service \
    --region us-east-1 \
    --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,LatestEvent:events[0].message}'

# Watch logs
aws logs tail /ecs/playstudy-backend --follow --region us-east-1
```

### 3. Expected timeline

- **0-30 seconds**: AWS propagates new secrets
- **30-60 seconds**: ECS pulls container image
- **60-90 seconds**: Container starts and runs health checks
- **90+ seconds**: Task marked as healthy, traffic flows

## Updating Secrets with Real Values

### Using AWS CLI

```bash
# Update individual secrets
aws secretsmanager update-secret \
    --secret-id playstudy/anthropic-api-key \
    --secret-string "sk-ant-YOUR-ACTUAL-KEY" \
    --region us-east-1
```

### Using AWS Console

1. Navigate to: https://console.aws.amazon.com/secretsmanager/home?region=us-east-1
2. Find the secret to update
3. Click "Retrieve secret value"
4. Click "Edit"
5. Update the value
6. Click "Save"

### After updating secrets

Force new deployment to pick up changes:
```bash
aws ecs update-service \
    --cluster playstudy-cluster \
    --service playstudy-backend-service \
    --force-new-deployment \
    --region us-east-1
```

## Security Best Practices

### Required Secrets (use strong, random values)

**SECRET_KEY** - Django secret key:
```bash
# Generate secure random key
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Update in AWS
aws secretsmanager update-secret \
    --secret-id playstudy/secret-key \
    --secret-string "YOUR_GENERATED_KEY" \
    --region us-east-1
```

**FIELD_ENCRYPTION_KEY** - For encrypting database fields:
```bash
# Generate 32-byte key
openssl rand -base64 32

# Update in AWS
aws secretsmanager update-secret \
    --secret-id playstudy/field-encryption-key \
    --secret-string "YOUR_GENERATED_KEY" \
    --region us-east-1
```

### Optional API Keys

Only update these if you're using the corresponding services:

- **Anthropic API**: Get from https://console.anthropic.com/
- **DeepSeek API**: Get from https://platform.deepseek.com/
- **OpenAI API**: Get from https://platform.openai.com/
- **Google Cloud API**: Get from https://console.cloud.google.com/
- **reCAPTCHA Secret**: Get from https://www.google.com/recaptcha/admin

## Verifying Secrets Exist

```bash
# List all playstudy secrets
aws secretsmanager list-secrets \
    --filters Key=name,Values=playstudy \
    --region us-east-1 \
    --query 'SecretList[].Name'

# Check a specific secret (without revealing value)
aws secretsmanager describe-secret \
    --secret-id playstudy/secret-key \
    --region us-east-1
```

## IAM Permissions

The ECS task execution role needs permission to read these secrets:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": [
                "arn:aws:secretsmanager:us-east-1:817977750104:secret:playstudy/*"
            ]
        }
    ]
}
```

Verify the execution role has this permission:
```bash
aws iam get-role \
    --role-name playstudy-ecs-execution-role \
    --query 'Role.Arn'
```

## Troubleshooting

### Issue: "Access Denied" when reading secrets

**Solution**: Add `secretsmanager:GetSecretValue` permission to execution role:

```bash
# Create policy
cat > /tmp/secrets-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "secretsmanager:GetSecretValue",
            "Resource": "arn:aws:secretsmanager:us-east-1:817977750104:secret:playstudy/*"
        }
    ]
}
EOF

# Attach to role
aws iam put-role-policy \
    --role-name playstudy-ecs-execution-role \
    --policy-name SecretsManagerAccess \
    --policy-document file:///tmp/secrets-policy.json
```

### Issue: Tasks still failing after creating secrets

1. Wait 30 seconds for secret propagation
2. Check latest error in service events
3. Verify secret names match exactly (case-sensitive)
4. Check execution role has correct permissions

### Issue: Need to delete a secret

```bash
# Delete secret (30-day recovery window)
aws secretsmanager delete-secret \
    --secret-id playstudy/secret-name \
    --region us-east-1

# Force immediate deletion (use with caution)
aws secretsmanager delete-secret \
    --secret-id playstudy/secret-name \
    --force-delete-without-recovery \
    --region us-east-1
```

## Cost

AWS Secrets Manager pricing (us-east-1):
- $0.40 per secret per month
- $0.05 per 10,000 API calls

For 7 secrets: ~$2.80/month

## Alternative: Remove Optional Secrets from Task Definition

If you don't need certain API integrations, you can remove them from the task definition instead:

1. Edit `ecs-task-definition.json`
2. Remove unwanted secrets from the `secrets` array
3. Re-run `./fix-all-placeholders.sh`

**Note**: The application must handle missing environment variables gracefully.
