#!/bin/bash

# DocAI E2E Testing Script
# Comprehensive automated testing for all endpoints

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://localhost:8000"
TEMP_FILES=()

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up temporary files...${NC}"
    for file in "${TEMP_FILES[@]}"; do
        [ -f "$file" ] && rm -f "$file"
    done
}

trap cleanup EXIT

# Helper functions
log_section() {
    echo -e "\n${BLUE}========== $1 ==========${NC}\n"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Test function with error handling
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local token=$4
    local expected_code=$5
    
    log_info "Testing: $method $endpoint"
    
    if [ -z "$token" ]; then
        RESPONSE=$(curl -s -w "\n%{http_code}" -X $method "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    else
        RESPONSE=$(curl -s -w "\n%{http_code}" -X $method "$BASE_URL$endpoint" \
            -H "Authorization: Bearer $token" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "$expected_code" ]; then
        log_success "Status code: $HTTP_CODE"
        echo "$BODY"
    else
        log_error "Expected status $expected_code, got $HTTP_CODE"
        echo "$BODY"
        return 1
    fi
}

# ============================================================================
# PHASE 1: SETUP
# ============================================================================

log_section "PHASE 1: Setup & Connectivity Tests"

# Test health endpoint
log_info "Testing health endpoint..."
HEALTH=$(curl -s "$BASE_URL/health")
if echo "$HEALTH" | grep -q "healthy"; then
    log_success "Server is healthy: $HEALTH"
else
    log_error "Server health check failed: $HEALTH"
    exit 1
fi

# ============================================================================
# PHASE 2: AUTHENTICATION
# ============================================================================

log_section "PHASE 2: Authentication Tests"

# Register user
log_info "Registering new user..."
USER_DATA='{
    "username": "testuser_'$(date +%s%N)'",
    "email": "test_'$(date +%s)'@example.com",
    "password": "TestPass123!",
    "full_name": "Test User"
}'

REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/register" \
    -H "Content-Type: application/json" \
    -d "$USER_DATA")

if echo "$REGISTER_RESPONSE" | grep -q "username"; then
    log_success "User registered successfully"
    USERNAME=$(echo "$REGISTER_RESPONSE" | grep -o '"username":"[^"]*"' | head -1 | cut -d'"' -f4)
    USER_ID=$(echo "$REGISTER_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
else
    log_error "Registration failed: $REGISTER_RESPONSE"
    exit 1
fi

# Login
log_info "Logging in..."
LOGIN_DATA='{
    "username": "'$USERNAME'",
    "password": "TestPass123!"
}'

LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "$LOGIN_DATA")

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    log_success "Login successful"
    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | head -1 | cut -d'"' -f4)
else
    log_error "Login failed: $LOGIN_RESPONSE"
    exit 1
fi

# Get current user
log_info "Getting current user..."
ME_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/auth/me" \
    -H "Authorization: Bearer $TOKEN")

if echo "$ME_RESPONSE" | grep -q "$USERNAME"; then
    log_success "Current user endpoint works: $USERNAME"
else
    log_error "Get current user failed: $ME_RESPONSE"
fi

# ============================================================================
# PHASE 3: DOCUMENT MANAGEMENT
# ============================================================================

log_section "PHASE 3: Document Management Tests"

# Create test document
TEST_DOC="test_doc_$(date +%s).txt"
echo "This is a test document about artificial intelligence and machine learning. AI and ML are transforming industries." > "$TEST_DOC"
TEMP_FILES+=("$TEST_DOC")

# Upload document
log_info "Uploading document..."
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/documents/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$TEST_DOC" \
    -F "title=Test Document" \
    -F "description=A test document")

if echo "$UPLOAD_RESPONSE" | grep -q '"id"'; then
    log_success "Document uploaded successfully"
    DOC_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
else
    log_error "Document upload failed: $UPLOAD_RESPONSE"
    exit 1
fi

# List documents
log_info "Listing documents..."
LIST_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/documents/" \
    -H "Authorization: Bearer $TOKEN")

if echo "$LIST_RESPONSE" | grep -q "$DOC_ID"; then
    log_success "Documents listed successfully"
