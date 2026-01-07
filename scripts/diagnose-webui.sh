#!/bin/bash
#
# Pi Router - Web UI Diagnostic Script
# Checks why the web interface is not accessible
#

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
ICON_WARNING="⚠️"
ICON_INFO="ℹ"

echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║${NC}     ${BOLD}Pi Router Web UI Diagnostics${NC}         ${CYAN}${BOLD}║${NC}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}${ICON_WARNING} Note: Some checks require root privileges${NC}"
    echo -e "${YELLOW}  For full diagnostics, run: sudo $0${NC}"
    echo ""
fi

ISSUES=0

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}${ICON_CHECK} $2${NC}"
    else
        echo -e "${RED}${ICON_CROSS} $2${NC}"
        ((ISSUES++))
    fi
}

print_info() {
    echo -e "${CYAN}${ICON_INFO} $1${NC}"
}

# 1. Check if pi-router service is running
echo -e "${BOLD}1. Service Status${NC}"
if systemctl is-active --quiet pi-router; then
    print_status 0 "pi-router service is running"
    SYSTEMD_STATUS=$(systemctl status pi-router | grep "Active:" | awk '{print $2, $3}')
    echo -e "   Status: ${GREEN}${SYSTEMD_STATUS}${NC}"
else
    print_status 1 "pi-router service is NOT running"
    echo -e "   ${YELLOW}Try: sudo systemctl start pi-router${NC}"
fi
echo ""

# 2. Check if port 8080 is listening
echo -e "${BOLD}2. Port 8080 Status${NC}"
if command -v ss &> /dev/null; then
    PORT_INFO=$(ss -tlnp | grep :8080)
    if [ -n "$PORT_INFO" ]; then
        print_status 0 "Port 8080 is listening"
        echo -e "   ${PORT_INFO}"
    else
        print_status 1 "Port 8080 is NOT listening"
        echo -e "   ${YELLOW}The service is running but not accepting connections${NC}"
    fi
elif command -v netstat &> /dev/null; then
    PORT_INFO=$(netstat -tlnp 2>/dev/null | grep :8080)
    if [ -n "$PORT_INFO" ]; then
        print_status 0 "Port 8080 is listening"
        echo -e "   ${PORT_INFO}"
    else
        print_status 1 "Port 8080 is NOT listening"
    fi
else
    echo -e "${YELLOW}Cannot check port status (ss and netstat not available)${NC}"
fi
echo ""

# 3. Check process
echo -e "${BOLD}3. Process Status${NC}"
PYTHON_PROC=$(ps aux | grep -E "uvicorn|python.*main:app" | grep -v grep)
if [ -n "$PYTHON_PROC" ]; then
    print_status 0 "Python/Uvicorn process is running"
    echo -e "   PID: $(echo $PYTHON_PROC | awk '{print $2}')"
else
    print_status 1 "No Uvicorn process found"
fi
echo ""

# 4. Check service logs for errors
echo -e "${BOLD}4. Recent Service Logs${NC}"
if command -v journalctl &> /dev/null; then
    echo -e "${CYAN}Last 10 log lines:${NC}"
    journalctl -u pi-router -n 10 --no-pager 2>/dev/null || echo -e "${YELLOW}Cannot read logs${NC}"
else
    echo -e "${YELLOW}journalctl not available${NC}"
fi
echo ""

# 5. Check if frontend is built
echo -e "${BOLD}5. Frontend Files${NC}"
if [ -d "/opt/pi-router/frontend/dist" ]; then
    FILE_COUNT=$(find /opt/pi-router/frontend/dist -type f 2>/dev/null | wc -l)
    if [ "$FILE_COUNT" -gt 0 ]; then
        print_status 0 "Frontend files present ($FILE_COUNT files)"
    else
        print_status 1 "Frontend directory exists but is empty"
        echo -e "   ${YELLOW}Build the frontend:${NC}"
        echo -e "   cd frontend && npm install && npm run build"
        echo -e "   sudo cp -r dist/* /opt/pi-router/frontend/dist/"
    fi
