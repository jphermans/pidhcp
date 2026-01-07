#!/bin/bash
#
# Pi Router Installation Script
# For Raspberry Pi 5 (Debian/Raspberry Pi OS)
#
# This script installs all dependencies and sets up the Pi Router service
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Icons
ICON_CHECK="✓"
ICON_CROSS="✗"
ICON_ARROW="→"
ICON_GEAR="⚙"
ICON_PACKAGE="📦"
ICON_NETWORK="🌐"
ICON_DATABASE="🗄️"
ICON_SECURITY="🔒"
ICON_ROCKET="🚀"
ICON_FOLDER="📁"
ICON_WARNING="⚠️"

# Print section header
print_header() {
    echo ""
    echo -e "${CYAN}${BOLD}$1${NC}"
    echo -e "${CYAN}$(printf '=%.0s' {1..50})${NC}"
}

# Print step
print_step() {
    echo ""
    echo -e "${BLUE}${ICON_ARROW} $1${NC}"
}

# Print success
print_success() {
    echo -e "${GREEN}${ICON_CHECK} $1${NC}"
}

# Print info
print_info() {
    echo -e "  ${CYAN}• $1${NC}"
}

# Print warning
print_warning() {
    echo -e "${YELLOW}${ICON_WARNING} $1${NC}"
}

echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║${NC}     ${CYAN}${BOLD}Pi Router Installation Script${NC}            ${GREEN}${BOLD}║${NC}"
echo -e "${GREEN}${BOLD}║${NC}     ${YELLOW}for Raspberry Pi 5${NC}                          ${GREEN}${BOLD}║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}${ICON_CROSS} Please run this script as root${NC}"
    echo -e "${YELLOW}  Run: sudo ./scripts/install.sh${NC}"
    exit 1
fi

# Detect OS
if [ ! -f /etc/os-release ]; then
    echo -e "${RED}${ICON_CROSS} Cannot detect OS${NC}"
    exit 1
fi
source /etc/os-release

print_info "Detected OS: ${BOLD}$PRETTY_NAME${NC}"
print_info "Installing to: ${BOLD}/opt/pi-router${NC}"
print_info "Persistent data: ${BOLD}/var/lib/pi-router/data${NC}"

# Step 1: Update system
print_header "${ICON_PACKAGE} STEP 1/9: Updating System Packages"
print_step "Updating package lists and upgrading system..."
apt-get update -qq
apt-get upgrade -y -qq
print_success "System updated successfully"

# Step 2: Install system dependencies
print_header "${ICON_PACKAGE} STEP 2/9: Installing System Dependencies"
print_step "Installing required packages..."
echo ""
apt-get install -y \
    hostapd \
    dnsmasq \
    nftables \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    gcc \
    git \
    curl \
    iw \
    wireless-tools \
    net-tools \
    wpasupplicant \
    network-manager \
    udev

print_success "System dependencies installed"
echo ""
print_info "Installed packages:"
print_info "  • hostapd - Access Point daemon"
print_info "  • dnsmasq - DHCP/DNS server"
print_info "  • nftables - Firewall/NAT"
print_info "  • python3 - Backend runtime"
print_info "  • wpa_supplicant - Wi-Fi client"
print_info "  • iw/wireless-tools - Wireless configuration"
print_info "  • network-manager - Network management (optional)"
print_info "  • udev - Device management (for auto-detection)"

# Step 3: Configure network interfaces
print_header "${ICON_NETWORK} STEP 3/9: Configuring Network Interfaces"

# Check if wlan1 exists
WLAN1_EXISTS=false
if ip link show wlan1 >/dev/null 2>&1; then
    WLAN1_EXISTS=true
    print_info "wlan1 detected - will configure as Access Point"
else
    print_warning "wlan1 not detected - installation will continue"
    print_info "AP will activate automatically when wlan1 is connected"
fi

print_step "Setting up wlan1 (Access Point) interface..."

# Create interfaces.d directory if it doesn't exist
mkdir -p /etc/network/interfaces.d/

# Create wlan1 static configuration
cat > /etc/network/interfaces.d/wlan1 << 'EOF'
auto wlan1
iface wlan1 inet static
    address 10.42.0.1
    netmask 255.255.255.0
EOF

# Configure dhcpcd to ignore wlan1
if [ -f /etc/dhcpcd.conf ]; then
    if ! grep -q "denyinterfaces wlan1" /etc/dhcpcd.conf 2>/dev/null; then
        echo "denyinterfaces wlan1" >> /etc/dhcpcd.conf
    fi
else
    print_warning "dhcpcd.conf not found - skipping dhcpcd configuration"
fi

print_success "Network interfaces configured"
echo ""
print_info "wlan0 - Uplink connection (client mode)"
print_info "wlan1 - Access Point (10.42.0.1/24)"
if [ "$WLAN1_EXISTS" = false ]; then
    print_warning "wlan1 not present - will auto-configure when connected"
fi