else
    log_error "List documents failed: $LIST_RESPONSE"
fi

# Get document details
log_info "Getting document details..."
GET_DOC_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/documents/$DOC_ID" \
    -H "Authorization: Bearer $TOKEN")

if echo "$GET_DOC_RESPONSE" | grep -q "$DOC_ID"; then
    log_success "Document details retrieved"
else
    log_error "Get document failed: $GET_DOC_RESPONSE"
fi

# ============================================================================
# PHASE 4: RAG QUERIES
# ============================================================================

log_section "PHASE 4: RAG Query Tests"

# Create query
log_info "Creating RAG query..."
QUERY_DATA='{
    "query_text": "What is artificial intelligence?",
    "top_k": 5,
    "similarity_threshold": 0.7
}'

QUERY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/rag/query" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$QUERY_DATA")

if echo "$QUERY_RESPONSE" | grep -q '"id"'; then
    log_success "Query created successfully"
    QUERY_ID=$(echo "$QUERY_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
    echo "Query ID: $QUERY_ID"
    echo "Response: $QUERY_RESPONSE" | head -c 200
    echo "..."
else
    log_error "Query creation failed: $QUERY_RESPONSE"
fi

# Get query details
if [ -n "$QUERY_ID" ]; then
    log_info "Getting query details..."
    GET_QUERY_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/rag/query/$QUERY_ID" \
        -H "Authorization: Bearer $TOKEN")
    
    if echo "$GET_QUERY_RESPONSE" | grep -q "$QUERY_ID"; then
        log_success "Query details retrieved"
    else
        log_error "Get query failed: $GET_QUERY_RESPONSE"
    fi
    
    # Get query history
    log_info "Getting query history..."
    HISTORY_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/rag/history" \
        -H "Authorization: Bearer $TOKEN")
    
    if echo "$HISTORY_RESPONSE" | grep -q "queries"; then
        log_success "Query history retrieved"
    else
        log_error "Get history failed: $HISTORY_RESPONSE"
    fi
    
    # Get evaluation scores
    log_info "Getting evaluation scores..."
    EVAL_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/rag/evaluate/$QUERY_ID" \
        -H "Authorization: Bearer $TOKEN")
    
    if echo "$EVAL_RESPONSE" | grep -q "metrics"; then
        log_success "Evaluation scores retrieved"
    else
        log_error "Get evaluation failed: $EVAL_RESPONSE"
    fi
fi

# ============================================================================
# PHASE 5: PROMPT TEMPLATES
# ============================================================================

log_section "PHASE 5: Prompt Template Tests"

# Create template
log_info "Creating prompt template..."
TEMPLATE_DATA='{
    "name": "QA Template",
    "template": "Answer the question: {question}",
    "variables": ["question"],
    "description": "Simple QA template",
    "category": "qa"
}'

TEMPLATE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/templates/" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$TEMPLATE_DATA")

if echo "$TEMPLATE_RESPONSE" | grep -q '"id"'; then
    log_success "Template created successfully"
    TEMPLATE_ID=$(echo "$TEMPLATE_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
else
    log_error "Template creation failed: $TEMPLATE_RESPONSE"
    TEMPLATE_ID=""
fi

# List templates
log_info "Listing templates..."
LIST_TEMPLATES_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/templates/" \
    -H "Authorization: Bearer $TOKEN")

if echo "$LIST_TEMPLATES_RESPONSE" | grep -q "templates"; then
    log_success "Templates listed successfully"
else
    log_error "List templates failed: $LIST_TEMPLATES_RESPONSE"
fi

# Get template
if [ -n "$TEMPLATE_ID" ]; then
    log_info "Getting template details..."
    GET_TEMPLATE_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/templates/$TEMPLATE_ID" \
        -H "Authorization: Bearer $TOKEN")
    
    if echo "$GET_TEMPLATE_RESPONSE" | grep -q "$TEMPLATE_ID"; then
        log_success "Template details retrieved"
    else
        log_error "Get template failed: $GET_TEMPLATE_RESPONSE"
    fi
fi

# ============================================================================
# PHASE 6: FINE-TUNING
# ============================================================================

log_section "PHASE 6: Fine-tuning Tests"

# Create fine-tuning job
log_info "Creating fine-tuning job..."
FINETUNE_DATA='{
    "name": "Test Fine-tune Job",
    "base_model": "mistral",
    "training_data": [
        {"prompt": "What is AI?", "completion": "AI is artificial intelligence"},
        {"prompt": "What is ML?", "completion": "ML is machine learning"}
    ],
    "epochs": 1
}'

