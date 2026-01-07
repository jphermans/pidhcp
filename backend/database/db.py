"""SQLite database for persistent storage."""

import aiosqlite
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Database:
    """SQLite database for storing configuration and state."""

    def __init__(self, db_path: str = "/var/lib/pi-router/data/pi-router.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init(self):
        """Initialize database tables."""
        async with aiosqlite.connect(self.db_path) as db:
            # Configuration table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    hashed_password TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Devices table - track all connected devices
            await db.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    mac TEXT PRIMARY KEY,
                    ip TEXT,
                    hostname TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_online BOOLEAN DEFAULT 1
                )
            """)

            # Service logs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS service_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # System events table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    description TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.commit()
            logger.info("Database initialized")

    async def get_config(self, key: str, default: Any = None) -> Optional[Any]:
        """Get a configuration value."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT value FROM config WHERE key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    try:
                        return json.loads(row[0])
                    except json.JSONDecodeError:
                        return row[0]
                return default

    async def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        async with aiosqlite.connect(self.db_path) as db:
            value_json = json.dumps(value) if not isinstance(value, str) else value
            await db.execute("""
                INSERT OR REPLACE INTO config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value_json))
            await db.commit()
            logger.debug(f"Config saved: {key}")

    async def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration values."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT key, value FROM config") as cursor:
                rows = await cursor.fetchall()
                result = {}
                for row in rows:
                    try:
                        result[row[0]] = json.loads(row[1])
                    except json.JSONDecodeError:
                        result[row[0]] = row[1]
                return result

    async def delete_config(self, key: str) -> None:
        """Delete a configuration value."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM config WHERE key = ?", (key,))
            await db.commit()

    # User management
    async def get_user(self, username: str) -> Optional[Dict]:
        """Get user by username."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT username, hashed_password FROM users WHERE username = ?",
                (username,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "username": row[0],
                        "hashed_password": row[1]
                    }
                return None

    async def create_user(self, username: str, hashed_password: str) -> None:
        """Create a new user."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO users (username, hashed_password)
                VALUES (?, ?)
            """, (username, hashed_password))
            await db.commit()
            logger.info(f"User created: {username}")

    async def update_user_password(self, username: str, hashed_password: str) -> None:
        """Update user password."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users SET hashed_password = ?, updated_at = CURRENT_TIMESTAMP
                WHERE username = ?
            """, (hashed_password, username))
            await db.commit()
            logger.info(f"Password updated for user: {username}")

    async def get_all_users(self) -> List[Dict]:
        """Get all users."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT username, created_at FROM users") as cursor:
                rows = await cursor.fetchall()
                return [
                    {"username": row[0], "created_at": row[1]}
                    for row in rows
                ]

    # Device tracking - new and improved
    async def update_device(self, mac: str, ip: str = None, hostname: str = None) -> None:
        """Update or insert a device (called when device is seen/active)."""
        async with aiosqlite.connect(self.db_path) as db:
            # Check if device exists
            async with db.execute("SELECT mac FROM devices WHERE mac = ?", (mac,)) as cursor:
                exists = await cursor.fetchone()

            if exists:
                # Update existing device
                await db.execute("""
                    UPDATE devices
                    SET ip = ?, hostname = ?, last_seen = CURRENT_TIMESTAMP, is_online = 1
                    WHERE mac = ?
                """, (ip, hostname or "Unknown", mac))
            else:
                # Insert new device
                await db.execute("""
                    INSERT INTO devices (mac, ip, hostname, first_seen, last_seen, is_online)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                """, (mac, ip, hostname or "Unknown"))
            await db.commit()
            logger.debug(f"Device updated: {mac}")

    async def get_devices(self, offline_timeout_minutes: int = 30) -> List[Dict]:
        """Get all devices with online status, filtering out old offline devices."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get all devices with their status
            async with db.execute("""
                SELECT mac, ip, hostname, first_seen, last_seen, is_online
                FROM devices
                ORDER BY last_seen DESC
            """) as cursor:
                rows = await cursor.fetchall()

            devices = []
            cutoff_time = datetime.now() - timedelta(minutes=offline_timeout_minutes)

            for row in rows:
                mac, ip, hostname, first_seen, last_seen, is_online = row

                # Parse timestamps
                if isinstance(last_seen, str):
                    last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                else:
                    last_seen_dt = last_seen

                if isinstance(first_seen, str):
                    first_seen_dt = datetime.fromisoformat(first_seen.replace('Z', '+00:00'))
                else:
                    first_seen_dt = first_seen

                # Determine if device is online (seen in last 5 minutes)
                online_cutoff = datetime.now() - timedelta(minutes=5)
                is_online_now = last_seen_dt > online_cutoff

                # Skip if offline for too long
                if not is_online_now and last_seen_dt < cutoff_time:
                    continue

                # Calculate time ago string
                time_ago = self._time_ago(last_seen_dt)

                devices.append({
                    "mac": mac,
                    "ip": ip,
                    "hostname": hostname,
                    "first_seen": first_seen_dt.isoformat(),
                    "last_seen": last_seen_dt.isoformat(),
                    "is_online": is_online_now,
                    "time_ago": time_ago
                })

            return devices

    def _time_ago(self, dt: datetime) -> str:
        """Calculate human-readable time ago string."""
        delta = datetime.now() - dt
        seconds = delta.total_seconds()

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes}m ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours}h ago"
        else:
            days = int(seconds / 86400)
            return f"{days}d ago"

    async def mark_device_offline(self, mac: str) -> None:
        """Mark a device as offline."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE devices SET is_online = 0 WHERE mac = ?
            """, (mac,))
            await db.commit()

    async def mark_all_devices_offline(self) -> None:
        """Mark all devices as offline (called periodically, then active ones are marked online)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE devices SET is_online = 0")
            await db.commit()

    async def delete_old_devices(self, offline_days: int = 7) -> int:
        """Delete devices that have been offline for more than specified days."""
        async with aiosqlite.connect(self.db_path) as db:
            cutoff = datetime.now() - timedelta(days=offline_days)
            cursor = await db.execute("""
                DELETE FROM devices WHERE last_seen < ?
            """, (cutoff.isoformat(),))
            await db.commit()
            deleted = cursor.rowcount
            if deleted > 0:
                logger.info(f"Deleted {deleted} old devices")
            return deleted

    async def cleanup_old_offline_devices(self, offline_minutes: int = 30) -> int:
        """Remove devices that have been offline for more than specified minutes (soft delete tracking)."""
        # This returns count of devices that would be filtered from UI
        async with aiosqlite.connect(self.db_path) as db:
            cutoff = datetime.now() - timedelta(minutes=offline_minutes)
            async with db.execute("""
                SELECT COUNT(*) FROM devices WHERE last_seen < ? AND is_online = 0
            """, (cutoff.isoformat(),)) as cursor:
                count = (await cursor.fetchone())[0]
            return count

    # Logging
    async def add_service_log(self, service: str, level: str, message: str) -> None:
        """Add a service log entry."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO service_logs (service, level, message)
                VALUES (?, ?, ?)
            """, (service, level, message))
            await db.commit()

    async def get_service_logs(self, service: str = None, limit: int = 100) -> List[Dict]:
        """Get service log entries."""
        async with aiosqlite.connect(self.db_path) as db:
            if service:
                async with db.execute("""
                    SELECT service, level, message, created_at
                    FROM service_logs
                    WHERE service = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (service, limit)) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute("""
                    SELECT service, level, message, created_at
                    FROM service_logs
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,)) as cursor:
                    rows = await cursor.fetchall()

            return [
                {
                    "service": row[0],
                    "level": row[1],
                    "message": row[2],
                    "created_at": row[3]
                }
                for row in rows
            ]

    # System events
    async def add_system_event(self, event_type: str, description: str = None, metadata: Dict = None) -> None:
        """Add a system event."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO system_events (event_type, description, metadata)
                VALUES (?, ?, ?)
            """, (event_type, description, json.dumps(metadata) if metadata else None))
            await db.commit()
            logger.info(f"System event: {event_type} - {description}")

    async def get_system_events(self, event_type: str = None, limit: int = 100) -> List[Dict]:
        """Get system events."""
        async with aiosqlite.connect(self.db_path) as db:
            if event_type:
                async with db.execute("""
                    SELECT event_type, description, metadata, created_at
                    FROM system_events
                    WHERE event_type = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (event_type, limit)) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute("""
                    SELECT event_type, description, metadata, created_at
                    FROM system_events
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,)) as cursor:
                    rows = await cursor.fetchall()

            return [
                {
                    "event_type": row[0],
                    "description": row[1],
                    "metadata": json.loads(row[2]) if row[2] else None,
                    "created_at": row[3]
                }
                for row in rows
            ]
