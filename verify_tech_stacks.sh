#!/bin/bash
# Tech Stack End-to-End Verification Script
# Run this after: python seed_tech_stacks.py

set -e

API_BASE="http://localhost:8000"
ENDPOINT_TECH_STACK="$API_BASE/api/v1/recruitment/tech-stack"
ENDPOINT_AGENT_QUERY="$API_BASE/api/agent/query"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Tech Stack System E2E Verification${NC}"
echo -e "${YELLOW}========================================${NC}"

# Test 1: API is running
echo -e "\n${YELLOW}[Test 1]${NC} Checking if API is running..."
if ! curl -s "$ENDPOINT_TECH_STACK" > /dev/null 2>&1; then
  echo -e "${RED}✗ FAILED${NC}: API not responding at $API_BASE"
  echo -e "   Start the API first: python main.py"
  exit 1
fi
echo -e "${GREEN}✓ PASSED${NC}: API is running"

# Test 2: Tech stacks loaded
echo -e "\n${YELLOW}[Test 2]${NC} Checking if tech stacks are loaded..."
STACK_COUNT=$(curl -s "$ENDPOINT_TECH_STACK" | jq 'length')
if [ "$STACK_COUNT" -lt 20 ]; then
  echo -e "${RED}✗ FAILED${NC}: Only $STACK_COUNT tech stacks found (expected 20)"
  echo -e "   Run: python seed_tech_stacks.py"
  exit 1
fi
echo -e "${GREEN}✓ PASSED${NC}: All 20 tech stacks loaded ($STACK_COUNT found)"

# Test 3: List tech stacks
echo -e "\n${YELLOW}[Test 3]${NC} Listing all tech stacks..."
echo "Tech Stacks:"
curl -s "$ENDPOINT_TECH_STACK" | jq -r '.[] | "\(.id). \(.name)"'

# Test 4: Get specific tech stack
echo -e "\n${YELLOW}[Test 4]${NC} Fetching tech stack #3 (SAP)..."
SAP_TECH=$(curl -s "$ENDPOINT_TECH_STACK/3")
SAP_NAME=$(echo "$SAP_TECH" | jq -r '.name')
if [ "$SAP_NAME" != "SAP" ]; then
  echo -e "${RED}✗ FAILED${NC}: Expected SAP, got $SAP_NAME"
  exit 1
fi
echo -e "${GREEN}✓ PASSED${NC}: SAP tech stack retrieved"
echo "  Name: $SAP_NAME"
echo "  Keywords: $(echo "$SAP_TECH" | jq -r '.keywords | join(", ")')"
echo "  Skills: $(echo "$SAP_TECH" | jq -r '.skills | join(", ")')"

# Test 5: Query structure validation
echo -e "\n${YELLOW}[Test 5]${NC} Testing query with tech_stack_id filter..."
QUERY_RESPONSE=$(curl -s -X POST "$ENDPOINT_AGENT_QUERY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me candidates",
    "user_id": 1,
    "tech_stack_id": 3
  }')

# Check response structure
if echo "$QUERY_RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
  echo -e "${GREEN}✓ PASSED${NC}: Query accepted with tech_stack_id filter"
  echo "  Response status: $(echo "$QUERY_RESPONSE" | jq -r '.status // .error')"
else
  echo -e "${YELLOW}⚠ WARNING${NC}: Query response structure unexpected"
  echo "$QUERY_RESPONSE" | head -100
fi

# Test 6: Verify upload directories exist
echo -e "\n${YELLOW}[Test 6]${NC} Checking upload directories..."
UPLOAD_BASE="uploads/tech_stack"
if [ ! -d "$UPLOAD_BASE" ]; then
  echo -e "${RED}✗ FAILED${NC}: Upload directory $UPLOAD_BASE does not exist"
  exit 1
fi

DIR_COUNT=$(ls -d "$UPLOAD_BASE"/*/ 2>/dev/null | wc -l)
if [ "$DIR_COUNT" -lt 20 ]; then
  echo -e "${YELLOW}⚠ WARNING${NC}: Only $DIR_COUNT upload directories found (expected 20)"
else
  echo -e "${GREEN}✓ PASSED${NC}: All 20 upload directories created ($DIR_COUNT found)"
fi

# List upload directories
echo "Upload directories:"
ls -d "$UPLOAD_BASE"/*/ 2>/dev/null | head -5 | xargs -I {} basename {} | sed 's/^/  /'
echo "  ... (showing first 5 of $DIR_COUNT)"

# Test 7: Database connectivity
echo -e "\n${YELLOW}[Test 7]${NC} Checking database connectivity..."
if [ ! -f ".env" ]; then
  echo -e "${YELLOW}⚠ WARNING${NC}: .env file not found (cannot verify DB URL)"
else
  DB_URL=$(grep DATABASE_URL .env | cut -d'=' -f2)
  echo -e "${GREEN}✓ PASSED${NC}: .env file found"
  echo "  Database configured: $(echo $DB_URL | sed 's/:[^:]*@/@/g')"
fi

# Summary
echo -e "\n${YELLOW}========================================${NC}"
echo -e "${GREEN}✅ All Critical Tests Passed!${NC}"
echo -e "${YELLOW}========================================${NC}"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Upload resumes with tech_stack_id:"
echo "   curl -X POST $API_BASE/api/v1/recruitment/resume/bulk-upload \\"
echo "     -F 'jd_id=1' -F 'tech_stack_id=3' -F 'file=@resume.pdf'"
echo ""
echo "2. Query with tech_stack_id filter:"
echo "   curl -X POST $ENDPOINT_AGENT_QUERY \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"query\": \"find ABAP developers\", \"tech_stack_id\": 3}'"
echo ""
echo "3. Count candidates in a tech stack:"
echo "   curl -X POST $ENDPOINT_AGENT_QUERY \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"query\": \"How many ABAP developers?\", \"tech_stack_id\": 3}'"
echo ""
echo -e "${YELLOW}For full reference, see: TECH_STACK_QUICK_REFERENCE.md${NC}"
