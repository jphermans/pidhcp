"""Configuration routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, validator
import logging

from config.manager import ConfigManager
from config.models import NetworkConfig, UplinkConfig, APConfig, DHCPConfig
from services.network_service import NetworkService
from services.auth_service import AuthService
from main import get_config_manager, network_service, auth_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Authentication
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get the current authenticated user."""
    token = credentials.credentials
    username = auth_service.verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return username


# Request models
class UplinkUpdateRequest(BaseModel):
    """Uplink configuration update request."""
    ssid: str
    password: str
    country: str = "US"

    @validator('ssid')
    def ssid_not_empty(cls, v):
        if not v.strip():
            raise ValueError('SSID cannot be empty')
        return v

    @validator('password')
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class APUpdateRequest(BaseModel):
    """AP configuration update request."""
    ssid: str
    password: str
    channel: int = 6
    country: str = "US"
    hw_mode: str = "g"

    @validator('ssid')
    def ssid_not_empty(cls, v):
        if not v.strip():
            raise ValueError('SSID cannot be empty')
        return v

    @validator('password')
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

    @validator('channel')
    def channel_range(cls, v):
        if not 1 <= v <= 13:
            raise ValueError('Channel must be between 1 and 13')
        return v


class DHCPUpdateRequest(BaseModel):
    """DHCP configuration update request."""
    subnet: str = "10.42.0.0"
    netmask: str = "255.255.255.0"
    gateway: str = "10.42.0.1"
    range_start: str = "10.42.0.50"
    range_end: str = "10.42.0.200"
    lease_time: str = "12h"


@router.get("/network")
async def get_network_config(_current_user: str = Depends(get_current_user)):
    """Get current network configuration."""
    config = config_manager.load_network_config()
    # Return config without passwords
    return {
        "uplink": {
            "ssid": config.uplink.ssid,
            "country": config.uplink.country,
            "has_password": bool(config.uplink.password)
        },
        "ap": {
            "ssid": config.ap.ssid,
            "channel": config.ap.channel,
            "country": config.ap.country,
            "hw_mode": config.ap.hw_mode,
            "has_password": True
        },
        "dhcp": config.dhcp.dict()
    }


@router.post("/uplink")
async def update_uplink_config(
    request: UplinkUpdateRequest,
    _current_user: str = Depends(get_current_user)
):
    """Update uplink (wlan0) configuration."""
    logger.info(f"Updating uplink config for SSID: {request.ssid}")

    # Update wpa_supplicant config and reconnect
    success, message = await network_service.update_uplink(
        ssid=request.ssid,
        password=request.password,
        country=request.country
    )

    if success:
        # Update saved config
        config = config_manager.load_network_config()
        config.uplink = UplinkConfig(
            ssid=request.ssid,
            password=request.password,
            country=request.country
        )
        config_manager.save_network_config(config)

        logger.info("Uplink configuration updated successfully")
        return {"success": True, "message": message}
    else:
        logger.error(f"Failed to update uplink: {message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )


@router.post("/ap")
async def update_ap_config(
    request: APUpdateRequest,
    _current_user: str = Depends(get_current_user)
):
    """Update AP (wlan1) configuration."""
    logger.info(f"Updating AP config for SSID: {request.ssid}")

    # Update hostapd config
    success, message = await network_service.update_ap_config({
        'ssid': request.ssid,
        'password': request.password,
        'channel': request.channel,
        'country': request.country,
        'hw_mode': request.hw_mode
    })

    if success:
        # Update saved config
        config = config_manager.load_network_config()
        config.ap = APConfig(
            ssid=request.ssid,
            password=request.password,
            channel=request.channel,
            country=request.country,
            hw_mode=request.hw_mode
        )
        config_manager.save_network_config(config)

        logger.info("AP configuration updated successfully")
        return {"success": True, "message": message}
    else:
        logger.error(f"Failed to update AP: {message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )


@router.post("/dhcp")
async def update_dhcp_config(
    request: DHCPUpdateRequest,
    _current_user: str = Depends(get_current_user)
):
    """Update DHCP configuration."""
    logger.info("Updating DHCP configuration")

    # Get current AP config for dnsmasq
    config = config_manager.load_network_config()

    # Update dnsmasq config
    success, message = await network_service.update_dhcp_config(
        dhcp_config=request.dict(),
        ap_config=config.ap.dict()
    )

    if success:
        # Update saved config
        config.dhcp = DHCPConfig(**request.dict())
        config_manager.save_network_config(config)

        logger.info("DHCP configuration updated successfully")
        return {"success": True, "message": message}
    else:
        logger.error(f"Failed to update DHCP: {message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )


@router.post("/reset")
async def reset_to_factory(_current_user: str = Depends(get_current_user)):
    """Reset configuration to factory defaults."""
    logger.warning("Resetting configuration to factory defaults")

    config_manager.reset_to_factory()

    return {
        "success": True,
        "message": "Configuration reset to factory defaults. Please reconfigure the router."
    }
