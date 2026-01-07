# Pi Router - Complete Installation Guide for Raspberry Pi 5

> **JPHsystems 2026**

This guide will walk you through installing and configuring the Pi Router on your Raspberry Pi 5 with step-by-step instructions.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Structure on the Pi](#project-structure-on-the-pi)
3. [Files That Will Be Added/Modified](#files-that-will-be-addedmodified)
4. [Installation Steps](#installation-steps)
5. [Post-Installation Configuration](#post-installation-configuration)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware
- Raspberry Pi 5 (or Pi 4)
- MicroSD card (16GB minimum, 32GB recommended)
- Two Wi-Fi interfaces:
  - Built-in Wi-Fi + USB Wi-Fi adapter, OR
  - Two USB Wi-Fi adapters
- Power supply (27W USB-C recommended for Pi 5)

### Software
- Raspberry Pi OS (Bookworm or later) - 64-bit recommended
- Internet connection for initial setup
- SSH access (enabled) or direct keyboard/monitor

### Initial Pi Setup
```bash
# Update your system
sudo apt update && sudo apt upgrade -y

# Enable SSH if not already enabled
sudo raspi-config
# Navigate to Interface Options → SSH → Enable

# Set a static IP for the Pi (optional but recommended)
# Edit: sudo nano /etc/dhcpcd.conf
# Add: interface wlan0
#      static ip_address=192.168.1.50/24
#      static routers=192.168.1.1
#      static domain_name_servers=8.8.8.8
```

---

## Project Structure on the Pi

The project will be installed in the following locations:

```
/opt/pi-router/              # Main application directory
├── backend/                 # Python FastAPI backend
│   ├── main.py
│   ├── config/
│   ├── services/
│   ├── api/
│   ├── database/
│   └── requirements.txt
├── frontend/dist/           # Built React frontend (static files)
│   ├── index.html
│   └── assets/
└── venv/                    # Python virtual environment

/etc/pi-router/              # Configuration directory
├── network.yaml            # Network configuration (uplink, AP, DHCP)
├── app.yaml                # Application configuration
└── network.yaml.backup     # Automatic backups

/var/lib/pi-router/          # State and data directory
├── pi-router.db            # SQLite database (devices, logs, events)
└── pi-router.db.backup     # Database backups

/usr/local/sbin/            # Privilege escalation helper scripts
├── pi-router-update-uplink
├── pi-router-update-ap
├── pi-router-update-dhcp
├── pi-router-install-sysctl
└── pi-router-save-nftables

/etc/systemd/system/        # Systemd service
└── pi-router.service       # Auto-start on boot

/etc/sudoers.d/             # Sudo permissions for web UI
└── pi-router               # Controlled sudo access

/etc/wpa_supplicant/        # WPA supplicant configs
└── wpa_supplicant-wlan0.conf  # Uplink Wi-Fi configuration

/etc/hostapd/               # Hostapd (AP) config
└── hostapd.conf            # AP configuration

/etc/dnsmasq.d/             # Dnsmasq (DHCP/DNS) config
└── pi-router.conf          # DHCP configuration

/etc/network/interfaces.d/  # Network interface configs
└── wlan1                   # Static IP for wlan1

/etc/nftables.d/            # Firewall rules
└── pi-router.nft           # NAT rules

/etc/sysctl.d/              # System parameters
└── 99-pi-router-forwarding.conf  # IP forwarding
```

### Why These Locations?

| Directory | Purpose | Standard? |
|-----------|---------|----------|
| `/opt/pi-router` | Third-party application | ✓ Linux standard |
| `/etc/pi-router` | Application config | ✓ Linux standard |
| `/var/lib/pi-router` | Application data/state | ✓ Linux standard |
| `/usr/local/sbin` | Local admin scripts | ✓ Linux standard |
| `/etc/systemd/system` | System services | ✓ Systemd standard |
| `/etc/sudoers.d` | Sudo configurations | ✓ Linux standard |

---

## Files That Will Be Added/Modified

### New Files Created by Installer

#### System Files
```
/etc/systemd/system/pi-router.service
/etc/sudoers.d/pi-router
/etc/network/interfaces.d/wlan1
/etc/sysctl.d/99-pi-router-forwarding.conf
/etc/nftables.d/pi-router.nft
/etc/dnsmasq.d/pi-router.conf
/usr/local/sbin/pi-router-update-uplink
/usr/local/sbin/pi-router-update-ap
/usr/local/sbin/pi-router-update-dhcp
/usr/local/sbin/pi-router-install-sysctl
/usr/local/sbin/pi-router-save-nftables
```

#### Optional Files (created by fix-wlan1.sh script)
```
/etc/NetworkManager/conf.d/unmanaged.conf  # Prevents NetworkManager from managing wlan1
/etc/udev/rules.d/90-nm-unmanage-wlan1.rules  # Udev rule to unmanage wlan1
/etc/dhcpcd.conf.backup-*  # Backups of dhcpcd.conf before modifications
```

#### Application Files
```
/opt/pi-router/ (entire directory tree)
/etc/pi-router/network.yaml
/etc/pi-router/app.yaml
/var/lib/pi-router/pi-router.db
```

### Modified System Files

#### 1. `/etc/dhcpcd.conf`
**Added by installer or fix-wlan1.sh script:**
```
# Pi Router - wlan1 configuration
# Prevent dhcpcd from managing wlan1 (AP interface)
denyinterfaces wlan1

# Explicitly allow wlan0 as the only managed WiFi interface
allowinterfaces wlan0

# Set routing metrics to ensure wlan0 is always preferred
interface wlan0
metric 100  # Lower metric = higher priority (default route)

# wlan1 should never get a default route
interface wlan1
metric 200  # Higher metric = lower priority
nooption routers
```
**Purpose:**
- Prevents dhcpcd from managing wlan1 (we want static IP for AP)
- Ensures only wlan0 gets DHCP configuration
- Sets routing metrics to prioritize wlan0 as the upstream interface
- Prevents wlan1 from ever becoming the default route (internet connection)
- **Backup:** The installer/fix script backs up the original file before modifications

**Understanding the Configuration:**
- **denyinterfaces wlan1**: DHCP client will never request an IP for wlan1
- **allowinterfaces wlan0**: Only wlan0 is managed by DHCP client
- **metric 100/200**: Lower metric values have higher priority for routing
- **nooption routers**: Prevents wlan1 from receiving a default gateway

This ensures wlan0 is always the preferred upstream connection and wlan1 can never accidentally become the internet connection.

#### 2. `/etc/wpa_supplicant/wpa_supplicant-wlan0.conf`
**Created/Maintained by:** Web UI
**Contains:** Uplink Wi-Fi configuration
```
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YourWiFiSSID"
    psk="YourWiFiPassword"
    key_mgmt=WPA-PSK
}
```

#### 3. `/etc/hostapd/hostapd.conf`
**Created/Maintained by:** Web UI
**Contains:** AP configuration
```
interface=wlan1
driver=nl80211
ssid=PiRouter-AP
hw_mode=g
channel=6
country_code=US
auth_algs=1
wpa=2
wpa_passphrase=YourAPPassword
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
```

---

## Installation Steps

### Step 1: Prepare Your Pi

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install basic tools
sudo apt install -y git curl

# 3. Create working directory
cd /tmp
```

### Step 2: Download the Project

```bash
# Option A: Clone from Git (if available)
git clone https://github.com/yourusername/pi-router.git
cd pi-router

# Option B: Copy files (if you have them locally)
# Copy the entire project folder to /tmp/pi-router
```

### Step 3: Run the Installer

```bash
# Make the installer executable
chmod +x scripts/install.sh

# Run with sudo (required for system file installation)
sudo ./scripts/install.sh
```

**What the installer does:**
1. Installs system packages (hostapd, dnsmasq, nftables, Python, etc.)
2. Configures network interfaces
3. Creates user `pi-router`
4. Installs Python dependencies in `/opt/pi-router/venv`
5. Copies backend files to `/opt/pi-router/backend`
6. Creates configuration directories
7. Installs privilege escalation helpers
8. Configures sudo permissions
9. Enables IP forwarding
10. Installs systemd service
11. Enables and starts services

### Step 4: Build the Frontend

```bash
# Navigate to frontend directory
cd /tmp/pi-router/frontend

# Install Node.js dependencies (if not already installed)
sudo apt install -y nodejs npm

# Install frontend dependencies
npm install

# Build the frontend (creates optimized production files)
npm run build

# Copy built files to application directory
sudo cp -r dist/* /opt/pi-router/frontend/dist/

# Set permissions
sudo chown -R pi-router:pi-router /opt/pi-router/frontend/dist
```

### Step 5: Start the Service

```bash
# Enable auto-start on boot
sudo systemctl enable pi-router

# Start the service now
sudo systemctl start pi-router

# Check status
sudo systemctl status pi-router
```

### Step 6: Access the Web UI

```bash
# Find your Pi's IP address
hostname -I

# Or check wlan0 specifically
ip addr show wlan0 | grep inet
```

Then open your browser and navigate to:
```
http://<your-pi-ip>:8080
```

**Default credentials:**
- Username: `admin`
- Password: `admin123`

**⚠️ IMPORTANT:** Change the password immediately after first login!

---

## Post-Installation Configuration

### 1. Configure Uplink (Internet Connection)

1. Go to **Network** tab in the web UI
2. Under "Uplink (wlan0) - Internet Connection":
   - Select **WPA (Normal Wi-Fi)** for standard Wi-Fi
   - OR select **Captive Portal** for hotels/airports
3. Enter your Wi-Fi credentials:
   - SSID (network name)
   - Password
   - Country code
4. Click **Apply Uplink Settings**
5. Wait for connection (check status)

### 2. Configure Access Point (Your Router's Wi-Fi)

1. Go to **Network** tab
2. Under "Access Point (wlan1) - Your Router's Wi-Fi":
   - Set SSID (e.g., "MyRouter")
   - Set password (minimum 8 characters)
   - Choose channel (1, 6, or 11 recommended)
   - Hardware mode: g (2.4GHz) or ac (5GHz)
3. Click **Apply AP Settings**

### 3. Enable NAT and IP Forwarding

1. Go to **Settings** tab
2. Click **Enable NAT & IP Forwarding**
3. This allows your devices to access the internet through the uplink

### 4. Change Admin Password

1. Go to **Settings** tab
2. Under "Change Password":
   - Enter current password
   - Enter new password
3. Click **Update Password**

---

## Verification

### Check if Services Are Running

```bash
# Check Pi Router web UI
sudo systemctl status pi-router
# Should show: Active: active (running)

# Check hostapd (AP)
sudo systemctl status hostapd
# Should show: Active: active (running)

# Check dnsmasq (DHCP/DNS)
sudo systemctl status dnsmasq
# Should show: Active: active (running)

# Check IP forwarding
sysctl net.ipv4.ip_forward
# Should show: net.ipv4.ip_forward = 1

# Check NAT rules
sudo nft list ruleset
# Should show masquerade and forwarding rules
```

### Check Network Interfaces

```bash
# Check wlan0 (uplink)
ip addr show wlan0
# Should have an IP from your main network

# Check wlan1 (AP)
ip addr show wlan1
# Should have IP: 10.42.0.1

# Check connected devices
sudo dnsmasq --dhcp-leasefile=/var/lib/misc/dnsmasq.leases --dhcp-leases
```

### Test from a Client Device

1. **Connect to your AP Wi-Fi** (SSID you configured)
2. **You should get an IP** in the range 10.42.0.50 - 10.42.0.200
3. **Check connectivity:**
   ```bash
   # On your client device
   ping 8.8.8.8
   curl https://www.google.com
   ```

---

## Troubleshooting

### AP Not Starting

```bash
# Check hostapd logs
sudo journalctl -u hostapd -n 50

# Check config syntax
sudo hostapd -d /etc/hostapd/hostapd.conf

# Common issues:
# - Channel not supported by your Wi-Fi adapter
# - Country code mismatch
# - Another process using wlan1
```

### No Internet Access

```bash
# Check if uplink is connected
iwconfig wlan0

# Check if wlan0 has IP
ip addr show wlan0

# Check if IP forwarding is enabled
sysctl net.ipv4.ip_forward

# Check NAT rules
sudo nft list table nat
sudo nft list table inet filter

# Test DNS
nslookup google.com 8.8.8.8
```

### Web UI Not Accessible

```bash
# Check service status
sudo systemctl status pi-router

# Check service logs
sudo journalctl -u pi-router -n 100

# Check if port 8080 is listening
sudo ss -tlnp | grep 8080

# Restart the service
sudo systemctl restart pi-router
``### DHCP Not Working

```bash
# Check dnsmasq
sudo systemctl status dnsmasq
sudo journalctl -u dnsmasq -n 50

# Test dnsmasq config
sudo dnsmasq --test

# Check lease file
cat /var/lib/misc/dnsmasq.leases

# Verify wlan1 has static IP
ip addr show wlan1
```

### Factory Reset

If things go wrong, reset to defaults:

```bash
# Option 1: Via web UI
# Go to Settings → Factory Reset

# Option 2: Manually
sudo rm /etc/pi-router/network.yaml
sudo rm /etc/pi-router/app.yaml
sudo systemctl restart pi-router

# Then reconfigure through web UI
```

### Restore from Backup

```bash
# List available backups
ls -la /etc/pi-router/*.backup

# Restore network config
sudo cp /etc/pi-router/network.yaml.backup /etc/pi-router/network.yaml

# Restart service
sudo systemctl restart pi-router
```

---

## Service Management

### Start/Stop/Restart

```bash
# Start
sudo systemctl start pi-router

# Stop
sudo systemctl stop pi-router

# Restart
sudo systemctl restart pi-router

# Reload (without disconnecting clients)
sudo systemctl reload pi-router
```

### Enable/Disable Auto-Start

```bash
# Enable on boot
sudo systemctl enable pi-router

# Disable on boot
sudo systemctl disable pi-router
```

### View Logs

```bash
# Live logs
sudo journalctl -u pi-router -f

# Last 100 lines
sudo journalctl -u pi-router -n 100

# Since last boot
sudo journalctl -u pi-router -b

# Export logs to file
sudo journalctl -u pi-router > pi-router-logs.txt
```

---

## Uninstallation

If you need to completely remove the Pi Router:

```bash
cd /path/to/pi-router
sudo ./scripts/uninstall.sh
```

**What gets removed:**
- `/opt/pi-router/` (application files)
- `/etc/pi-router/` (configuration)
- `/var/lib/pi-router/` (data, unless you choose to keep it)
- `/usr/local/sbin/pi-router-*` (helper scripts)
- `/etc/sudoers.d/pi-router` (sudo permissions)
- `/etc/systemd/system/pi-router.service` (service)
- `pi-router` user

**What stays:**
- `/etc/hostapd/hostapd.conf` (AP config)
- `/etc/dnsmasq.d/pi-router.conf` (DHCP config)
- `/etc/wpa_supplicant/wpa_supplicant-wlan0.conf` (uplink config)
- These are kept so you can manually restore if needed

---

## Security Best Practices

1. **Change Default Password**
   ```bash
   # Via web UI: Settings → Change Password
   ```

2. **Keep System Updated**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

3. **Use Strong Wi-Fi Passwords**
   - Minimum 8 characters
   - Mix of letters, numbers, symbols
   - Avoid common words

4. **Limit Web UI Access** (Optional)
   ```bash
   # Configure firewall to only allow local network
   sudo nft add rule inet filter input ip saddr 10.42.0.0/24 tcp dport 8080 accept
   sudo nft add rule inet filter input tcp dport 8080 drop
   ```

5. **Regular Backups**
   ```bash
   # Backup config
   sudo cp /etc/pi-router/*.yaml ~/pi-router-backup/

   # Backup database
   sudo cp /var/lib/pi-router/pi-router.db ~/pi-router-backup/
   ```

---

## Advanced Configuration

### Change Web UI Port

Edit `/etc/pi-router/app.yaml`:
```yaml
port: 8080  # Change to your desired port
```

Then restart:
```bash
sudo systemctl restart pi-router
```

### Change DHCP Range

1. Go to **Network** tab in web UI
2. Expand "DHCP Settings (Advanced)"
3. Change range start/end
4. Click **Apply DHCP Settings**

### Change AP Subnet

1. Go to **Network** tab
2. Expand "DHCP Settings (Advanced)"
3. Change subnet, netmask, gateway
4. Click **Apply DHCP Settings**
5. **Note:** You'll need to reconnect devices after this

---

## Getting Help

### Collect Debug Information

```bash
# Generate full diagnostic report
sudo journalctl -u pi-router -u hostapd -u dnsmasq -b > diagnostics.txt
ip addr show >> diagnostics.txt
sudo nft list ruleset >> diagnostics.txt
sysctl net.ipv4.ip_forward >> diagnostics.txt
```

### Useful Commands

```bash
# Scan for Wi-Fi networks (uplink options)
sudo iwlist wlan0 scan | grep ESSID

# Check Wi-Fi signal strength
sudo iwconfig wlan0

# Monitor DHCP activity in real-time
sudo journalctl -u dnsmasq -f

# See current connections
sudo netstat -tn | grep :8080

# Check system resources
htop
```

---

## File Locations Summary

| File Location | Purpose | Editable by Web UI? |
|---------------|---------|---------------------|
| `/opt/pi-router/backend/` | Application code | No (code files) |
| `/opt/pi-router/frontend/dist/` | Web UI files | No (built files) |
| `/etc/pi-router/network.yaml` | Network config | Yes |
| `/etc/pi-router/app.yaml` | App config | Manual only |
| `/var/lib/pi-router/pi-router.db` | Database | Via Web UI |
| `/etc/hostapd/hostapd.conf` | AP config | Yes |
| `/etc/dnsmasq.d/pi-router.conf` | DHCP config | Yes |
| `/etc/wpa_supplicant/wpa_supplicant-wlan0.conf` | Uplink Wi-Fi | Yes |
| `/etc/systemd/system/pi-router.service` | Service config | Manual only |
| `/etc/sudoers.d/pi-router` | Sudo rules | Manual only |

---

## Quick Reference Card

```
╔════════════════════════════════════════════════════════════════╗
║                    Pi Router Quick Reference                    ║
╠════════════════════════════════════════════════════════════════╣
║  Application:  /opt/pi-router                                    ║
║  Config:       /etc/pi-router                                   ║
║  Database:     /var/lib/pi-router/pi-router.db                  ║
║  Service:      pi-router.service                                ║
║  Web UI:       http://<pi-ip>:8080                              ║
║  Defaults:     admin / admin123                                 ║
╠════════════════════════════════════════════════════════════════╣
║  Commands:                                                   ║
║    sudo systemctl start pi-router                            ║
║    sudo systemctl stop pi-router                             ║
║    sudo systemctl restart pi-router                           ║
║    sudo systemctl status pi-router                            ║
║    sudo journalctl -u pi-router -f                            ║
╚════════════════════════════════════════════════════════════════╝
```

---

**JPHsystems 2026**
