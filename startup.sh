#!/bin/bash

# DocAI Startup Script
# Usage: ./startup.sh [option]
# Options: api, worker, all, docker

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}    DocAI - Startup Script${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
if ! command_exists python3; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

# Load environment variables
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}Please edit .env with your configuration${NC}"
fi

# Parse arguments
OPTION="${1:-all}"

case $OPTION in
    api)
        echo -e "${GREEN}Starting FastAPI server...${NC}"
        python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8001
        ;;
    worker)
        echo -e "${GREEN}Starting Celery worker...${NC}"
        if ! command_exists celery; then
            echo -e "${RED}Celery is not installed${NC}"
            exit 1
        fi
        celery -A src.workers.tasks worker --loglevel=info --concurrency=4
        ;;
    docker)
        echo -e "${GREEN}Starting with Docker Compose...${NC}"
        if ! command_exists docker-compose; then
            echo -e "${RED}Docker Compose is not installed${NC}"
            exit 1
        fi
        docker-compose up -d
        echo -e "${GREEN}Services started!${NC}"
        echo -e "${GREEN}API: http://localhost:8001${NC}"
        echo -e "${GREEN}Docs: http://localhost:8001/docs${NC}"
        docker-compose logs -f api
        ;;
    all)
        echo -e "${YELLOW}Starting all services locally...${NC}"
        echo -e "${GREEN}Prerequisites: PostgreSQL and Redis must be running${NC}"
        echo ""
        echo -e "${YELLOW}Terminal 1: API Server${NC}"
        echo "  python -m uvicorn src.api.main:app --reload"
        echo ""
        echo -e "${YELLOW}Terminal 2: Celery Worker${NC}"
        echo "  celery -A src.workers.tasks worker --loglevel=info"
        echo ""
        echo -e "${YELLOW}Terminal 3: This Terminal${NC}"
        echo "  cd /Users/milinddeshmukh/docAi && source .venv/bin/activate"
        echo ""
        echo -e "${GREEN}Then visit: http://localhost:8001/docs${NC}"
        ;;
    *)
        echo -e "${RED}Unknown option: $OPTION${NC}"
        echo "Usage: $0 [api|worker|all|docker]"
        exit 1
        ;;
esac
