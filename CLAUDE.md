# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pi Router is a full-featured Wi-Fi router system for Raspberry Pi 5. It turns a Pi into a router with dual Wi-Fi operation (uplink + access point), DHCP/DNS services, NAT/routing, and a modern React-based web UI for management.

### Architecture

The system has three main components:

1. **Backend** (`backend/`) - FastAPI application providing REST API and serving static frontend
   - `main.py` - Application entry point with lifespan-managed service initialization
   - `config/manager.py` - YAML configuration management with auto-backup and factory reset
   - `services/network_service.py` - Network operations (Wi-Fi, AP, DHCP, NAT) via subprocess calls
   - `services/auth_service.py` - JWT-based authentication with encrypted password storage
   - `services/system_service.py` - System status monitoring (CPU, memory, disk)
   - `services/portal_service.py` - Captive portal functionality for client authentication
   - `api/routes/` - API endpoints organized by domain (auth, status, config, services, portal)
   - `database/db.py` - SQLite database for settings, logs, and client sessions

2. **Frontend** (`frontend/`) - React SPA with Vite build system
   - `src/pages/` - Main pages (Dashboard, Network, Settings, Login)
   - `src/components/` - Reusable UI components
   - React Router for navigation, fetch API for backend communication

3. **Infrastructure** (`scripts/`) - System integration scripts
   - Privilege escalation helpers (`pi-router-update-*`, `pi-router-install-*`, `pi-router-save-*`)
   - These scripts are installed to `/usr/local/sbin/` during setup and called by NetworkService

### Network Configuration

The system manages two Wi-Fi interfaces:
- **wlan0** - Uplink (client mode) connects to existing Wi-Fi via wpa_supplicant
- **wlan1** - Access Point with hostapd, assigns IPs via dnsmasq (10.42.0.50-200)

NAT/routing is handled by nftables with masquerade on wlan0. IP forwarding is persisted via sysctl.

Configuration files:
- `/etc/pi-router/network.yaml` - Network settings (SSID, passwords, DHCP range)
- `/etc/pi-router/app.yaml` - Application settings (secret key, admin credentials, port)
- Runtime configs: `/etc/wpa_supplicant/wpa_supplicant-wlan0.conf`, `/etc/hostapd/hostapd.conf`, `/etc/dnsmasq.d/pi-router.conf`

## Common Commands

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
npm run dev      # Development server (Vite)
npm run build    # Production build to dist/
npm run lint     # ESLint check
```

### Production Build

```bash
# Frontend
cd frontend
npm run build

# Backend
cd ../backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8080
```

### Docker Deployment

```bash
docker-compose up -d    # Build and start
docker-compose logs -f  # View logs
docker-compose down     # Stop
```

### System Integration (on Raspberry Pi)

```bash
sudo ./scripts/install.sh           # Full installation
sudo systemctl start pi-router       # Start service
sudo systemctl status pi-router      # Check status
sudo journalctl -u pi-router -n 50   # View logs
```

## Key Implementation Details

### Service Initialization Pattern

The application uses FastAPI's lifespan context manager to initialize services globally. All services (ConfigManager, AuthService, NetworkService, SystemService) are instantiated once at startup and stored in module-level globals, then accessed by route handlers. This avoids per-request initialization overhead.

### Privilege Escalation

NetworkService writes configuration to temporary files in `/tmp/`, then uses sudo to call privilege escalation scripts in `/usr/local/sbin/` that move files to protected system locations and restart services. This pattern allows the FastAPI app to run as a non-root user while still managing system services.

### Configuration Management

ConfigManager loads YAML configs into Pydantic models (`backend/config/models.py`). When saving configs, it first creates backups before overwriting. The factory reset feature archives existing configs as `.factory_backup` before generating new defaults.

### Network Operations

NetworkService wraps all system commands (iwconfig, ip, systemctl, nft, etc.) in an async `run_command()` method with timeout handling. It parses command output with regex to extract structured data (SSIDs, IP addresses, signal strength, DHCP leases).

### Frontend Architecture

The frontend is a simple React application without a complex state management library. Components use fetch() to call the REST API and store state in useState hooks. Authentication tokens are stored in localStorage and sent via Authorization header.

## Development Notes

- Python 3.12+ required
- Node.js 20+ required for frontend
- systemd services must be managed via sudo (hostapd, dnsmasq, wpa_supplicant)
- Configuration changes to system services require restarting those services via NetworkService methods
- Frontend build output must be copied to production location after building: `sudo cp -r frontend/dist/* /opt/pi-router/frontend/dist/`