else
    print_status 1 "Frontend directory not found"
    echo -e "   ${YELLOW}Build and install frontend:${NC}"
    echo -e "   cd frontend && npm install && npm run build"
    echo -e "   sudo mkdir -p /opt/pi-router/frontend/dist"
    echo -e "   sudo cp -r dist/* /opt/pi-router/frontend/dist/"
fi
echo ""

# 6. Check network interfaces
echo -e "${BOLD}6. Network Interfaces${NC}"
ip -4 addr show 2>/dev/null | grep -E "^\d|inet " | head -20 || echo -e "${YELLOW}Cannot check interfaces${NC}"
echo ""

# 7. Check configuration
echo -e "${BOLD}7. Configuration Files${NC}"
if [ -f /etc/pi-router/app.yaml ]; then
    print_status 0 "app.yaml exists"
    if grep -q "host:" /etc/pi-router/app.yaml; then
        HOST=$(grep "host:" /etc/pi-router/app.yaml | awk '{print $2}')
        PORT=$(grep "port:" /etc/pi-router/app.yaml | awk '{print $2}')
        echo -e "   Configured to listen on: ${CYAN}${HOST}:${PORT}${NC}"
    fi
else
    print_status 1 "app.yaml not found"
fi
echo ""

# 8. Check Python environment
echo -e "${BOLD}8. Python Environment${NC}"
if [ -d "/opt/pi-router/venv" ]; then
    print_status 0 "Python venv exists"
    PYTHON_VERSION=$(/opt/pi-router/venv/bin/python --version 2>&1)
    echo -e "   ${PYTHON_VERSION}"
else
    print_status 1 "Python venv not found"
fi

# Check if required packages are installed
if [ -d "/opt/pi-router/venv" ]; then
    INSTALLED=$(/opt/pi-router/venv/bin/pip list 2>/dev/null | grep -E "fastapi|uvicorn" | wc -l)
    if [ "$INSTALLED" -ge 2 ]; then
        print_status 0 "Required Python packages installed"
    else
        print_status 1 "Missing required Python packages"
        echo -e "   ${YELLOW}Install packages:${NC}"
        echo -e "   /opt/pi-router/venv/bin/pip install fastapi uvicorn"
    fi
fi
echo ""

# 9. Test local connection
echo -e "${BOLD}9. Local Connection Test${NC}"
if command -v curl &> /dev/null; then
    if curl -s http://localhost:8080 > /dev/null 2>&1; then
        print_status 0 "Local connection to port 8080 works"
    else
        print_status 1 "Cannot connect locally to port 8080"
    fi
else
    echo -e "${YELLOW}curl not available - cannot test connection${NC}"
fi
echo ""

# Summary
echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}${BOLD}Summary${NC}"
echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${NC}"

if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}${ICON_CHECK} No obvious issues found!${NC}"
    echo ""
    echo -e "${BOLD}Try accessing:${NC}"
    echo -e "  ${CYAN}http://localhost:8080${NC} (from the Pi itself)"
    echo -e "  ${CYAN}http://$(hostname -I | awk '{print $1}'):8080${NC} (from another device)"
    echo ""
    echo -e "${YELLOW}If still not working:${NC}"
    echo -e "  • Check firewall: sudo iptables -L -n"
    echo -e "  • Restart service: sudo systemctl restart pi-router"
    echo -e "  • Check full logs: sudo journalctl -u pi-router -f"
else
    echo -e "${RED}Found ${ISSUES} issue(s) - see details above${NC}"
    echo ""
    echo -e "${BOLD}Common fixes:${NC}"
    echo -e "  1. ${CYAN}Build frontend:${NC}"
    echo -e "     cd frontend && npm install && npm run build"
    echo -e "     sudo cp -r dist/* /opt/pi-router/frontend/dist/"
    echo ""
    echo -e "  2. ${CYAN}Restart service:${NC}"
    echo -e "     sudo systemctl restart pi-router"
    echo ""
    echo -e "  3. ${CYAN}Reinstall Python packages:${NC}"
    echo -e "     cd /opt/pi-router"
    echo -e "     source venv/bin/activate"
    echo -e "     pip install -r backend/requirements.txt"
    echo ""
    echo -e "  4. ${CYAN}Check service logs:${NC}"
    echo -e "     sudo journalctl -u pi-router -n 50"
fi
echo ""
