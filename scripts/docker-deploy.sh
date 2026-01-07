#!/bin/bash
#
# Pi Router - Docker Deployment Script
# Automated Docker deployment for Pi Router
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║${NC}     Pi Router Docker Deployment Script${NC}      ${CYAN}${BOLD}║${NC}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed${NC}"
    echo -e "${YELLOW}Installing Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo ""
    echo -e "${GREEN}Docker installed!${NC}"
    echo -e "${YELLOW}Please log out and log back in, then run this script again.${NC}"
    exit 0
fi

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo -e "${RED}Docker Compose is not available${NC}"
    echo -e "${YELLOW}Please install Docker Compose v2${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker is installed"

# Create necessary directories
echo ""
echo -e "${CYAN}Creating directories...${NC}"
mkdir -p config data
echo -e "${GREEN}✓${NC} Directories created"

# Check if .env exists
if [ ! -f .env ]; then
    echo ""
    echo -e "${CYAN}Creating environment file...${NC}"
    cp .env.example .env

    # Generate secure secret key
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env

    echo -e "${YELLOW}⚠${NC}  Created .env file with defaults"
    echo -e "${YELLOW}⚠${NC}  Please edit .env and change:"
    echo -e "       - ADMIN_PASSWORD"
    echo -e "       - AP_PASSWORD"
    echo ""
    read -p "Press Enter to continue (or Ctrl+C to edit .env first)..."
else
    echo -e "${GREEN}✓${NC} Environment file exists"
fi

# Check WiFi interfaces
echo ""
echo -e "${CYAN}Checking WiFi interfaces...${NC}"
if [ -d /sys/class/net/wlan0 ]; then
    echo -e "${GREEN}✓${NC} wlan0 detected (uplink)"
else
    echo -e "${YELLOW}⚠${NC}  wlan0 not found"
fi

if [ -d /sys/class/net/wlan1 ]; then
    echo -e "${GREEN}✓${NC} wlan1 detected (AP)"
else
    echo -e "${YELLOW}⚠${NC}  wlan1 not found - will activate when connected"
fi

# Build and start containers
echo ""
echo -e "${CYAN}Building and starting containers...${NC}"
docker compose up -d --build

# Wait for services to be healthy
echo ""
echo -e "${CYAN}Waiting for services to start...${NC}"
sleep 10

# Check status
echo ""
if docker compose ps | grep -q "Up"; then
    echo -e "${GREEN}✓${NC} Containers are running"
    echo ""
    echo -e "${CYAN}${BOLD}Deployment successful!${NC}"
    echo ""
    echo -e "${BOLD}Access the web UI at:${NC}"
    PI_IP=$(hostname -I | awk '{print $1}')
    echo -e "   ${CYAN}http://${PI_IP}:80${NC}"
    echo ""
    echo -e "${BOLD}Default credentials:${NC}"
    echo -e "   Username: ${GREEN}admin${NC}"
    echo -e "   Password: ${GREEN}admin123${NC}"
    echo -e "   ${RED}IMPORTANT: Change password after first login!${NC}"
    echo ""
    echo -e "${BOLD}Useful commands:${NC}"
    echo -e "  View logs:     ${CYAN}docker compose logs -f${NC}"
    echo -e "  Stop services: ${CYAN}docker compose down${NC}"
    echo -e "  Restart:       ${CYAN}docker compose restart${NC}"
else
    echo -e "${RED}✗${NC} Deployment failed"
    echo -e "${YELLOW}Check logs:${NC} docker compose logs"
    exit 1
fi
