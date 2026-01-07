# Pi Router Docker Deployment Guide

Complete guide to deploying Pi Router as Docker containers on Raspberry Pi 5.

> **IMPORTANT**: Docker deployment requires special network configurations because containers need direct access to WiFi hardware (wlan0 and wlan1).

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Deployment Steps](#deployment-steps)
- [Managing Containers](#managing-containers)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## Architecture Overview

### Container Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Raspberry Pi 5                          │
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Frontend (Nginx)│         │  Backend (FastAPI)│         │
│  │  :80             │────────▶│  :8080           │         │
│  │  React Web UI    │         │  Python/uvicorn  │         │
│  └──────────────────┘         └────────┬─────────┘         │
│                                       │                      │
│                         ┌─────────────┴──────────┐          │
│                         │  Host Network Mode     │          │
│                         │  (network_mode: host)  │          │
│                         └─────────────┬──────────┘          │
│                                       │                      │
│  ┌──────────────┐         ┌───────────────┴───────┐         │
│  │    wlan0     │         │    wlan1              │         │
│  │  (Uplink)    │         │  (AP+DHCP)            │         │
│  │  /dev/wlan0  │         │  /dev/wlan1           │         │
│  └──────────────┘         └───────────────────────┘         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Host Network Mode**: Backend uses `network_mode: host` to directly access WiFi interfaces
2. **Privileged Mode**: Required for network operations and hardware access
3. **Device Passthrough**: Direct access to `/dev/wlan0` and `/dev/wlan1`
4. **Volume Mounts**: Configuration and database persisted outside containers
5. **Separate Containers**: Frontend and backend in separate containers for isolation

## Prerequisites

### Hardware

- Raspberry Pi 5 (recommended) or Pi 4
- Two WiFi interfaces:
  - **wlan0**: Built-in WiFi (uplink connection)
  - **wlan1**: USB WiFi adapter (Access Point)
- MicroSD card (16GB minimum, 32GB recommended)
- Power supply (27W USB-C for Pi 5 recommended)

### Software

- Raspberry Pi OS Bookworm (64-bit recommended)
- Docker Engine 24.0+
- Docker Compose v2.20+

### Check Your System

```bash
# Verify WiFi interfaces
iwconfig
# You should see wlan0 and wlan1

# Check Docker version
docker --version
docker compose version

# Check if Docker is running
sudo systemctl status docker
```

## Quick Start

### 1. Install Docker (if not installed)

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Re-login for group changes to take effect
# or run: newgrp docker
```

### 2. Clone Repository

```bash
cd ~
git clone https://github.com/jphermans/pidhcp.git
cd pidhcp
```

### 3. Configure Environment

```bash
# Copy environment file
cp .env.example .env

# Edit configuration (optional but recommended)
nano .env

# Minimum required changes:
# - SECRET_KEY (generate a random string)
# - ADMIN_PASSWORD (change from default)
```

Generate a secure secret key:
```bash
openssl rand -hex 32
```

### 4. Create Required Directories

```bash
# Create data and config directories
mkdir -p config data

# Set proper permissions
sudo chown -R $USER:$USER config data
chmod 755 config data
```

### 5. Deploy Containers

```bash
# Build and start containers
docker compose up -d

# Check container status
docker compose ps

# View logs
docker compose logs -f
```

### 6. Access Web UI

Open your browser:
```
http://YOUR_PI_IP:80
```

Default credentials:
- Username: `admin`
- Password: `admin123`

**IMPORTANT**: Change password immediately after first login!

## Configuration

### Environment Variables (.env)

```bash
# Timezone
TZ=America/New_York

# Application
SECRET_KEY=your-secure-random-key-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password
LOG_LEVEL=INFO

# WiFi Interfaces
WLAN0_INTERFACE=wlan0  # Built-in WiFi (uplink)
WLAN1_INTERFACE=wlan1  # USB WiFi (AP)

# Access Point Settings
AP_SSID=MyRouter-AP
AP_PASSWORD=YourSecurePassword
AP_CHANNEL=6
AP_COUNTRY=US
```

### Volumes

| Volume | Purpose | Host Path |
|--------|---------|-----------|
| `./config` | Configuration files | `/config` in container |
| `./data` | Database and state | `/data` in container |
| `/etc/wpa_supplicant` | WPA config (read-only) | Monitor host WiFi |

## Deployment Steps

### Initial Deployment

```bash
# 1. Clone repository
git clone https://github.com/jphermans/pidhcp.git
cd pidhcp

# 2. Configure
cp .env.example .env
nano .env

# 3. Create directories
mkdir -p config data

# 4. Build and start
docker compose up -d --build

# 5. Check status
docker compose ps
docker compose logs
```

### Verify Deployment

```bash
# Check backend is running
curl http://localhost:8080/health

# Check frontend
curl http://localhost/health

# View container logs
docker compose logs backend
docker compose logs frontend

# Check network interfaces
docker compose exec backend iwconfig
```

### Configure WiFi

1. **Access Web UI**: http://YOUR_PI_IP:80
2. **Configure Uplink (wlan0)**:
   - Go to Network tab
   - Enter your WiFi SSID and password
   - Click "Apply Uplink Settings"
3. **Configure AP (wlan1)**:
   - Set your AP SSID and password
   - Choose channel (1, 6, or 11 recommended)
   - Click "Apply AP Settings"
4. **Enable NAT**:
   - Go to Settings tab
   - Click "Enable NAT & IP Forwarding"

## Managing Containers

### Start/Stop/Restart

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart specific service
docker compose restart backend
docker compose restart frontend

# View logs
docker compose logs -f backend
docker compose logs -f frontend
```

### Update Containers

```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose down
docker compose up -d --build

# Or use single command
docker compose up -d --build --force-recreate
```

### Backup Configuration

```bash
# Backup config and data
tar -czf pid-router-backup-$(date +%Y%m%d).tar.gz config/ data/

# Restore
tar -xzf pid-router-backup-YYYYMMDD.tar.gz
```

### Container Shell Access

```bash
# Access backend container
docker compose exec backend bash

# Access frontend container
docker compose exec frontend sh
```

## Troubleshooting

### Containers Won't Start

```bash
# Check Docker is running
sudo systemctl status docker

# Check container logs
docker compose logs

# Verify network interfaces exist
docker compose exec backend ls -la /dev/wlan*

# Check permissions
ls -la config/ data/
```

### WiFi Not Working

```bash
# Check interfaces in container
docker compose exec backend iwconfig

# Verify device passthrough
docker compose exec backend ls -la /dev/wlan0 /dev/wlan1

# Check hostapd status
docker compose exec backend systemctl status hostapd

# Check wpa_supplicant
docker compose exec backend wpa_cli -i wlan0 status
```

### Cannot Access Web UI

```bash
# Check if frontend is running
docker compose ps

# Check nginx config
docker compose exec frontend nginx -t

# Test backend API directly
curl http://localhost:8080/health

# View frontend logs
docker compose logs frontend
```

### Permission Errors

```bash
# Fix data directory permissions
sudo chown -R $USER:$USER config data
chmod -R 755 config data

# Or run with correct user
docker compose down
sudo chown -R 1000:1000 config data
docker compose up -d
```

### Port Already in Use

```bash
# Check what's using port 80
sudo ss -tlnp | grep :80

# Change frontend port in docker-compose.yml:
# ports:
#   - "8080:80"  # Use port 8080 instead of 80
```

## Security Considerations

### 1. Change Default Credentials

```bash
# Edit .env file
nano .env

# Change these values:
ADMIN_USERNAME=your-username
ADMIN_PASSWORD=strong-password-here
SECRET_KEY=$(openssl rand -hex 32)
```

### 2. Network Security

- Backend runs in host network mode (required for WiFi access)
- Consider using firewall rules to restrict access
- Only expose necessary ports

### 3. WiFi Security

- Use WPA2-AES for both uplink and AP
- Use strong passwords (minimum 12 characters)
- Change default AP SSID and password

### 4. Container Security

- Containers run with privileged mode (required for WiFi)
- Keep Docker images updated
- Scan for vulnerabilities: `docker scan`

### 5. Data Security

- Configuration stored in `./config` directory
- Database stored in `./data` directory
- Regular backups recommended

## Advanced Configuration

### Custom Networks

If default network mode causes issues, you can use macvlan:

```yaml
# In docker-compose.yml
backend:
  network_mode: service:network-delegator
  # ... rest of config

network-delegator:
  image: alpine
  cap_add:
    - NET_ADMIN
  devices:
    - /dev/wlan0
    - /dev/wlan1
  network_mode: host
```

### Resource Limits

Add to `docker-compose.yml`:

```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 512M
      reservations:
        cpus: '1'
        memory: 256M
```

### Auto-Start on Boot

```bash
# Enable Docker service
sudo systemctl enable docker

# Enable containers
docker compose up -d
# Containers with "restart: unless-stopped" will auto-start
```

## Monitoring

### Health Checks

```bash
# Container health
docker compose ps

# Backend health endpoint
curl http://localhost:8080/health

# Frontend health
curl http://localhost/health
```

### Logs

```bash
# Follow all logs
docker compose logs -f

# Specific service
docker compose logs -f backend

# Last 100 lines
docker compose logs --tail=100
```

### Statistics

```bash
# Container stats
docker stats

# Disk usage
docker system df

# Volume usage
du -sh config/ data/
```

## Performance Tips

1. **Use 64-bit OS** for better performance
2. **Use SSD** for data directory if possible
3. **Limit log size** in docker-compose.yml
4. **Regular cleanup**: `docker system prune -a`
5. **Monitor resources**: `docker stats`

## Uninstallation

```bash
# Stop and remove containers
docker compose down

# Remove volumes
docker compose down -v

# Remove images
docker rmi pid-router-backend pid-router-frontend

# Remove data (optional)
rm -rf config/ data/
```

## Support

For issues and feature requests:
- GitHub: https://github.com/jphermans/pidhcp/issues
- Documentation: https://github.com/jphermans/pidhcp

## License

MIT License - JPHsystems 2026
