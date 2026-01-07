#!/bin/bash
#
# Pi Router - Docker Backup Script
# Backup configuration and data from Docker deployment
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Create backup
BACKUP_FILE="pi-router-backup-$(date +%Y%m%d-%H%M%S).tar.gz"

echo -e "${CYAN}Creating backup...${NC}"
echo ""

# Stop containers first
echo -e "${YELLOW}Stopping containers...${NC}"
docker compose down

# Create backup
echo -e "${YELLOW}Backing up config and data...${NC}"
tar -czf "$BACKUP_FILE" config/ data/

# Start containers again
echo -e "${YELLOW}Restarting containers...${NC}"
docker compose up -d

echo ""
echo -e "${GREEN}✓ Backup created: ${BACKUP_FILE}${NC}"
echo ""
echo "To restore:"
echo "  tar -xzf $BACKUP_FILE"
echo "  docker compose up -d"
