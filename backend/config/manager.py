"""Configuration manager for loading, saving, and validating configs."""

import yaml
import os
from pathlib import Path
from typing import Optional
import shutil
import logging

from .models import AppConfig, NetworkConfig, APConfig, DHCPConfig, UplinkConfig

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application and network configuration."""

    def __init__(self, config_dir: str = "/etc/pi-router", state_dir: str = "/var/lib/pi-router"):
        self.config_dir = Path(config_dir)
        self.state_dir = Path(state_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.network_config_file = self.config_dir / "network.yaml"
        self.app_config_file = self.config_dir / "app.yaml"

    def load_network_config(self) -> NetworkConfig:
        """Load network configuration from file, or return defaults."""
        if not self.network_config_file.exists():
            logger.info("Network config not found, creating defaults")
            default_config = NetworkConfig(
                uplink=UplinkConfig(
                    ssid="",
                    password="",
                    country="US"
                ),
                ap=APConfig(),
                dhcp=DHCPConfig()
            )
            self.save_network_config(default_config)
            return default_config

        try:
            with open(self.network_config_file, 'r') as f:
                data = yaml.safe_load(f)
                return NetworkConfig(**data)
        except Exception as e:
            logger.error(f"Failed to load network config: {e}")
            raise

    def save_network_config(self, config: NetworkConfig) -> None:
        """Save network configuration to file."""
        # Create backup first
        if self.network_config_file.exists():
            backup_file = self.config_dir / f"network.yaml.backup"
            shutil.copy2(self.network_config_file, backup_file)

        try:
            with open(self.network_config_file, 'w') as f:
                # Use safe_dump but redact passwords for safety
                data = config.dict()
                yaml.safe_dump(data, f, default_flow_style=False)
            logger.info("Network configuration saved")
        except Exception as e:
            logger.error(f"Failed to save network config: {e}")
            # Restore backup if it existed
            if self.network_config_file.exists() and (self.config_dir / "network.yaml.backup").exists():
                shutil.copy2(self.config_dir / "network.yaml.backup", self.network_config_file)
            raise

    def load_app_config(self) -> AppConfig:
        """Load application configuration from file, or return defaults."""
        if not self.app_config_file.exists():
            logger.info("App config not found, creating defaults")
            default_config = AppConfig()
            self.save_app_config(default_config)
            return default_config

        try:
            with open(self.app_config_file, 'r') as f:
                data = yaml.safe_load(f)
                return AppConfig(**data)
        except Exception as e:
            logger.error(f"Failed to load app config: {e}")
            return AppConfig()

    def save_app_config(self, config: AppConfig) -> None:
        """Save application configuration to file."""
        try:
            with open(self.app_config_file, 'w') as f:
                data = config.dict()
                # Redact secret key in file
                if data.get('secret_key') == "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION":
                    data['secret_key'] = "***CHANGE_THIS***"
                yaml.safe_dump(data, f, default_flow_style=False)
            logger.info("App configuration saved")
        except Exception as e:
            logger.error(f"Failed to save app config: {e}")
            raise

    def reset_to_factory(self) -> None:
        """Reset all configuration to factory defaults."""
        logger.warning("Resetting configuration to factory defaults")

        # Backup existing configs
        if self.network_config_file.exists():
            shutil.move(self.network_config_file, self.config_dir / "network.yaml.factory_backup")
        if self.app_config_file.exists():
            shutil.move(self.app_config_file, self.config_dir / "app.yaml.factory_backup")

        # Create fresh defaults
        self.load_network_config()  # Creates default
        self.load_app_config()  # Creates default

        logger.info("Configuration reset to factory defaults")
