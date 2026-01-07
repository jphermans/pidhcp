"""Network service for managing Wi-Fi, AP, DHCP, and routing."""

import subprocess
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re
import aiofiles

logger = logging.getLogger(__name__)


class NetworkService:
    """Service for network operations."""

    # Configuration file paths
    WPA_SUPPLICANT_CONF = "/etc/wpa_supplicant/wpa_supplicant-wlan0.conf"
    HOSTAPD_CONF = "/etc/hostapd/hostapd.conf"
    DNSMASQ_CONF = "/etc/dnsmasq.d/pi-router.conf"
    NF_TABLES_CONF = "/etc/nftables.d/pi-router.nft"
    SYSCTL_CONF = "/etc/sysctl.d/99-pi-router-forwarding.conf"

    def __init__(self, config_dir: str = "/etc/pi-router"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    async def run_command(self, cmd: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
        """Run a command asynchronously and return (success, stdout, stderr)."""
        try:
            logger.debug(f"Running command: {' '.join(cmd)}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')
            success = process.returncode == 0

            if not success:
                logger.warning(f"Command failed: {' '.join(cmd)} - {stderr_str}")

            return (success, stdout_str, stderr_str)
        except asyncio.TimeoutError:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            return (False, "", "Command timed out")
        except Exception as e:
            logger.error(f"Command exception: {e}")
            return (False, "", str(e))

    async def get_wlan0_status(self) -> Dict:
        """Get the status of wlan0 (uplink)."""
        status = {
            "connected": False,
            "ssid": None,
            "ip_address": None,
            "gateway": None,
            "signal_strength": None,
            "interface": "wlan0"
        }

        # Get connection status and SSID using iwconfig
        success, stdout, _ = await self.run_command(["iwconfig", "wlan0"])
        if success:
            # Parse SSID
            match = re.search(r'ESSID:"([^"]+)"', stdout)
            if match:
                status["ssid"] = match.group(1)
                status["connected"] = bool(status["ssid"])

            # Parse signal quality
            match = re.search(r'Link Quality=(\d+)/(\d+)', stdout)
            if match:
                quality = int(match.group(1))
                total = int(match.group(2))
                status["signal_strength"] = f"{int(quality / total * 100)}%"

        # Get IP address
        success, stdout, _ = await self.run_command(["ip", "-o", "-4", "addr", "show", "wlan0"])
        if success:
            match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', stdout)
            if match:
                status["ip_address"] = match.group(1)

        # Get gateway
        success, stdout, _ = await self.run_command(["ip", "route", "show", "default"])
        if success:
            match = re.search(r'default.*via\s+(\d+\.\d+\.\d+\.\d+).*dev\s+wlan0', stdout)
            if match:
                status["gateway"] = match.group(1)

        return status

    async def get_wlan1_status(self) -> Dict:
        """Get the status of wlan1 (AP)."""
        status = {
            "running": False,
            "ssid": None,
            "ip_address": None,
            "channel": None,
            "interface": "wlan1",
            "clients": 0
        }

        # Check if hostapd is running
        success, stdout, _ = await self.run_command(["systemctl", "is-active", "hostapd"])
        status["running"] = success

        # Get AP SSID from hostapd config
        if Path(self.HOSTAPD_CONF).exists():
            async with aiofiles.open(self.HOSTAPD_CONF, 'r') as f:
                content = await f.read()
                match = re.search(r'^ssid=(.+)$', content, re.MULTILINE)
                if match:
                    status["ssid"] = match.group(1).strip()
                match = re.search(r'^channel=(\d+)', content, re.MULTILINE)
                if match:
                    status["channel"] = int(match.group(1))

        # Get IP address
        success, stdout, _ = await self.run_command(["ip", "-o", "-4", "addr", "show", "wlan1"])
        if success:
            match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', stdout)
            if match:
                status["ip_address"] = match.group(1)

        # Count DHCP leases
        status["clients"] = await self._get_dhcp_client_count()

        return status

    async def _get_dhcp_client_count(self) -> int:
        """Get the number of DHCP clients."""
        success, stdout, _ = await self.run_command(["dnsmasq", "--dhcp leases"])
        if success:
            return len([line for line in stdout.strip().split('\n') if line.strip()])
        return 0

    async def get_dhcp_leases(self) -> List[Dict]:
        """Get list of DHCP leases."""
        leases = []

        success, stdout, _ = await self.run_command(["dnsmasq", "--dhcp-leasefile=/var/lib/misc/dnsmasq.leases", "--dhcp-leases"])
        if not success:
            # Try reading lease file directly
            try:
                async with aiofiles.open("/var/lib/misc/dnsmasq.leases", 'r') as f:
                    content = await f.read()
                    stdout = content
            except Exception:
                return []

        for line in stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 5:
                leases.append({
                    "mac": parts[1],
                    "ip": parts[2],
                    "hostname": parts[3] if parts[3] != "*" else "Unknown",
                    "expires": parts[0]
                })

        return leases

    def generate_hostapd_config(self, ap_config: dict) -> str:
        """Generate hostapd configuration content."""
        return f"""# Pi Router AP Configuration
interface=wlan1
driver=nl80211
ssid={ap_config['ssid']}
hw_mode={ap_config['hw_mode']}
channel={ap_config['channel']}
country_code={ap_config['country']}
auth_algs=1
wpa=2
wpa_passphrase={ap_config['password']}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP
rsn_pairwise=CCMP
"""

    def generate_dnsmasq_config(self, dhcp_config: dict, ap_config: dict) -> str:
        """Generate dnsmasq configuration content."""
        return f"""# Pi Router DHCP and DNS Configuration
# Listen on wlan1 only
interface=wlan1
bind-interfaces
except-interface=lo

# DHCP range
dhcp-range={dhcp_config['range_start']},{dhcp_config['range_end']},{dhcp_config['netmask']},{dhcp_config['lease_time']}

# DHCP options
dhcp-option=3,{dhcp_config['gateway']}
dhcp-option=6,8.8.8.8,8.8.4.4

# Log DHCP activity
log-queries
log-dhcp

# Cache DNS entries
cache-size=150

# Don't read /etc/resolv.conf
no-resolv

# Upstream DNS servers
server=1.1.1.1
server=1.0.0.1
"""

    def generate_nftables_config(self) -> str:
        """Generate nftables NAT configuration."""
        return """# Pi Router NAT Configuration
table nat {
    chain postrouting {
        type nat hook postrouting priority srcnat { policy accept; }
        oifname "wlan0" masquerade
    }
}

table inet filter {
    chain forward {
        type filter hook forward priority filter { policy accept; }
        # Allow forwarding from wlan1 to wlan0
        iifname "wlan1" oifname "wlan0" accept
        # Allow established/related connections back
        ct state established,related accept
    }
}
"""

    def generate_wpa_supplicant_config(self, uplink_config: dict) -> str:
        """Generate wpa_supplicant configuration for wlan0."""
        country = uplink_config.get('country', 'US')
        return f"""country={country}
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid="{uplink_config['ssid']}"
    psk="{uplink_config['password']}"
    key_mgmt=WPA-PSK
}}
"""

    async def update_uplink(self, ssid: str, password: str, country: str = "US") -> Tuple[bool, str]:
        """Update wlan0 uplink configuration and reconnect."""
        try:
            # Generate new config
            config_content = self.generate_wpa_supplicant_config({
                'ssid': ssid,
                'password': password,
                'country': country
            })

            # Write to temp file first, then move (atomic)
            temp_file = Path("/tmp/wpa_supplicant-wlan0.conf.new")
            async with aiofiles.open(temp_file, 'w') as f:
                await f.write(config_content)

            # Set proper permissions
            await self.run_command(["chmod", "600", str(temp_file)])
            await self.run_command(["chown", "root:root", str(temp_file)])

            # Move to actual location (requires privilege escalation)
            success, _, err = await self.run_command([
                "sudo", "/usr/local/sbin/pi-router-update-uplink",
                str(temp_file)
            ])

            if not success:
                return False, f"Failed to update config: {err}"

            # Restart wpa_supplicant on wlan0
            success, _, err = await self.run_command([
                "sudo", "systemctl", "restart", "wpa_supplicant@wlan0"
            ])

            if not success:
                return False, f"Failed to restart wpa_supplicant: {err}"

            # Wait a bit for connection
            await asyncio.sleep(5)

            # Check if connected
            status = await self.get_wlan0_status()
            if status["connected"]:
                return True, "Successfully connected to uplink network"
            else:
                return False, "Configuration updated but not yet connected (check SSID/password)"

        except Exception as e:
            logger.error(f"Failed to update uplink: {e}")
            return False, str(e)

    async def update_ap_config(self, ap_config: dict) -> Tuple[bool, str]:
        """Update AP configuration and restart hostapd."""
        try:
            config_content = self.generate_hostapd_config(ap_config)

            # Write to temp file
            temp_file = Path("/tmp/hostapd.conf.new")
            async with aiofiles.open(temp_file, 'w') as f:
                await f.write(config_content)

            # Move to actual location
            success, _, err = await self.run_command([
                "sudo", "/usr/local/sbin/pi-router-update-ap",
                str(temp_file)
            ])

            if not success:
                return False, f"Failed to update AP config: {err}"

            # Restart hostapd
            success, _, err = await self.run_command([
                "sudo", "systemctl", "restart", "hostapd"
            ])

            if success:
                return True, "AP configuration updated successfully"
            else:
                return False, f"Failed to restart hostapd: {err}"

        except Exception as e:
            logger.error(f"Failed to update AP config: {e}")
            return False, str(e)

    async def update_dhcp_config(self, dhcp_config: dict, ap_config: dict) -> Tuple[bool, str]:
        """Update DHCP configuration and restart dnsmasq."""
        try:
            config_content = self.generate_dnsmasq_config(dhcp_config, ap_config)

            # Write to temp file
            temp_file = Path("/tmp/dnsmasq.conf.new")
            async with aiofiles.open(temp_file, 'w') as f:
                await f.write(config_content)

            # Move to actual location
            success, _, err = await self.run_command([
                "sudo", "/usr/local/sbin/pi-router-update-dhcp",
                str(temp_file)
            ])

            if not success:
                return False, f"Failed to update DHCP config: {err}"

            # Restart dnsmasq
            success, _, err = await self.run_command([
                "sudo", "systemctl", "restart", "dnsmasq"
            ])

            if success:
                return True, "DHCP configuration updated successfully"
            else:
                return False, f"Failed to restart dnsmasq: {err}"

        except Exception as e:
            logger.error(f"Failed to update DHCP config: {e}")
            return False, str(e)

    async def restart_service(self, service: str) -> Tuple[bool, str]:
        """Restart a system service."""
        valid_services = ["hostapd", "dnsmasq", "wpa_supplicant@wlan0"]
        if service not in valid_services:
            return False, f"Invalid service: {service}"

        success, _, err = await self.run_command([
            "sudo", "systemctl", "restart", service
        ])

        if success:
            return True, f"Service {service} restarted successfully"
        else:
            return False, f"Failed to restart {service}: {err}"

    async def check_nat_enabled(self) -> bool:
        """Check if NAT/masquerade is enabled."""
        success, stdout, _ = await self.run_command([
            "nft", "list", "table", "nat"
        ])
        return success and "masquerade" in stdout

    async def enable_ip_forwarding(self) -> Tuple[bool, str]:
        """Enable IPv4 packet forwarding."""
        # Enable immediately
        success, _, err = await self.run_command([
            "sudo", "sysctl", "-w", "net.ipv4.ip_forward=1"
        ])

        if not success:
            return False, f"Failed to enable forwarding: {err}"

        # Persist in sysctl config
        sysctl_content = "net.ipv4.ip_forward=1\n"
        temp_file = Path("/tmp/sysctl-pi-router")
        async with aiofiles.open(temp_file, 'w') as f:
            await f.write(sysctl_content)

        success, _, err = await self.run_command([
            "sudo", "/usr/local/sbin/pi-router-install-sysctl",
            str(temp_file)
        ])

        if success:
            return True, "IPv4 forwarding enabled"
        else:
            return False, f"Failed to persist forwarding config: {err}"

    async def setup_nat(self) -> Tuple[bool, str]:
        """Setup nftables NAT rules."""
        config_content = self.generate_nftables_config()
        temp_file = Path("/tmp/nftables.conf.new")
        async with aiofiles.open(temp_file, 'w') as f:
            await f.write(config_content)

        # Load nftables rules
        success, _, err = await self.run_command([
            "sudo", "nft", "-f", str(temp_file)
        ])

        if not success:
            return False, f"Failed to load nftables rules: {err}"

        # Save for persistence
        success, _, err = await self.run_command([
            "sudo", "/usr/local/sbin/pi-router-save-nftables",
            str(temp_file)
        ])

        if success:
            return True, "NAT rules configured successfully"
        else:
            return False, f"Failed to save nftables config: {err}"

    async def ensure_wlan1_ap_mode(self) -> Tuple[bool, str]:
        """Ensure wlan1 is in AP mode and not managed by wpa_supplicant."""
        issues = []
        fixes = []

        # Check if wpa_supplicant is running on wlan1
        success, _, _ = await self.run_command([
            "systemctl", "is-active", "wpa_supplicant@wlan1"
        ])

        if success:
            issues.append("wpa_supplicant@wlan1 is running (should be disabled)")
            # Disable and stop wpa_supplicant on wlan1
            success, _, err = await self.run_command([
                "sudo", "systemctl", "disable", "wpa_supplicant@wlan1"
            ])
            if success:
                fixes.append("Disabled wpa_supplicant@wlan1")
            else:
                return False, f"Failed to disable wpa_supplicant@wlan1: {err}"

            success, _, err = await self.run_command([
                "sudo", "systemctl", "stop", "wpa_supplicant@wlan1"
            ])
            if success:
                fixes.append("Stopped wpa_supplicant@wlan1")
            else:
                return False, f"Failed to stop wpa_supplicant@wlan1: {err}"

        # Check if NetworkManager is managing wlan1
        success, stdout, _ = await self.run_command([
            "nmcli", "device", "show", "wlan1"
        ])

        if success:
            # Check if it's managed
            if "managed: true" in stdout.lower() or "managed" in stdout.lower():
                issues.append("NetworkManager is managing wlan1")
                # Create udev rule to unmanage wlan1
                udev_content = """# Prevent NetworkManager from managing wlan1
ACTION=="add", SUBSYSTEM=="net", DRIVERS=="?*", ATTR{address}=="*", KERNELS=="wlan1", ENV{NM_UNMANAGED}="1"
"""
                temp_file = Path("/tmp/90-nm-unmanage-wlan1.rules")
                async with aiofiles.open(temp_file, 'w') as f:
                    await f.write(udev_content)

                success, _, err = await self.run_command([
                    "sudo", "mv", str(temp_file), "/etc/udev/rules.d/90-nm-unmanage-wlan1.rules"
                ])
                if success:
                    fixes.append("Created udev rule to unmanage wlan1")
                else:
                    return False, f"Failed to create udev rule: {err}"

                # Reload udev rules
                await self.run_command(["sudo", "udevadm", "control", "--reload-rules"])
                fixes.append("Reloaded udev rules")

        # Check for wpa_supplicant.conf files that might include wlan1
        for conf_path in [
            "/etc/wpa_supplicant/wpa_supplicant.conf",
            "/etc/wpa_supplicant/wpa_supplicant-wlan1.conf"
        ]:
            if Path(conf_path).exists():
                # Check if wlan1 is mentioned
                try:
                    async with aiofiles.open(conf_path, 'r') as f:
                        content = await f.read()
                        if "wlan1" in content or "interface=wlan1" in content:
                            issues.append(f"wlan1 configured in {conf_path}")
                            fixes.append(f"Review {conf_path} - ensure wlan1 is not configured")
                except Exception:
                    pass

        # Ensure hostapd is enabled
        success, _, _ = await self.run_command([
            "systemctl", "is-enabled", "hostapd"
        ])

        if not success:
            issues.append("hostapd is not enabled")
            success, _, err = await self.run_command([
                "sudo", "systemctl", "enable", "hostapd"
            ])
            if success:
                fixes.append("Enabled hostapd service")
            else:
                return False, f"Failed to enable hostapd: {err}"

        # Restart hostapd to ensure it takes control of wlan1
        success, _, err = await self.run_command([
            "sudo", "systemctl", "restart", "hostapd"
        ])

        if success:
            fixes.append("Restarted hostapd")
        else:
            return False, f"Failed to restart hostapd: {err}"

        if issues:
            return True, f"Fixed {len(issues)} issue(s): {'; '.join(issues)}. Fixes: {'; '.join(fixes)}"
        else:
            return True, "wlan1 is correctly configured for AP mode"

    async def get_interface_conflicts(self) -> Dict:
        """Check for interface configuration conflicts."""
        conflicts = {
            "wlan1_as_client": False,
            "wpa_supplicant_on_wlan1": False,
            "networkmanager_managing_wlan1": False,
            "hostapd_running": False,
            "warnings": [],
            "recommendations": []
        }

        # Check if wpa_supplicant is running on wlan1
        success, _, _ = await self.run_command([
            "systemctl", "is-active", "wpa_supplicant@wlan1"
        ])
        conflicts["wpa_supplicant_on_wlan1"] = success
        if success:
            conflicts["warnings"].append("wpa_supplicant@wlan1 is running - this will prevent AP mode")
            conflicts["recommendations"].append("Disable: sudo systemctl disable --now wpa_supplicant@wlan1")

        # Check NetworkManager
        success, stdout, _ = await self.run_command([
            "nmcli", "device", "show", "wlan1"
        ], timeout=5)
        if success and ("managed: true" in stdout.lower() or "managed" in stdout.lower()):
            conflicts["networkmanager_managing_wlan1"] = True
            conflicts["warnings"].append("NetworkManager is managing wlan1")
            conflicts["recommendations"].append("Add udev rule to unmanage wlan1")

        # Check hostapd status
        success, _, _ = await self.run_command([
            "systemctl", "is-active", "hostapd"
        ])
        conflicts["hostapd_running"] = success
        if not success:
            conflicts["warnings"].append("hostapd is not running")
            conflicts["recommendations"].append("Enable: sudo systemctl enable --now hostapd")

        # Check if wlan1 is in client mode (has an IP from uplink)
        success, stdout, _ = await self.run_command(["iwconfig", "wlan1"])
        if success:
            # If it shows ESSID and not in master mode, it's likely in client mode
            if "ESSID:" in stdout and "Mode:Master" not in stdout:
                conflicts["wlan1_as_client"] = True
                conflicts["warnings"].append("wlan1 appears to be in client mode")
                conflicts["recommendations"].append("Run interface cleanup to restore AP mode")

        return conflicts
