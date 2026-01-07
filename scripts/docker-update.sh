#!/bin/bash
#
# Pi Router - Docker Update Script
# Update Docker containers to latest version
#

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}Updating Pi Router Docker containers...${NC}"
echo ""

# Pull latest code
echo -e "${YELLOW}Pulling latest code...${NC}"
git pull

# Stop containers
echo -e "${YELLOW}Stopping containers...${NC}"
docker compose down

# Rebuild and start
echo -e "${YELLOW}Rebuilding containers...${NC}"
docker compose up -d --build --force-recreate

# Wait for startup
sleep 5

echo ""
echo -e "${GREEN}✓ Update complete!${NC}"
echo ""
echo "Check status: docker compose ps"
echo "View logs: docker compose logs -f"