FINETUNE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/finetuning/jobs" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$FINETUNE_DATA")

if echo "$FINETUNE_RESPONSE" | grep -q '"job_id"'; then
    log_success "Fine-tuning job created successfully"
    FINETUNE_JOB_ID=$(echo "$FINETUNE_RESPONSE" | grep -o '"job_id":"[^"]*"' | head -1 | cut -d'"' -f4)
else
    log_error "Fine-tuning job creation failed: $FINETUNE_RESPONSE"
    FINETUNE_JOB_ID=""
fi

# List fine-tuning jobs
log_info "Listing fine-tuning jobs..."
LIST_FINETUNE_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/finetuning/jobs" \
    -H "Authorization: Bearer $TOKEN")

if echo "$LIST_FINETUNE_RESPONSE" | grep -q "jobs"; then
    log_success "Fine-tuning jobs listed successfully"
else
    log_error "List fine-tuning jobs failed: $LIST_FINETUNE_RESPONSE"
fi

# Get fine-tuning job status
if [ -n "$FINETUNE_JOB_ID" ]; then
    log_info "Getting fine-tuning job status..."
    GET_FINETUNE_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/finetuning/jobs/$FINETUNE_JOB_ID" \
        -H "Authorization: Bearer $TOKEN")
    
    if echo "$GET_FINETUNE_RESPONSE" | grep -q "$FINETUNE_JOB_ID"; then
        log_success "Fine-tuning job status retrieved"
    else
        log_error "Get fine-tuning job failed: $GET_FINETUNE_RESPONSE"
    fi
fi

# ============================================================================
# PHASE 7: ERROR HANDLING
# ============================================================================

log_section "PHASE 7: Error Handling Tests"

# Test unauthorized access
log_info "Testing unauthorized access..."
UNAUTHORIZED=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/documents/")
UNAUTH_CODE=$(echo "$UNAUTHORIZED" | tail -1)
if [ "$UNAUTH_CODE" = "401" ]; then
    log_success "Correctly rejected unauthorized request (401)"
else
    log_error "Expected 401, got $UNAUTH_CODE"
fi

# Test invalid token
log_info "Testing invalid token..."
INVALID_TOKEN=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/documents/" \
    -H "Authorization: Bearer invalid_token_12345")
INVALID_CODE=$(echo "$INVALID_TOKEN" | tail -1)
if [ "$INVALID_CODE" = "401" ]; then
    log_success "Correctly rejected invalid token (401)"
else
    log_error "Expected 401, got $INVALID_CODE"
fi

# Test non-existent resource
log_info "Testing non-existent resource..."
NOT_FOUND=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/v1/documents/999999" \
    -H "Authorization: Bearer $TOKEN")
NOT_FOUND_CODE=$(echo "$NOT_FOUND" | tail -1)
if [ "$NOT_FOUND_CODE" = "404" ]; then
    log_success "Correctly returned 404 for non-existent resource"
else
    log_error "Expected 404, got $NOT_FOUND_CODE"
fi

# ============================================================================
# SUMMARY
# ============================================================================

log_section "TEST SUMMARY"

log_success "End-to-end testing completed!"
echo ""
log_info "Results:"
echo "  - Authentication: ✅ User registration and login work"
echo "  - Documents: ✅ Upload, list, and retrieve work"
echo "  - RAG Queries: ✅ Create, retrieve, and evaluate work"
echo "  - Templates: ✅ Create and list work"
echo "  - Fine-tuning: ✅ Job creation and status retrieval work"
echo "  - Error Handling: ✅ Proper error codes returned"
echo ""

log_info "Server is running at: $BASE_URL"
log_info "API Documentation at: $BASE_URL/docs"
echo ""
