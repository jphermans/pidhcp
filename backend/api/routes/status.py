"""Status routes."""

from fastapi import APIRouter, Depends
import logging

from services.network_service import NetworkService
from services.system_service import SystemService
from services.auth_service import AuthService
from database.db import Database
from main import network_service, system_service, auth_service

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
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return username


@router.get("/network")
async def get_network_status(_current_user: str = Depends(get_current_user)):
    """Get overall network status."""
    wlan0_status = await network_service.get_wlan0_status()
    wlan1_status = await network_service.get_wlan1_status()
    dhcp_leases = await network_service.get_dhcp_leases()
    nat_enabled = await network_service.check_nat_enabled()

    return {
        "wlan0": wlan0_status,
        "wlan1": wlan1_status,
        "dhcp_leases": dhcp_leases,
        "nat_enabled": nat_enabled
    }


@router.get("/wlan0")
async def get_wlan0_status(_current_user: str = Depends(get_current_user)):
    """Get wlan0 (uplink) status."""
    return await network_service.get_wlan0_status()


@router.get("/wlan1")
async def get_wlan1_status(_current_user: str = Depends(get_current_user)):
    """Get wlan1 (AP) status."""
    return await network_service.get_wlan1_status()


@router.get("/devices")
async def get_devices(_current_user: str = Depends(get_current_user)):
    """Get all connected devices with online/offline status."""
    db = Database()

    # Sync devices from DHCP leases first
    try:
        leases = await network_service.get_dhcp_leases()
        for lease in leases:
            await db.update_device(
                mac=lease["mac"],
                ip=lease["ip"],
                hostname=lease["hostname"]
            )
    except Exception as e:
        logger.error(f"Error syncing devices from DHCP: {e}")

    # Get devices with 30-minute filter
    devices = await db.get_devices(offline_timeout_minutes=30)

    return {"devices": devices}


@router.get("/dhcp-leases")
async def get_dhcp_leases(_current_user: str = Depends(get_current_user)):
    """Get DHCP leases."""
    return {"leases": await network_service.get_dhcp_leases()}


@router.get("/system")
async def get_system_status(_current_user: str = Depends(get_current_user)):
    """Get system status."""
    system_info = await system_service.get_system_info()

    # Get service statuses
    hostapd_status = await system_service.get_service_status("hostapd")
    dnsmasq_status = await system_service.get_service_status("dnsmasq")
    wpa_status = await system_service.get_service_status("wpa_supplicant@wlan0")

    return {
        "system": system_info,
        "services": {
            "hostapd": hostapd_status,
            "dnsmasq": dnsmasq_status,
            "wpa_supplicant": wpa_status
        }
    }