# Step 4: Install Python dependencies
print_header "${ICON_GEAR} STEP 4/9: Installing Python Dependencies"
print_step "Creating Python virtual environment..."
mkdir -p /opt/pi-router
python3 -m venv /opt/pi-router/venv
source /opt/pi-router/venv/bin/activate

print_step "Installing Python packages..."
pip install --upgrade pip -qq
pip install fastapi uvicorn[standard] pydantic pydantic-settings \
    python-multipart passlib[bcrypt] python-jose[cryptography] \
    aiofiles psutil pyyaml aiosqlite \
    boto3 requests -qq

print_success "Python dependencies installed"
echo ""
print_info "Installed: FastAPI, Uvicorn, SQLite, JWT auth, system monitoring"
print_info "Backup support: AWS S3 (boto3), WebDAV (requests)"

# Step 5: Create directories and copy files
print_header "${ICON_FOLDER} STEP 5/9: Creating Directories and Installing Files"
print_step "Creating system user and directories..."

# Create user
useradd -r -s /bin/false -d /var/lib/pi-router pi-router 2>/dev/null || true

# Create directories
mkdir -p /etc/pi-router
mkdir -p /var/lib/pi-router
mkdir -p /var/lib/pi-router/data  # Persistent data directory
mkdir -p /opt/pi-router/backend
mkdir -p /opt/pi-router/frontend/dist
mkdir -p /usr/local/sbin

# Create symlink from backend to persistent data
ln -sf /var/lib/pi-router/data /opt/pi-router/backend/data

print_step "Copying application files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cp -r "$PROJECT_ROOT/backend/"* /opt/pi-router/backend/

# Set permissions
chown -R pi-router:pi-router /var/lib/pi-router
chmod 755 /opt/pi-router

print_success "Files installed"
echo ""
print_info "Application location: /opt/pi-router"
print_info "${GREEN}${BOLD}Persistent data: /var/lib/pi-router/data${NC}"
print_warning "Your database and settings will survive all updates!"

# Step 6: Install privilege escalation helpers
print_header "${ICON_SECURITY} STEP 6/9: Installing Security Helpers"
print_step "Installing privilege escalation scripts..."

# Copy helper scripts
cp "$SCRIPT_DIR/pi-router-update-uplink" /usr/local/sbin/
cp "$SCRIPT_DIR/pi-router-update-ap" /usr/local/sbin/
cp "$SCRIPT_DIR/pi-router-update-dhcp" /usr/local/sbin/
cp "$SCRIPT_DIR/pi-router-install-sysctl" /usr/local/sbin/
cp "$SCRIPT_DIR/pi-router-save-nftables" /usr/local/sbin/
cp "$SCRIPT_DIR/pi-router-service-control" /usr/local/sbin/
cp "$SCRIPT_DIR/pi-router-init-wlan1" /usr/local/sbin/

chmod +x /usr/local/sbin/pi-router-*

print_step "Configuring sudoers..."
# Configure sudoers
cat > /etc/sudoers.d/pi-router << 'EOF'
# Pi Router sudoers configuration
pi-router ALL=(ALL) NOPASSWD: /usr/local/sbin/pi-router-update-uplink
pi-router ALL=(ALL) NOPASSWD: /usr/local/sbin/pi-router-update-ap
pi-router ALL=(ALL) NOPASSWD: /usr/local/sbin/pi-router-update-dhcp
pi-router ALL=(ALL) NOPASSWD: /usr/local/sbin/pi-router-install-sysctl
pi-router ALL=(ALL) NOPASSWD: /usr/local/sbin/pi-router-save-nftables
pi-router ALL=(ALL) NOPASSWD: /usr/local/sbin/pi-router-service-control
pi-router ALL=(ALL) NOPASSWD: /bin/systemctl restart hostapd
pi-router ALL=(ALL) NOPASSWD: /bin/systemctl restart dnsmasq
pi-router ALL=(ALL) NOPASSWD: /bin/systemctl restart wpa_supplicant@wlan0
pi-router ALL=(ALL) NOPASSWD: /bin/systemctl start hostapd
pi-router ALL=(ALL) NOPASSWD: /bin/systemctl start dnsmasq
pi-router ALL=(ALL) NOPASSWD: /bin/systemctl stop hostapd
pi-router ALL=(ALL) NOPASSWD: /bin/systemctl stop dnsmasq
pi-router ALL=(ALL) NOPASSWD: /bin/systemctl is-active hostapd
pi-router ALL=(ALL) NOPASSWD: /bin/systemctl is-active dnsmasq
pi-router ALL=(ALL) NOPASSWD: /bin/systemctl is-enabled hostapd
pi-router ALL=(ALL) NOPASSWD: /bin/systemctl is-enabled dnsmasq
pi-router ALL=(ALL) NOPASSWD: /usr/bin/nft -f *
pi-router ALL=(ALL) NOPASSWD: /usr/sbin/sysctl -w net.ipv4.ip_forward=1
EOF

chmod 440 /etc/sudoers.d/pi-router

print_success "Security helpers installed"

