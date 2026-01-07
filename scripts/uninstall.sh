#!/bin/bash
#
# Pi Router Uninstallation Script
# Removes all installed components
#

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  Pi Router Uninstallation Script${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run this script as root${NC}"
    exit 1
fi

# Stop and disable service
echo -e "${YELLOW}Stopping services...${NC}"
systemctl stop pi-router.service 2>/dev/null || true
systemctl disable pi-router.service 2>/dev/null || true

# Remove systemd files
echo -e "${YELLOW}Removing systemd service...${NC}"
rm -f /etc/systemd/system/pi-router.service
systemctl daemon-reload

# Remove helper scripts
echo -e "${YELLOW}Removing helper scripts...${NC}"
rm -f /usr/local/sbin/pi-router-*

# Remove sudoers configuration
echo -e "${YELLOW}Removing sudoers configuration...${NC}"
rm -f /etc/sudoers.d/pi-router

# Remove application files
echo -e "${YELLOW}Removing application files...${NC}"
rm -rf /opt/pi-router
rm -rf /etc/pi-router
rm -f /etc/sysctl.d/99-pi-router-forwarding.conf
rm -f /etc/nftables.d/pi-router.nft
rm -f /etc/dnsmasq.d/pi-router.conf

# Remove user
echo -e "${YELLOW}Removing user...${NC}"
userdel pi-router 2>/dev/null || true

echo ""
echo -e "${GREEN}Uninstallation complete!${NC}"
echo ""
echo -e "Note: Configuration data in /var/lib/pi-router was preserved."
echo -e "To remove it, run: rm -rf /var/lib/pi-router"
echo ""
