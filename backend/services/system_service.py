"""System service for system-level operations."""

import subprocess
import logging
import asyncio
from typing import Dict, List, Tuple
import psutil

logger = logging.getLogger(__name__)


class SystemService:
    """Service for system operations."""

    async def run_command(self, cmd: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
        """Run a command asynchronously."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            return (process.returncode == 0, stdout.decode('utf-8', errors='replace'), stderr.decode('utf-8', errors='replace'))
        except asyncio.TimeoutError:
            return (False, "", "Command timed out")
        except Exception as e:
            return (False, "", str(e))

    async def get_system_info(self) -> Dict:
        """Get system information."""
        # CPU temperature (Raspberry Pi specific)
        temp = 0
        try:
            success, stdout, _ = await self.run_command(["vcgencmd", "measure_temp"])
            if success:
                import re
                match = re.search(r'([\d.]+)', stdout)
                if match:
                    temp = float(match.group(1))
        except Exception:
            pass

        # Memory usage
        mem = psutil.virtual_memory()

        # Disk usage
        disk = psutil.disk_usage('/')

        # CPU usage
        cpu = psutil.cpu_percent(interval=1)

        # Uptime
        uptime = 0
        try:
            success, stdout, _ = await self.run_command(["cat", "/proc/uptime"])
            if success:
                uptime_seconds = float(stdout.split()[0])
                uptime = int(uptime_seconds)
        except Exception:
            pass

        return {
            "cpu_percent": cpu,
            "cpu_temp": temp,
            "memory": {
                "total": mem.total,
                "available": mem.available,
                "percent": mem.percent,
                "used": mem.used
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "uptime": uptime
        }

    async def get_service_status(self, service: str) -> Dict:
        """Get the status of a systemd service."""
        status = {
            "name": service,
            "active": False,
            "enabled": False,
            "state": "unknown"
        }

        # Check if active
        success, stdout, _ = await self.run_command(["systemctl", "is-active", service])
        status["active"] = success
        if success:
            status["state"] = stdout.strip()

        # Check if enabled
        success, stdout, _ = await self.run_command(["systemctl", "is-enabled", service])
        status["enabled"] = success

        return status

    async def get_service_logs(self, service: str, lines: int = 50) -> List[str]:
        """Get recent logs for a service."""
        success, stdout, _ = await self.run_command([
            "journalctl", "-u", service, "-n", str(lines), "--no-pager"
        ])

        if success:
            return stdout.strip().split('\n')
        return []

    async def reboot_system(self) -> Tuple[bool, str]:
        """Reboot the system."""
        success, _, err = await self.run_command([
            "sudo", "reboot"
        ])
        if success:
            return True, "System rebooting"
        else:
            return False, f"Failed to reboot: {err}"
