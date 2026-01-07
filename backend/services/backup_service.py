"""Backup service for syncing settings with various providers and servers."""

import os
import json
import shutil
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
import sqlite3

logger = logging.getLogger(__name__)


class BackupService:
    """Service for creating and managing backups with multiple storage backends."""

    def __init__(self, data_dir: str = "/var/lib/pi-router/data"):
        self.data_dir = Path(data_dir)
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "pi-router.db"

    def create_backup(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a local backup of database and configuration."""
        if not name:
            name = datetime.now().strftime("backup_%Y%m%d_%H%M%S")

        backup_path = self.backup_dir / name
        backup_path.mkdir(parents=True, exist_ok=True)

        # Copy database
        if self.db_path.exists():
            shutil.copy2(self.db_path, backup_path / "pi-router.db")

        # Backup configuration from /etc/pi-router
        config_dir = backup_path / "config"
        config_dir.mkdir(exist_ok=True)

        etc_config = Path("/etc/pi-router")
        if etc_config.exists():
            for file in etc_config.iterdir():
                if file.is_file():
                    shutil.copy2(file, config_dir / file.name)

        # Create metadata
        metadata = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
            "type": "local"
        }

        with open(backup_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Backup created: {backup_path}")

        return {
            "success": True,
            "name": name,
            "path": str(backup_path),
            "size_mb": self._get_dir_size(backup_path) / (1024 * 1024),
            "created_at": metadata["created_at"]
        }

    def restore_backup(self, name: str) -> Dict[str, Any]:
        """Restore a backup from local storage."""
        backup_path = self.backup_dir / name

        if not backup_path.exists():
            return {"success": False, "error": "Backup not found"}

        # Restore database
        db_backup = backup_path / "pi-router.db"
        if db_backup.exists():
            shutil.copy2(db_backup, self.data_dir / "pi-router.db.restored")

            # Import data from restored backup
            try:
                self._import_sqlite(db_backup, self.db_path)
                os.remove(self.data_dir / "pi-router.db.restored")
            except Exception as e:
                logger.error(f"Failed to import database: {e}")
                return {"success": False, "error": str(e)}

        # Restore configuration
        config_backup = backup_path / "config"
        if config_backup.exists():
            etc_config = Path("/etc/pi-router")
            etc_config.mkdir(parents=True, exist_ok=True)

            for file in config_backup.iterdir():
                if file.is_file():
                    shutil.copy2(file, etc_config / file.name)

        logger.info(f"Backup restored: {backup_path}")

        return {
            "success": True,
            "name": name,
            "restored_at": datetime.now().isoformat()
        }

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all local backups."""
        backups = []

        for backup_path in self.backup_dir.iterdir():
            if backup_path.is_dir():
                metadata_file = backup_path / "metadata.json"

                metadata = {
                    "name": backup_path.name,
                    "created_at": datetime.fromtimestamp(backup_path.stat().st_ctime).isoformat(),
                    "size_mb": self._get_dir_size(backup_path) / (1024 * 1024)
                }

                if metadata_file.exists():
                    try:
                        with open(metadata_file) as f:
                            metadata.update(json.load(f))
                    except Exception as e:
                        logger.warning(f"Failed to read metadata: {e}")

                backups.append(metadata)

        return sorted(backups, key=lambda x: x["created_at"], reverse=True)

    def delete_backup(self, name: str) -> Dict[str, Any]:
        """Delete a local backup."""
        backup_path = self.backup_dir / name

        if not backup_path.exists():
            return {"success": False, "error": "Backup not found"}

        shutil.rmtree(backup_path)
        logger.info(f"Backup deleted: {backup_path}")

        return {"success": True, "name": name}

    def sync_to_s3(self, backup_name: str, s3_config: Dict[str, str]) -> Dict[str, Any]:
        """Sync backup to AWS S3."""
        try:
            import boto3
            from botocore.exceptions import ClientError

            backup_path = self.backup_dir / backup_name
            if not backup_path.exists():
                return {"success": False, "error": "Backup not found"}

            # Create S3 client
            s3 = boto3.client(
                's3',
                aws_access_key_id=s3_config.get('access_key'),
                aws_secret_access_key=s3_config.get('secret_key'),
                region_name=s3_config.get('region', 'us-east-1')
            )

            # Create tarball
            tarball = self._create_tarball(backup_path)

            try:
                bucket = s3_config['bucket']
                key = f"pi-router-backups/{backup_name}.tar.gz"

                s3.upload_file(str(tarball), bucket, key)

                # Clean up tarball
                tarball.unlink()

                logger.info(f"Backup synced to S3: {bucket}/{key}")

                return {
                    "success": True,
                    "provider": "s3",
                    "location": f"s3://{bucket}/{key}",
                    "synced_at": datetime.now().isoformat()
                }
            except ClientError as e:
                return {"success": False, "error": str(e)}

        except ImportError:
            return {"success": False, "error": "boto3 not installed. Install with: pip install boto3"}

    def sync_to_rsync(self, backup_name: str, rsync_config: Dict[str, str]) -> Dict[str, Any]:
        """Sync backup to remote server via rsync."""
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            return {"success": False, "error": "Backup not found"}

        try:
            host = rsync_config.get('host')
            user = rsync_config.get('user', 'pi')
            path = rsync_config.get('path', '~/backups')
            port = rsync_config.get('port', '22')

            # Create tarball
            tarball = self._create_tarball(backup_path)

            # Use rsync to transfer
            dest = f"{user}@{host}:{path}"
            cmd = [
                'rsync',
                '-avz',
                '-e', f'ssh -p {port}',
                str(tarball),
                dest
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            # Clean up tarball
            tarball.unlink()

            if result.returncode == 0:
                logger.info(f"Backup synced via rsync: {dest}")

                return {
                    "success": True,
                    "provider": "rsync",
                    "location": dest,
                    "synced_at": datetime.now().isoformat()
                }
            else:
                return {"success": False, "error": result.stderr}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def sync_to_ftp(self, backup_name: str, ftp_config: Dict[str, str]) -> Dict[str, Any]:
        """Sync backup to FTP server."""
        try:
            from ftplib import FTP

            backup_path = self.backup_dir / backup_name
            if not backup_path.exists():
                return {"success": False, "error": "Backup not found"}

            # Create tarball
            tarball = self._create_tarball(backup_path)

            try:
                ftp = FTP()
                ftp.connect(
                    ftp_config['host'],
                    int(ftp_config.get('port', 21))
                )
                ftp.login(ftp_config['user'], ftp_config['password'])

                # Change to backup directory
                remote_path = ftp_config.get('path', '/')
                if remote_path != '/':
                    ftp.cwd(remote_path)

                # Upload file
                with open(tarball, 'rb') as f:
                    ftp.storbinary(f'STOR {tarball.name}', f)

                ftp.quit()

                # Clean up tarball
                tarball.unlink()

                logger.info(f"Backup synced to FTP: {ftp_config['host']}")

                return {
                    "success": True,
                    "provider": "ftp",
                    "location": f"ftp://{ftp_config['host']}/{remote_path}/{tarball.name}",
                    "synced_at": datetime.now().isoformat()
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        except ImportError:
            return {"success": False, "error": "ftplib not available"}

    def sync_to_webdav(self, backup_name: str, webdav_config: Dict[str, str]) -> Dict[str, Any]:
        """Sync backup to WebDAV server (e.g., Nextcloud, ownCloud)."""
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            return {"success": False, "error": "Backup not found"}

        try:
            import requests

            # Create tarball
            tarball = self._create_tarball(backup_path)

            try:
                url = webdav_config['url']
                username = webdav_config.get('username')
                password = webdav_config.get('password')
                path = webdav_config.get('path', '/pi-router-backups')

                # Upload file
                upload_url = f"{url}{path}/{tarball.name}"

                with open(tarball, 'rb') as f:
                    response = requests.put(
                        upload_url,
                        data=f,
                        auth=(username, password) if username else None,
                        verify=webdav_config.get('verify_ssl', True)
                    )

                # Clean up tarball
                tarball.unlink()

                if response.status_code in (200, 201, 204):
                    logger.info(f"Backup synced to WebDAV: {upload_url}")

                    return {
                        "success": True,
                        "provider": "webdav",
                        "location": upload_url,
                        "synced_at": datetime.now().isoformat()
                    }
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}

            except Exception as e:
                return {"success": False, "error": str(e)}

        except ImportError:
            return {"success": False, "error": "requests not installed. Install with: pip install requests"}

    def export_settings(self) -> Dict[str, Any]:
        """Export settings as JSON for manual backup."""
        # Export database data as JSON
        settings = {
            "exported_at": datetime.now().isoformat(),
            "settings": {}
        }

        try:
            conn = sqlite3.connect(self.db_path)

            # Export config table
            cursor = conn.execute("SELECT key, value FROM config")
            for row in cursor:
                key, value = row
                try:
                    settings["settings"][key] = json.loads(value)
                except:
                    settings["settings"][key] = value

            conn.close()

            return {
                "success": True,
                "data": settings,
                "size_bytes": len(json.dumps(settings))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def import_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Import settings from JSON."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for key, value in settings.get("settings", {}).items():
                value_json = json.dumps(value) if not isinstance(value, str) else value
                cursor.execute("""
                    INSERT OR REPLACE INTO config (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, value_json))

            conn.commit()
            conn.close()

            logger.info("Settings imported successfully")

            return {
                "success": True,
                "imported_at": datetime.now().isoformat(),
                "keys_count": len(settings.get("settings", {}))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_dir_size(self, path: Path) -> int:
        """Get total size of directory in bytes."""
        total = 0
        for item in path.rglob('*'):
            if item.is_file():
                total += item.stat().st_size
        return total

    def _create_tarball(self, path: Path) -> Path:
        """Create a tarball of the backup directory."""
        import tarfile

        tarball_path = path.parent / f"{path.name}.tar.gz"

        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(path, arcname=path.name)

        return tarball_path

    def _import_sqlite(self, source_db: Path, target_db: Path) -> None:
        """Import data from source database to target database."""
        # Connect to both databases
        source = sqlite3.connect(source_db)
        target = sqlite3.connect(target_db)

        # Get list of tables
        tables = source.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

        for table in tables:
            table_name = table[0]

            # Get data from source
            data = source.execute(f"SELECT * FROM {table_name}").fetchall()

            if data:
                # Clear target table
                target.execute(f"DELETE FROM {table_name}")

                # Get column count
                col_count = len(data[0])

                # Insert data
                placeholders = ','.join(['?' for _ in range(col_count)])
                target.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", data)

        target.commit()
        source.close()
        target.close()
