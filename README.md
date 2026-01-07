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

### Installation

#### Step 1: Prepare Your Pi

Update your system:

```bash
sudo apt update && sudo apt upgrade -y
```

#### Step 2: Clone the Repository

```bash
cd ~
git clone https://github.com/yourusername/pi-router.git
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
https://github.com/yourusername/pi-router/issues

---

**JPHsystems 2026**