# Step 7: Configure IP forwarding
print_header "${ICON_NETWORK} STEP 7/9: Configuring IP Forwarding"
print_step "Enabling IPv4 packet forwarding..."

cat > /etc/sysctl.d/99-pi-router-forwarding.conf << 'EOF'
net.ipv4.ip_forward=1
EOF

sysctl -w net.ipv4.ip_forward=1

print_success "IP forwarding enabled"
print_info "NAT routing is now active"

# Step 8: Install systemd service
print_header "${ICON_ROCKET} STEP 8/9: Installing Systemd Service"
print_step "Installing pi-router service..."

cp "$SCRIPT_DIR/../systemd/pi-router.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable pi-router.service

print_success "Systemd service installed"
print_info "Service will start automatically on boot"

# Step 9: Enable and start services
print_header "${ICON_ROCKET} STEP 9/9: Enabling Network Services"
print_step "Setting up wlan1 auto-activation..."

# Install udev rule for wlan1 detection
if [ -f "$SCRIPT_DIR/99-pi-router-wlan1.rules" ]; then
    cp "$SCRIPT_DIR/99-pi-router-wlan1.rules" /etc/udev/rules.d/
    udevadm control --reload-rules
    print_success "Udev rule installed - wlan1 will auto-activate when connected"
else
    print_warning "Udev rule file not found, skipping..."
fi

# Install systemd service that waits for wlan1
if [ -f "$SCRIPT_DIR/../systemd/pi-router-wait-wlan1.service" ]; then
    cp "$SCRIPT_DIR/../systemd/pi-router-wait-wlan1.service" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable pi-router-wait-wlan1.service
    print_success "Auto-activation service installed"
fi

print_step "Enabling hostapd and dnsmasq..."

# Unmask hostapd
systemctl unmask hostapd
systemctl enable hostapd

# Enable dnsmasq
systemctl enable dnsmasq

# Only start hostapd if wlan1 exists
if [ "$WLAN1_EXISTS" = true ]; then
    print_success "Network services enabled (wlan1 present - hostapd will start)"
else
    print_warning "wlan1 not detected - hostapd will start when wlan1 is connected"
fi

echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║${NC}       ${ICON_ROCKET} Installation Complete! ${GREEN}${BOLD}              ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}${BOLD}📋 Next Steps:${NC}"
echo ""
echo -e "${YELLOW}1. Build the frontend:${NC}"
echo -e "   cd ${PROJECT_ROOT}/frontend"
echo -e "   npm install"
echo -e "   npm run build"
echo -e "   sudo cp -r dist/* /opt/pi-router/frontend/dist/"
echo ""
echo -e "${YELLOW}2. Start the service:${NC}"
echo -e "   sudo systemctl start pi-router"
echo ""
echo -e "${YELLOW}3. Access the web UI:${NC}"
echo -e "   http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo -e "${YELLOW}4. Default login:${NC}"
echo -e "   Username: ${GREEN}admin${NC}"
echo -e "   Password: ${GREEN}admin123${NC}"
echo ""
echo -e "${YELLOW}5. Configure your Wi-Fi:${NC}"
echo -e "   • Uplink (wlan0): Connect to existing network"
echo -e "   • Access Point (wlan1): Create your own Wi-Fi"
echo ""
if [ "$WLAN1_EXISTS" = false ]; then
    echo -e "${GREEN}${BOLD}🔌 wlan1 Auto-Activation:${NC}"
    echo -e "   ${BOLD}wlan1 was not detected during installation.${NC}"
    echo -e "   The system is configured to automatically activate the AP"
    echo -e "   when you connect the wlan1 WiFi adapter:"
    echo -e "   • Just plug in your USB WiFi adapter"
    echo -e "   • The AP will start automatically (within 5-10 seconds)"
    echo -e "   • Check status: ${CYAN}sudo systemctl status hostapd${NC}"
    echo ""
fi
echo -e "${CYAN}${BOLD}📂 Important Locations:${NC}"
echo -e "   • Application: ${BOLD}/opt/pi-router${NC}"
echo -e "   • ${GREEN}${BOLD}Persistent data: /var/lib/pi-router/data${NC}"
echo -e "   • Logs: journalctl -u pi-router -f"
echo ""
echo -e "${CYAN}${BOLD}🔄 GitHub Sync:${NC}"
echo -e "   • Pull updates: ${BOLD}./scripts/sync-repo.sh${NC}"
echo -e "   • Your data is safe in /var/lib/pi-router/data"
echo ""
echo -e "${CYAN}${BOLD}🔧 Troubleshooting:${NC}"
echo -e "   • If wlan1 connects to your home network instead of being an AP:"
echo -e "   - Run: ${BOLD}sudo ./scripts/fix-wlan1.sh${NC}"
echo -e "   - This will disable wpa_supplicant on wlan1 and restore AP mode"
echo ""
print_warning "You may need to configure wlan0 manually first"
print_info "Use: sudo raspi-config → Localisation Options → Wireless LAN"
echo ""
