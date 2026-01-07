#!/bin/bash
#
# Pi Router - Pull and Update from GitHub Script
# This script pulls latest changes from GitHub and rebuilds the frontend
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Pi Router - Update from GitHub${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if git repository exists
if [ ! -d ".git" ]; then
    echo -e "${RED}Error: Not a git repository${NC}"
    exit 1
fi

echo -e "${YELLOW}Fetching latest changes...${NC}"
git fetch origin

# Check if there are changes to pull
CURRENT_COMMIT=$(git rev-parse HEAD)
UPSTREAM_COMMIT=$(git rev-parse '@{u}')

if [ "$CURRENT_COMMIT" = "$UPSTREAM_COMMIT" ]; then
    echo -e "${GREEN}Already up to date!${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}Changes found on GitHub. Pulling...${NC}"
echo ""
git pull origin $(git rev-parse --abbrev-ref HEAD)

echo ""
echo -e "${YELLOW}Rebuilding frontend...${NC}"
cd frontend
npm install
npm run build

echo ""
echo -e "${YELLOW}Copying frontend files...${NC}"
sudo cp -r dist/* /opt/pi-router/frontend/dist/

echo ""
echo -e "${YELLOW}Restarting Pi Router service...${NC}"
sudo systemctl restart pi-router

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Update complete!${NC}"
echo -e "${GREEN}========================================${NC}"
