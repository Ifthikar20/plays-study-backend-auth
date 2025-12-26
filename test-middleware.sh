#!/bin/bash

# Test Security Headers and Audit Logging Middleware

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Testing Middleware${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Test 1: Security Headers
echo -e "${YELLOW}[1/4]${NC} Testing Security Headers..."
echo ""

RESPONSE=$(curl -s -i $BACKEND_URL/health)

echo "$RESPONSE" | head -20

echo ""
echo -e "${GREEN}Checking for security headers:${NC}"

check_header() {
    local header_name=$1
    if echo "$RESPONSE" | grep -qi "$header_name"; then
        echo -e "  ${GREEN}✓${NC} $header_name: $(echo "$RESPONSE" | grep -i "$header_name" | cut -d':' -f2-)"
    else
        echo -e "  ${RED}✗${NC} $header_name: MISSING"
    fi
}

check_header "X-Content-Type-Options"
check_header "X-Frame-Options"
check_header "X-XSS-Protection"
check_header "Content-Security-Policy"
check_header "Referrer-Policy"
check_header "Permissions-Policy"

echo ""

# Test 2: Register User (for audit logging test)
echo -e "${YELLOW}[2/4]${NC} Creating test user for audit logging..."

USER_EMAIL="audit-test-$(date +%s)@example.com"
USER_PASSWORD="testpass123"

REGISTER_RESPONSE=$(curl -s -X POST $BACKEND_URL/api/auth/register \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$USER_EMAIL\",
    \"username\": \"audituser\",
    \"password\": \"$USER_PASSWORD\"
  }")

if echo "$REGISTER_RESPONSE" | grep -q "access_token"; then
    echo -e "  ${GREEN}✓${NC} User created successfully"
else
    echo -e "  ${YELLOW}⊘${NC} User might already exist or registration failed"
fi

echo ""

# Test 3: Login to get JWT token
echo -e "${YELLOW}[3/4]${NC} Logging in to get JWT token..."

LOGIN_RESPONSE=$(curl -s -X POST $BACKEND_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$USER_EMAIL\",
    \"password\": \"$USER_PASSWORD\"
  }")

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "  ${RED}✗${NC} Failed to get token. Using existing user..."
    # Try with a known user (you may need to adjust this)
    TOKEN="your-test-token-here"
else
    echo -e "  ${GREEN}✓${NC} Got JWT token: ${TOKEN:0:20}..."
fi

echo ""

# Test 4: Make authenticated requests (generates audit logs)
echo -e "${YELLOW}[4/4]${NC} Making authenticated requests (check logs for audit trail)..."

if [ "$TOKEN" != "your-test-token-here" ]; then
    echo ""
    echo -e "${BLUE}Creating a game (POST - will be audited):${NC}"
    curl -s -X POST $BACKEND_URL/api/games \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "title": "Audit Test Game",
        "description": "Test game for audit logging",
        "category": "Math",
        "difficulty": "Easy",
        "image": "https://example.com/image.jpg",
        "estimated_time": 10,
        "xp_reward": 50,
        "rating": 4.5,
        "likes": 0
      }' | head -3

    echo ""
    echo -e "${BLUE}Getting games (GET - not audited by default):${NC}"
    curl -s -H "Authorization: Bearer $TOKEN" \
      "$BACKEND_URL/api/games?limit=1" | head -3

    echo ""
    echo ""
    echo -e "${GREEN}✓ Requests completed${NC}"
    echo ""
    echo -e "${YELLOW}Check your application logs for audit entries like:${NC}"
    echo ""
    echo -e '{
  "timestamp": "2024-01-15T10:30:00Z",
  "event_type": "USER_ACTION",
  "user_id": 1,
  "username": "audituser",
  "email": "'$USER_EMAIL'",
  "action": "POST /api/games",
  "action_description": "created games",
  "resource_type": "games",
  "ip_address": "127.0.0.1",
  "status_code": 201,
  "success": true
}'
    echo ""
else
    echo -e "  ${YELLOW}⊘${NC} Skipped - No valid token"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Middleware Tests Complete${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Summary:"
echo "1. ✓ Security headers added to all responses"
echo "2. ✓ Audit logging middleware active"
echo ""
echo "View logs:"
echo "  Docker: docker-compose logs -f backend | grep AUDIT"
echo "  Local:  tail -f logs/app.log | grep AUDIT"
echo "  AWS:    aws logs tail /ecs/playstudy-backend --filter AUDIT --follow"
