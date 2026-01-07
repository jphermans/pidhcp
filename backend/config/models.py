"""Configuration data models."""

import os
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
import re


class UplinkConfig(BaseModel):
    """Wi-Fi uplink (wlan0) configuration."""
    mode: Literal["wpa", "portal"] = Field(
        default="wpa",
        description="Connection mode: wpa (WPA2-PSK) or portal (captive portal)"
    )
    ssid: str = Field(default="", min_length=0, max_length=32, description="Uplink Wi-Fi SSID")
    password: Optional[str] = Field(default="", max_length=63, description="Uplink Wi-Fi password (WPA mode)")
    country: str = Field(default="US", min_length=2, max_length=2, description="Country code")
    portal_url: Optional[str] = Field(default=None, description="Captive portal URL (portal mode)")
    portal_username: Optional[str] = Field(default=None, description="Portal login username")
    portal_password: Optional[str] = Field(default=None, description="Portal login password")
    auto_detect_portal: bool = Field(
        default=True,
        description="Automatically detect and handle captive portals"
    )

    @validator('country')
    def upper_case_country(cls, v):
        return v.upper()

    @validator('ssid')
    def ssid_required_for_wpa(cls, v, values):
        if values.get('mode') == 'wpa' and not v:
            raise ValueError('SSID is required for WPA mode')
        return v


class APConfig(BaseModel):
    """Access Point (wlan1) configuration."""
    ssid: str = Field(default="PiRouter-AP", min_length=1, max_length=32, description="AP SSID")
    password: str = Field(default="SecurePass123", min_length=8, max_length=63, description="AP password (WPA2)")
    channel: int = Field(default=6, ge=1, le=13, description="Wi-Fi channel (1-13)")
    country: str = Field(default="US", min_length=2, max_length=2, description="Country code")
    hw_mode: str = Field(default="g", description="Hardware mode (a/b/g/n/ac)")

    @validator('hw_mode')
    def validate_hw_mode(cls, v):
        valid_modes = ['a', 'b', 'g', 'n', 'ac']
        if v not in valid_modes:
            raise ValueError(f'Invalid hw_mode. Must be one of: {", ".join(valid_modes)}')
        return v

    @validator('country')
    def upper_case_country(cls, v):
        return v.upper()


class DHCPConfig(BaseModel):
    """DHCP server configuration."""
    subnet: str = Field(default="10.42.0.0", description="Subnet address")
    netmask: str = Field(default="255.255.255.0", description="Network mask")
    gateway: str = Field(default="10.42.0.1", description="Gateway IP (wlan1 address)")
    range_start: str = Field(default="10.42.0.50", description="DHCP range start")
    range_end: str = Field(default="10.42.0.200", description="DHCP range end")
    lease_time: str = Field(default="12h", description="DHCP lease time")

    @validator('gateway')
    def validate_gateway(cls, v):
        if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', v):
            raise ValueError('Invalid IP address format')
        parts = v.split('.')
        if any(int(p) > 255 for p in parts):
            raise ValueError('IP address parts must be 0-255')
        return v

    @validator('range_start', 'range_end', pre=True)
    def validate_ips(cls, v):
        if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', str(v)):
            raise ValueError('Invalid IP address format')
        parts = str(v).split('.')
        if any(int(p) > 255 for p in parts):
            raise ValueError('IP address parts must be 0-255')
        return v


class NetworkConfig(BaseModel):
    """Complete network configuration."""
    uplink: UplinkConfig
    ap: APConfig
    dhcp: DHCPConfig

    class Config:
        json_encoders = {
            # Redact passwords when logging
            str: lambda v: "*****" if "password" in str(v) else v
        }


class AppConfig(BaseModel):
    """Application configuration."""
    secret_key: str = Field(default="CHANGE_THIS_SECRET_KEY_IN_PRODUCTION", description="JWT secret key")
    admin_username: str = Field(default="admin", description="Admin username")
    admin_password: str = Field(default="admin123", description="Admin password (change on first login)")
    log_level: str = Field(default="INFO", description="Logging level")
    host: str = Field(default="0.0.0.0", description="Server bind address")
    port: int = Field(default=8080, description="Server port")
    config_dir: str = Field(default_factory=lambda: os.environ.get('CONFIG_DIR', '/config'), description="Configuration directory")
    state_dir: str = Field(default_factory=lambda: os.environ.get('STATE_DIR', '/data'), description="State directory")
