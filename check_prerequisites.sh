#!/bin/bash

# DocAI Prerequisites Checker

echo "========================================="
echo "DocAI Prerequisites Verification"
echo "========================================="
echo ""

CHECKS_PASSED=0
CHECKS_FAILED=0

check_item() {
    local name=$1
    local command=$2
    
    if eval "$command" > /dev/null 2>&1; then
        echo "✅ $name"
        ((CHECKS_PASSED++))
    else
        echo "❌ $name"
        ((CHECKS_FAILED++))
    fi
}

# Python checks
echo "📦 Python & Dependencies:"
check_item "Python 3.10+" "python3 --version | grep -E '3\.(1[0-9]|[0-9]{2})'"
check_item "Virtual Environment" "[ -d '.venv' ]"
check_item "FastAPI installed" "python3 -c 'import fastapi'"
check_item "SQLAlchemy installed" "python3 -c 'import sqlalchemy'"
check_item "Pydantic installed" "python3 -c 'import pydantic'"
echo ""

# Services checks
echo "🐳 Services:"
check_item "Docker installed" "docker --version"
check_item "PostgreSQL available" "docker pull postgres:15 > /dev/null 2>&1 || true && docker images | grep -q postgres"
check_item "Redis available" "docker pull redis:7 > /dev/null 2>&1 || true && docker images | grep -q redis"
check_item "Ollama installed" "which ollama"
echo ""

# Project structure checks
echo "📁 Project Structure:"
check_item "src/api/main.py exists" "[ -f 'src/api/main.py' ]"
check_item "src/data/models.py exists" "[ -f 'src/data/models.py' ]"
check_item "src/ai/llm_service.py exists" "[ -f 'src/ai/llm_service.py' ]"
check_item "pyproject.toml exists" "[ -f 'pyproject.toml' ]"
check_item "requirements.txt exists" "[ -f 'requirements.txt' ]"
echo ""

# Database setup
echo "💾 Database Setup:"
if [ -f '.env' ]; then
    echo "✅ .env file exists"
    ((CHECKS_PASSED++))
else
    echo "❌ .env file missing (copy from .env.example)"
    ((CHECKS_FAILED++))
fi

# Summary
echo ""
echo "========================================="
echo "Summary: $CHECKS_PASSED passed, $CHECKS_FAILED failed"
echo "========================================="
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo "✅ All prerequisites satisfied!"
    echo ""
    echo "Next steps:"
    echo "1. Activate virtual environment: source .venv/bin/activate"
    echo "2. Start PostgreSQL: docker run -d --name postgres_docai ..."
    echo "3. Start Redis: docker run -d --name redis_docai ..."
    echo "4. Start Ollama: ollama serve"
    echo "5. Pull model: ollama pull mistral"
    echo "6. Start server: python -m uvicorn src.api.main:app --reload --port 8000"
    echo "7. Run tests: ./e2e_test.sh"
else
    echo "❌ Some prerequisites are missing. Please install them first."
fi
echo ""
