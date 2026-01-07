#!/bin/bash
#
# Pi Router - Initialize Configuration Files
# Creates default configuration files if they don't exist
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}Pi Router - Configuration Initialization${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root${NC}"
    echo "sudo $0"
    exit 1
fi

CONFIG_DIR="/etc/pi-router"
SERVICE_USER="pi-router"

# Create directory if it doesn't exist
if [ ! -d "$CONFIG_DIR" ]; then
    echo -e "${YELLOW}Creating $CONFIG_DIR${NC}"
    mkdir -p "$CONFIG_DIR"
fi

# Create app.yaml if it doesn't exist
if [ ! -f "$CONFIG_DIR/app.yaml" ]; then
    echo -e "${GREEN}Creating app.yaml${NC}"
    cat > "$CONFIG_DIR/app.yaml" << 'EOF'
# Pi Router Application Configuration
secret_key: "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION"
admin_username: admin
admin_password: admin123
log_level: INFO
host: 0.0.0.0
port: 8080
config_dir: /etc/pi-router
state_dir: /var/lib/pi-router
EOF
else
    echo -e "${GREEN}app.yaml already exists${NC}"
fi

# Create network.yaml if it doesn't exist
if [ ! -f "$CONFIG_DIR/network.yaml" ]; then
    echo -e "${GREEN}Creating network.yaml${NC}"
    cat > "$CONFIG_DIR/network.yaml" << 'EOF'
# Pi Router Network Configuration
uplink:
  mode: wpa
  ssid: ""
  password: ""
  country: US

ap:
  ssid: PiRouter-AP
  password: SecurePass123
  channel: 6
  country: US
  hw_mode: g

dhcp:
  subnet: 10.42.0.0
  netmask: 255.255.255.0
  gateway: 10.42.0.1
  range_start: 10.42.0.50
  range_end: 10.42.0.200
  lease_time: 12h
EOF
else
    echo -e "${GREEN}network.yaml already exists${NC}"
fi

# Set proper ownership
echo -e "${GREEN}Setting ownership to $SERVICE_USER:$SERVICE_USER${NC}"
chown -R $SERVICE_USER:$SERVICE_USER "$CONFIG_DIR"
chmod 755 "$CONFIG_DIR"
chmod 640 "$CONFIG_DIR"/*.yaml

echo ""
echo -e "${GREEN}✓ Configuration files initialized${NC}"
echo ""
echo -e "${CYAN}Config files created:${NC}"
ls -la "$CONFIG_DIR"/*.yaml
echo ""
echo -e "${YELLOW}IMPORTANT: Change the default passwords!${NC}"
echo "  • Admin password: admin123"
echo "  • AP password: SecurePass123"
echo "  • Secret key: CHANGE_THIS_SECRET_KEY_IN_PRODUCTION"
echo ""
echo -e "${CYAN}Restart the service:${NC}"
echo "  sudo systemctl restart pi-router"
