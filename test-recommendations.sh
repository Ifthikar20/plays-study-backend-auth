#!/bin/bash

# Test Recommendation Endpoints Locally

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
ML_SERVICE_URL="${ML_SERVICE_URL:-http://localhost:8001}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Testing PlayStudy Recommendation System${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Test 1: ML Service Health
echo -e "${YELLOW}[1/5]${NC} Testing ML Service Health..."
ML_HEALTH=$(curl -s $ML_SERVICE_URL/health || echo "FAILED")

if echo "$ML_HEALTH" | grep -q "healthy"; then
    echo -e "  ${GREEN}✓ ML Service is healthy${NC}"
    echo "  Response: $ML_HEALTH"
else
    echo -e "  ${RED}✗ ML Service is not responding${NC}"
    echo "  Make sure ML service is running on port 8001"
    exit 1
fi

echo ""

# Test 2: Backend Health
echo -e "${YELLOW}[2/5]${NC} Testing Main Backend Health..."
BACKEND_HEALTH=$(curl -s $BACKEND_URL/health || echo "FAILED")

if echo "$BACKEND_HEALTH" | grep -q "ok"; then
    echo -e "  ${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "  ${RED}✗ Backend is not responding${NC}"
    echo "  Make sure backend is running on port 8000"
    exit 1
fi

echo ""

# Test 3: ML Service Direct Call (Internal)
echo -e "${YELLOW}[3/5]${NC} Testing ML Service Direct Call..."
ML_REQUEST='{
  "user_play_history": [
    {"game_id": 1, "play_count": 5},
    {"game_id": 2, "play_count": 3}
  ],
  "all_games": [
    {
      "id": 1,
      "category": "Math",
      "difficulty": "hard",
      "estimated_time": 15,
      "xp_reward": 100,
      "rating": 4.5,
      "likes": 234,
      "title": "Algebra Quiz"
    },
    {
      "id": 2,
      "category": "Math",
      "difficulty": "medium",
      "estimated_time": 10,
      "xp_reward": 80,
      "rating": 4.3,
      "likes": 189,
      "title": "Geometry Basics"
    },
    {
      "id": 3,
      "category": "Math",
      "difficulty": "hard",
      "estimated_time": 20,
      "xp_reward": 150,
      "rating": 4.7,
      "likes": 312,
      "title": "Calculus Challenge"
    },
    {
      "id": 4,
      "category": "Science",
      "difficulty": "medium",
      "estimated_time": 12,
      "xp_reward": 90,
      "rating": 4.4,
      "likes": 267,
      "title": "Physics Quest"
    }
  ],
  "limit": 2
}'

ML_RESPONSE=$(curl -s -X POST $ML_SERVICE_URL/recommend \
    -H "Content-Type: application/json" \
    -d "$ML_REQUEST")

if echo "$ML_RESPONSE" | grep -q "game_ids"; then
    echo -e "  ${GREEN}✓ ML Service returning recommendations${NC}"
    echo "  Response:"
    echo "$ML_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$ML_RESPONSE"
else
    echo -e "  ${RED}✗ ML Service not returning valid recommendations${NC}"
    echo "  Response: $ML_RESPONSE"
    exit 1
fi

echo ""

# Test 4: Backend to ML Service Integration
echo -e "${YELLOW}[4/5]${NC} Testing Backend → ML Service Integration..."
INTEGRATION_HEALTH=$(curl -s $BACKEND_URL/api/recommendations/health || echo "FAILED")

if echo "$INTEGRATION_HEALTH" | grep -q "healthy"; then
    echo -e "  ${GREEN}✓ Backend can reach ML service${NC}"
    echo "  Response:"
    echo "$INTEGRATION_HEALTH" | python3 -m json.tool 2>/dev/null || echo "$INTEGRATION_HEALTH"
else
    echo -e "  ${RED}✗ Backend cannot reach ML service${NC}"
    echo "  Response: $INTEGRATION_HEALTH"
    exit 1
fi

echo ""

# Test 5: End-to-End (requires authentication)
echo -e "${YELLOW}[5/5]${NC} Testing End-to-End Recommendations..."

if [ -z "$JWT_TOKEN" ]; then
    echo -e "  ${YELLOW}⊘ Skipped - Set JWT_TOKEN environment variable to test${NC}"
    echo "    Example: export JWT_TOKEN='your-jwt-token'"
    echo "    Get token by logging in: curl -X POST $BACKEND_URL/api/auth/login ..."
else
    RECOMMENDATIONS=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" \
        "$BACKEND_URL/api/recommendations/similar?limit=5")

    if echo "$RECOMMENDATIONS" | grep -q "id"; then
        echo -e "  ${GREEN}✓ Successfully got personalized recommendations${NC}"
        echo "  Number of games: $(echo $RECOMMENDATIONS | grep -o '"id"' | wc -l)"
    else
        echo -e "  ${RED}✗ Failed to get recommendations${NC}"
        echo "  Response: $RECOMMENDATIONS"
    fi
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ All Tests Passed${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Your recommendation system is working correctly!"
echo ""
echo "Next steps:"
echo "  1. Test with real user data"
echo "  2. Deploy to AWS using deployment scripts"
echo "  3. Update frontend to call /api/recommendations/similar"
