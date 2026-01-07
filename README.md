# Pi Router - Wi-Fi Router for Raspberry Pi 5

Turn your Raspberry Pi 5 into a full-featured Wi-Fi router with a modern web interface.

> **JPHsystems 2026**

![Pi Router](https://img.shields.io/badge/Raspberry_Pi-5-C51A4A?style=flat&logo=raspberry-pi)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- **Dual Wi-Fi Operation**: Connect to existing Wi-Fi (wlan0) and create your own AP (wlan1)
- **DHCP Server**: Automatic IP assignment with dnsmasq
- **NAT/Routing**: Full internet access for connected devices
- **Modern Web UI**: Clean, responsive interface built with React
- **Secure**: Authentication and encrypted credential storage
- **SQLite Database**: Persistent storage for settings and logs
- **Docker Support**: Easy containerized deployment
- **Visual Status Monitoring**: Real-time status with critical warnings for unavailable interfaces

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Raspberry Pi 5                          │
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │    wlan0     │         │    wlan1     │                 │
│  │  (Uplink)    │         │  (AP+DHCP)   │                 │
│  │              │         │  10.42.0.1   │                 │
│  └──────┬───────┘         └──────┬───────┘                 │
│         │                        │                          │
│         │        ┌───────────────┴───────┐                  │
│         │        │   NAT / Routing        │                  │
│         │        │   (nftables)           │                  │
│         │        └───────────────┬────────┘                  │
│         │                        │                          │
│  ┌──────┴────────────────────────┴────────┐                 │
│  │          Pi Router Web UI (FastAPI)    │                 │
│  │            :8080                        │                 │
│  └─────────────────────────────────────────┘                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Quick Start (Noob-Friendly Guide)

### Prerequisites

- Raspberry Pi 5 with Raspberry Pi OS (Bookworm or later)
- Two Wi-Fi adapters (built-in + USB, or dual USB)
- Internet connection for initial setup
- SSH access or direct keyboard/monitor

> **CRITICAL REQUIREMENT - Two Wi-Fi Interfaces**
>
> This project **requires two separate Wi-Fi interfaces** to function properly:
> - **wlan0**: Used for uplink connection (connects to your existing Wi-Fi network)
> - **wlan1**: Used for the Access Point (creates a new Wi-Fi network for your devices)
>
> You must have either:
> - Built-in Wi-Fi + USB Wi-Fi adapter, OR
> - Two USB Wi-Fi adapters
>
> **The web UI will display a prominent red warning banner when wlan1 is not available or the hostapd service is not running.** If you see this warning, check that:
> 1. You have a second Wi-Fi adapter connected and recognized by the system
> 2. The hostapd service is running: `sudo systemctl status hostapd`
> 3. The wlan1 interface exists: `ip link show wlan1`

### Required System Packages

The installer will automatically install all necessary packages. Here's the complete list for reference:

| Package | Purpose |
|---------|---------|
| `hostapd` | Access Point daemon - creates the Wi-Fi AP on wlan1 |
| `dnsmasq` | DHCP and DNS server - assigns IPs to connected devices |
| `nftables` | Firewall/NAT - routes traffic from wlan1 to wlan0 |
| `wpasupplicant` | Wi-Fi client - connects wlan0 to existing networks |
| `python3` | Backend runtime - runs the FastAPI web application |
| `python3-pip` | Python package manager |
| `python3-venv` | Virtual environment support |
| `python3-dev` | Python development headers |
| `gcc` | C compiler - for building Python packages |
| `iw` | Wireless configuration tool |
| `wireless-tools` | Additional wireless tools (iwconfig, etc.) |
| `net-tools` | Network utilities (netstat, etc.) |
| `network-manager` | Network management (optional, for troubleshooting) |
| `udev` | Device management - for auto-detecting wlan1 |
| `git` | Version control - for cloning and updating |
| `curl` | HTTP client - for downloading files |

**Note:** All packages are automatically installed by the installation script. You don't need to install them manually.

### Installation

#### Step 1: Prepare Your Pi

Update your system:

```bash
sudo apt update && sudo apt upgrade -y
```

#### Step 2: Clone the Repository

```bash
cd ~
git clone https://github.com/jphermans/pidhcp.git
cd pi-router
```

#### Step 3: Run the Installer

The installer will:
- Install all dependencies (hostapd, dnsmasq, nftables, Python)
- Configure network interfaces
- Set up the database
- Install systemd services
- Create privilege escalation helpers

```bash
sudo ./scripts/install.sh
```

#### Step 4: Build the Frontend

```bash
cd frontend
npm install
npm run build
cd ..
sudo cp -r frontend/dist/* /opt/pi-router/frontend/dist/
```

#### Step 5: Start the Service

```bash
sudo systemctl start pi-router
sudo systemctl status pi-router
```

#### Step 6: Access the Web UI

Open your browser and navigate to:

```
http://<your-pi-ip>:8080
```

Default credentials:
- **Username**: `admin`
- **Password**: `admin123`

> **Important**: Change the default password after your first login!

### Initial Configuration

1. **Set up your uplink (wlan0)**
   - Go to **Network** tab
   - Enter your existing Wi-Fi SSID and password
   - Click "Apply Uplink Settings"
   - Wait for connection

2. **Configure your Access Point (wlan1)**
   - Go to **Network** tab
   - Set your AP SSID and password
   - Choose a channel (1, 6, or 11 are typically best)
   - Click "Apply AP Settings"

3. **Enable NAT and IP Forwarding**
   - Go to **Settings** tab
   - Click "Enable NAT & IP Forwarding"

4. **Connect your devices**
   - Devices should now be able to connect to your new AP
   - They will receive IPs via DHCP (10.42.0.50 - 10.42.0.200)
   - Internet access should work through the uplink

## Docker Installation

### Prerequisites

- Docker and Docker Compose installed on your Pi

### Quick Start

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

Access the web UI at `http://<your-pi-ip>:8080`

## Configuration Files

### Network Configuration

Located at `/etc/pi-router/network.yaml`:

```yaml
uplink:
  ssid: "MyWiFi"
  password: "wifipassword"
  country: "US"

ap:
  ssid: "PiRouter-AP"
  password: "SecurePass123"
  channel: 6
  country: "US"
  hw_mode: "g"

dhcp:
  subnet: "10.42.0.0"
  netmask: "255.255.255.0"
  gateway: "10.42.0.1"
  range_start: "10.42.0.50"
  range_end: "10.42.0.200"
  lease_time: "12h"
```

### Application Configuration

Located at `/etc/pi-router/app.yaml`:

```yaml
secret_key: "CHANGE_THIS_SECRET_KEY"
admin_username: "admin"
admin_password: "admin123"
log_level: "INFO"
host: "0.0.0.0"
port: 8080
```

## Troubleshooting

### wlan1 Connecting to Home Network Instead of Being an AP

**Symptom:** wlan1 connects to your existing Wi-Fi network instead of creating its own Access Point.

**Cause:** This happens when wpa_supplicant or NetworkManager is managing wlan1 as a client interface instead of letting hostapd manage it as an Access Point.

**Quick Fix:**

```bash
sudo ./scripts/fix-wlan1.sh
```

This script will:
- Disable wpa_supplicant@wlan1 service
- Configure NetworkManager to ignore wlan1
- Ensure hostapd is running
- Restart services to restore AP mode

**Via Web UI:**
1. Go to Settings tab
2. Click "Check Interface Conflicts" to see issues
3. Click "Fix wlan1 AP Mode" to automatically correct problems

**Manual Fix:**
```bash
# Disable wpa_supplicant on wlan1
sudo systemctl stop wpa_supplicant@wlan1
sudo systemctl disable wpa_supplicant@wlan1

# Restart hostapd
sudo systemctl restart hostapd

# Verify it's in Master mode
sudo iwconfig wlan1
# Should show: Mode:Master
```

### Installation Without wlan1 (Auto-Activation Feature)

**New Feature:** The installer now works even if wlan1 is not connected during installation.

**What happens:**
1. Installation completes successfully
2. System installs udev rules and systemd services
3. When you plug in wlan1 USB WiFi adapter, the AP automatically starts

**How it works:**
- Udev rule detects when wlan1 is added
- Automatically runs initialization script
- Disables wpa_supplicant on wlan1
- Configures static IP (10.42.0.1)
- Starts hostapd and dnsmasq

**To manually trigger:**
```bash
sudo /usr/local/sbin/pi-router-init-wlan1
```

**Check auto-activation service:**
```bash
sudo systemctl status pi-router-wait-wlan1
```

### Missing Required Packages

If you get errors about missing commands or services, some packages might not be installed.

**Check if packages are installed:**
```bash
# Check key packages
dpkg -l | grep -E "hostapd|dnsmasq|nftables|wpasupplicant|python3"

# Check if commands are available
which hostapd dnsmasq nft iw iwconfig nmcli
```

**Install missing packages manually:**
```bash
sudo apt update
sudo apt install -y hostapd dnsmasq nftables wpasupplicant \
    python3 python3-pip python3-venv python3-dev gcc \
    iw wireless-tools net-tools network-manager udev
```

**Re-run the installer if needed:**
```bash
cd ~/pidhcp
sudo ./scripts/install.sh
```

### Critical Warning Banner in Web UI (wlan1 Not Available)

If you see a **red warning banner** at the top of the Dashboard saying "CRITICAL: wlan1 Access Point Not Running", this means the system cannot detect or use the wlan1 interface. The Access Point functionality will not work.

**Common causes and solutions:**

1. **Missing second Wi-Fi adapter**
   ```bash
   # Check available wireless interfaces
   iwconfig
   # or
   ip link show | grep wlan
   ```
   - You should see both `wlan0` and `wlan1`
   - If you only see `wlan0`, you need to add a second Wi-Fi adapter

2. **hostapd service not running**
   ```bash
   sudo systemctl status hostapd
   sudo systemctl start hostapd
   sudo systemctl enable hostapd
   ```

3. **Interface name mismatch**
   - Some systems may use different interface names (e.g., `wlx...`)
   - Check your actual interface names with `ip link show`
   - You may need to configure udev rules to rename interfaces consistently

4. **Wi-Fi adapter not supported by hostapd**
   - Some USB Wi-Fi adapters don't support AP mode
   - Check adapter compatibility with `hostapd`
   - Look for adapters with AR9271, RT5370, or similar chipsets

### AP Not Starting

Check hostapd status:

```bash
sudo systemctl status hostapd
sudo journalctl -u hostapd -n 50
```

Common issues:
- Channel not supported by your Wi-Fi adapter
- Country code mismatch
- Another process using wlan1

### DHCP Not Working

Check dnsmasq:

```bash
sudo systemctl status dnsmasq
sudo journalctl -u dnsmasq -n 50
```

Verify config:

```bash
sudo dnsmasq --test
```

### Uplink (wlan0) Not Connecting

Check wpa_supplicant:

```bash
sudo systemctl status wpa_supplicant@wlan0
sudo wpa_cli -i wlan0 status
```

Manually test connection:

```bash
wpa_supplicant -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant-wlan0.conf
```

### NAT Not Working

Check IP forwarding:

```bash
sysctl net.ipv4.ip_forward
# Should show: net.ipv4.ip_forward = 1
```

Check nftables:

```bash
sudo nft list ruleset
```

Re-enable if needed:

```bash
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward
```

### Web UI Not Accessible

Check service status:

```bash
sudo systemctl status pi-router
sudo journalctl -u pi-router -n 50
```

Verify it's listening:

```bash
sudo ss -tlnp | grep 8080
```

### Recovery: Factory Reset

If things go wrong, reset to defaults:

```bash
# Via web UI: Settings -> Factory Reset
# Or via command line:
sudo rm /etc/pi-router/network.yaml
sudo rm /etc/pi-router/app.yaml
sudo systemctl restart pi-router
```

### Recovery: Restore from Backup

Configuration backups are created automatically:

```bash
# List backups
ls -la /etc/pi-router/*.backup

# Restore network config
sudo cp /etc/pi-router/network.yaml.backup /etc/pi-router/network.yaml

# Restart service
sudo systemctl restart pi-router
```

## Service Management

### Start/Stop/Restart

```bash
sudo systemctl start pi-router
sudo systemctl stop pi-router
sudo systemctl restart pi-router
```

### Enable at Boot

```bash
sudo systemctl enable pi-router
```

### View Logs

```bash
# All logs
sudo journalctl -u pi-router -f

# Last 100 lines
sudo journalctl -u pi-router -n 100
```

## Uninstallation

```bash
cd ~/pi-router
sudo ./scripts/uninstall.sh
```

This removes all installed components but preserves data in `/var/lib/pi-router`.

To completely remove everything:

```bash
sudo rm -rf /var/lib/pi-router
```

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Building for Production

```bash
# Frontend
cd frontend
npm run build

# Backend
cd ../backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8080
```

## Security Considerations

1. **Change default password** immediately after installation
2. **Use strong WPA2 passwords** for both uplink and AP
3. **Keep the system updated** with `sudo apt update && sudo apt upgrade`
4. **Consider using a firewall** to restrict access to the web UI
5. **Run updates during low-traffic periods** as network will restart

## Hardware Requirements

- Raspberry Pi 5 (recommended) or Pi 4
- Two Wi-Fi interfaces:
  - Built-in Wi-Fi + USB Wi-Fi adapter, OR
  - Two USB Wi-Fi adapters
- MicroSD card (16GB minimum, 32GB recommended)
- Power supply (27W USB-C for Pi 5 recommended)

## License

MIT License - JPHsystems 2026

## Support

For issues and feature requests, please visit:
https://github.com/jphermans/pidhcp/issues

---

**JPHsystems 2026**
