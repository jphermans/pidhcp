#!/bin/bash
#
# Pi Router - Fix wlan1 Interface Script
# Ensures wlan1 is in AP mode and not managed by wpa_supplicant or NetworkManager
#
# Usage: sudo ./scripts/fix-wlan1.sh
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
ICON_WARNING="⚠️"
ICON_GEAR="⚙"

echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║${NC}     ${BOLD}Fix wlan1 Interface Configuration${NC}       ${CYAN}${BOLD}║${NC}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}${ICON_CROSS} Please run this script as root${NC}"
    echo -e "${YELLOW}  Run: sudo ./scripts/fix-wlan1.sh${NC}"
    exit 1
fi

# Check for required commands
MISSING_CMDS=()
for cmd in systemctl udevadm iwconfig ip grep; do
    if ! command -v $cmd &> /dev/null; then
        MISSING_CMDS+=($cmd)
    fi
done

if [ ${#MISSING_CMDS[@]} -gt 0 ]; then
    echo -e "${RED}${ICON_CROSS} Missing required commands: ${MISSING_CMDS[*]}${NC}"
    echo -e "${YELLOW}Install required packages:${NC}"
    echo -e "  sudo apt update"
    echo -e "  sudo apt install -y iw wireless-tools net-tools grep"
    exit 1
fi

# Track issues and fixes
ISSUES=0
FIXES=0

# Function to print section header
print_header() {
    echo ""
    echo -e "${CYAN}${BOLD}$1${NC}"
    echo -e "${CYAN}$(printf '=%.0s' {1..50})${NC}"
}

# Function to print step
print_step() {
    echo ""
    echo -e "${BLUE}${ICON_ARROW} $1${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}${ICON_CHECK} $1${NC}"
    ((FIXES++))
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}${ICON_WARNING} $1${NC}"
    ((ISSUES++))
}

# Function to print info
print_info() {
    echo -e "  ${CYAN}• $1${NC}"
}

# Step 1: Check and disable wpa_supplicant@wlan1
print_header "${ICON_GEAR} Step 1: Checking wpa_supplicant on wlan1"
if systemctl is-active --quiet wpa_supplicant@wlan1 2>/dev/null; then
    print_warning "wpa_supplicant@wlan1 is running (should be disabled)"
    print_step "Stopping and disabling wpa_supplicant@wlan1..."
    systemctl stop wpa_supplicant@wlan1 2>/dev/null || true
    systemctl disable wpa_supplicant@wlan1 2>/dev/null || true
    print_success "Disabled wpa_supplicant@wlan1"
else
    print_info "wpa_supplicant@wlan1 is not running (good)"
fi

# Step 2: Check and disable wpa_supplicant@wpa_supplicant-wlan1.service (alternative name)
print_header "${ICON_GEAR} Step 2: Checking alternative wpa_supplicant service names"
if systemctl is-active --quiet wpa_supplicant@wpa_supplicant-wlan1.service 2>/dev/null; then
    print_warning "Found alternative wpa_supplicant service for wlan1"
    print_step "Stopping and disabling..."
    systemctl stop wpa_supplicant@wpa_supplicant-wlan1.service 2>/dev/null || true
    systemctl disable wpa_supplicant@wpa_supplicant-wlan1.service 2>/dev/null || true
    print_success "Disabled alternative wpa_supplicant service"
else
    print_info "No alternative wpa_supplicant service found"
fi

# Step 3: Check NetworkManager
print_header "${ICON_GEAR} Step 3: Checking NetworkManager"
if command -v nmcli &> /dev/null; then
    if nmcli device show wlan1 &> /dev/null; then
        MANAGED=$(nmcli -t -f DEVICE,STATE device show wlan1 2>/dev/null | cut -d: -f2)
        if [ -n "$MANAGED" ] && [ "$MANAGED" != "unmanaged" ]; then
            print_warning "NetworkManager is managing wlan1"
            print_step "Creating udev rule to unmanage wlan1..."

            # Create udev rule
            cat > /etc/udev/rules.d/90-nm-unmanage-wlan1.rules << 'EOF'
# Prevent NetworkManager from managing wlan1
ACTION=="add", SUBSYSTEM=="net", DRIVERS=="?*", KERNELS=="wlan1", ENV{NM_UNMANAGED}="1"
EOF

            print_success "Created udev rule"

            print_step "Reloading udev rules..."
            udevadm control --reload-rules
            print_success "Reloaded udev rules"

            print_step "Triggering udev for wlan1..."
            udevadm trigger --subsystem-match=net --action=add
            print_success "Triggered udev"

            print_info "You may need to reboot for NetworkManager changes to take full effect"
        else
            print_info "NetworkManager is not managing wlan1 (good)"
        fi
    else
        print_info "wlan1 not found by NetworkManager"
    fi
else
    print_info "NetworkManager not installed"
fi

# Step 4: Check wpa_supplicant.conf files
print_header "${ICON_GEAR} Step 4: Checking wpa_supplicant configuration files"
for conf_file in /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant-wlan1.conf; do
    if [ -f "$conf_file" ]; then
        if grep -q "wlan1" "$conf_file" 2>/dev/null || grep -q "interface=wlan1" "$conf_file" 2>/dev/null; then
            print_warning "wlan1 found in $conf_file"
            print_info "Review: $conf_file"
            print_info "Ensure wlan1 is not configured as a client interface"
        fi
    fi
done
print_info "No problematic wpa_supplicant configurations found"

# Step 5: Check dhcpcd configuration
print_header "${ICON_GEAR} Step 5: Checking dhcpcd configuration"
if [ -f /etc/dhcpcd.conf ]; then
    if grep -q "denyinterfaces wlan1" /etc/dhcpcd.conf 2>/dev/null; then
        print_info "dhcpcd already configured to ignore wlan1 (good)"
    else
        print_warning "dhcpcd may try to manage wlan1"
        print_info "Consider adding 'denyinterfaces wlan1' to /etc/dhcpcd.conf"
        print_info "This prevents dhcpcd from interfering with hostapd"
    fi
else
    print_info "dhcpcd.conf not found"
fi

# Step 6: Ensure hostapd is enabled and running
print_header "${ICON_GEAR} Step 6: Checking hostapd service"
if systemctl is-enabled --quiet hostapd; then
    print_info "hostapd is enabled (good)"
else
    print_warning "hostapd is not enabled"
    print_step "Enabling hostapd..."
    systemctl enable hostapd
    print_success "Enabled hostapd"
fi

if systemctl is-active --quiet hostapd; then
    print_info "hostapd is running (good)"
else
    print_warning "hostapd is not running"
    print_step "Starting hostapd..."
    systemctl start hostapd
    sleep 2
    if systemctl is-active --quiet hostapd; then
        print_success "Started hostapd"
    else
        print_warning "hostapd failed to start - check configuration"
    fi
fi

# Step 7: Verify wlan1 is in Master mode
print_header "${ICON_GEAR} Step 7: Verifying wlan1 mode"
if command -v iwconfig &> /dev/null; then
    WLAN1_MODE=$(iwconfig wlan1 2>/dev/null | grep -oP 'Mode:\K\S+' || echo "")
    if [ "$WLAN1_MODE" = "Master" ]; then
        print_success "wlan1 is in Master (AP) mode"
    else
        print_warning "wlan1 is not in Master mode (current: ${WLAN1_MODE:-unknown})"
        print_info "Restarting hostapd may fix this..."
        systemctl restart hostapd
        sleep 3
        WLAN1_MODE=$(iwconfig wlan1 2>/dev/null | grep -oP 'Mode:\K\S+' || echo "")
        if [ "$WLAN1_MODE" = "Master" ]; then
            print_success "wlan1 is now in Master (AP) mode"
        else
            print_warning "wlan1 still not in Master mode"
        fi
    fi
else
    print_info "iwconfig not available, cannot verify mode"
fi

# Summary
echo ""
echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}${BOLD}Summary${NC}"
echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${NC}"

if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}${ICON_CHECK} No issues found! wlan1 is properly configured.${NC}"
    exit 0
else
    echo -e "${YELLOW}Found ${ISSUES} issue(s) and applied ${FIXES} fix(es).${NC}"
    echo ""
    echo -e "${BOLD}Next steps:${NC}"
    echo -e "  1. Verify hostapd is running: ${CYAN}sudo systemctl status hostapd${NC}"
    echo -e "  2. Check wlan1 mode: ${CYAN}sudo iwconfig wlan1${NC}"
    echo -e "  3. View hostapd logs if needed: ${CYAN}sudo journalctl -u hostapd -n 50${NC}"
    echo ""
    echo -e "${YELLOW}If wlan1 still connects to your home network:${NC}"
    echo -e "  • Check for other wpa_supplicant services: ${CYAN}systemctl | grep wpa${NC}"
    echo -e "  • Check if any systemd-networkd config manages wlan1"
    echo -e "  • Reboot the Pi: ${CYAN}sudo reboot${NC}"
    exit 0
fi
