#!/bin/bash
# ==============================================================================
# AI RESUME PARSER - SETUP SCRIPT
# ==============================================================================
# This script prepares the environment and starts the application using Docker.

# --- Colors for Output ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting AI Resume Parser setup...${NC}\n"

# --- 1. Check for Docker ---
# Check for both 'docker' and 'docker compose' (v2) or 'docker-compose' (v1)
if ! [ -x "$(command -v docker)" ]; then
  echo -e "${RED}ERROR: Docker is not installed.${NC}"
  echo "Please install Docker Desktop before running this script."
  exit 1
fi
if ! (docker compose version &> /dev/null || docker-compose version &> /dev/null); then
    echo -e "${RED}ERROR: Docker Compose is not installed or not available in the system's PATH.${NC}"
    echo "Please ensure Docker Desktop is running and 'docker compose' (v2) or 'docker-compose' (v1) is installed."
    exit 1
fi

echo "✔ Docker & Docker Compose are installed."

# --- 2. Check for .env file ---
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}WARNING: '.env' file not found.${NC}"
    echo "Copying '.env.example' to '.env'..."
    cp .env.example .env
    echo -e "\n${GREEN}SUCCESS: '.env' file created.${NC}"
    echo -e "\n${RED}-------------------------------------------------------------------${NC}"
    echo -e "${YELLOW}ACTION REQUIRED:${NC} Please open the new '.env' file and add your"
    echo -e "${YELLOW}GOOGLE_API_KEY before running this script again."
    echo -e "${RED}-------------------------------------------------------------------${NC}\n"
    exit 1
else
    echo "✔ '.env' file found."
fi

# --- 3. Check for API Key in .env ---
# THE FIX IS HERE:
# This command checks if the GOOGLE_API_KEY line *exists* and has *at least one character* after the =
if ! grep -q "GOOGLE_API_KEY=.*[a-zA-Z0-9]" .env; then
    echo -e "\n${RED}-------------------------------------------------------------------${NC}"
    echo -e "${YELLOW}ERROR: GOOGLE_API_KEY is missing or empty in your .env file.${NC}"
    echo "Please add your Google AI Studio API key to the .env file."
    echo -e "${RED}-------------------------------------------------------------------${NC}\n"
    exit 1
else
     echo "✔ GOOGLE_API_KEY is present."
fi

# --- 4. Build and Start Docker Containers ---
echo -e "\n${GREEN}Building and starting all application services...${NC}"
echo "This may take a few minutes on the first run."

# The 'docker-compose' command is now 'docker compose' in v2
# We'll check which one to use for compatibility.
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

$COMPOSE_CMD up --build -d

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}-------------------------------------------------------------------${NC}"
    echo -e "${GREEN}SUCCESS! The AI Resume Parser is running.${NC}"
    echo -e "\n${YELLOW}API is available at:${NC}    http://localhost:8000"
    echo -e "${YELLOW}API Docs (Swagger UI):${NC} http://localhost:8000/docs"
    echo -e "${GREEN}-------------------------------------------------------------------${NC}"
else
    echo -e "\n${RED}ERROR: Docker Compose failed to build or start.${NC}"
    echo "Please check the logs above for errors."
    exit 1
fi