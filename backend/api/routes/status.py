"""Status routes."""

from fastapi import APIRouter, Depends, HTTPException, status
import logging

from services.network_service import NetworkService
from services.system_service import SystemService
from database.db import Database
from main import get_network_service, get_system_service, get_auth_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Authentication
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service = Depends(get_auth_service)
) -> str:
    """Get the current authenticated user."""
    token = credentials.credentials
    username = auth_service.verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return username


@router.get("/network")
async def get_network_status(
    _current_user: str = Depends(get_current_user),
    network_service = Depends(get_network_service)
):
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
async def get_wlan0_status(
    _current_user: str = Depends(get_current_user),
    network_service = Depends(get_network_service)
):
    """Get wlan0 (uplink) status."""
    return await network_service.get_wlan0_status()


@router.get("/wlan1")
async def get_wlan1_status(
    _current_user: str = Depends(get_current_user),
    network_service = Depends(get_network_service)
):
    """Get wlan1 (AP) status."""
    return await network_service.get_wlan1_status()


@router.get("/devices")
async def get_devices(
    _current_user: str = Depends(get_current_user),
    network_service = Depends(get_network_service)
):
    """Get all connected devices with online/offline status."""
    db = Database()

    # Sync devices from DHCP leases first
    try:
        leases = await network_service.get_dhcp_leases()
        logger.info(f"Retrieved {len(leases)} DHCP leases")
        for lease in leases:
            logger.debug(f"Syncing device: {lease['hostname']} ({lease['mac']}) at {lease['ip']}")
            await db.update_device(
                mac=lease["mac"],
                ip=lease["ip"],
                hostname=lease["hostname"]
            )
    except Exception as e:
        logger.error(f"Error syncing devices from DHCP: {e}", exc_info=True)

    # Get devices with 30-minute filter
    devices = await db.get_devices(offline_timeout_minutes=30)
    logger.info(f"Returning {len(devices)} devices from database")

    return {"devices": devices}


@router.get("/dhcp-leases")
async def get_dhcp_leases(
    _current_user: str = Depends(get_current_user),
    network_service = Depends(get_network_service)
):
    """Get DHCP leases."""
    return {"leases": await network_service.get_dhcp_leases()}


@router.get("/system")
async def get_system_status(
    _current_user: str = Depends(get_current_user),
    system_service = Depends(get_system_service)
):
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


@router.get("/interface-conflicts")
async def get_interface_conflicts(
    _current_user: str = Depends(get_current_user),
    network_service = Depends(get_network_service)
):
    """Check for interface configuration conflicts."""
    conflicts = await network_service.get_interface_conflicts()
    return {"conflicts": conflicts}


@router.post("/fix-wlan1")
async def fix_wlan1_ap_mode(
    _current_user: str = Depends(get_current_user),
    network_service = Depends(get_network_service)
):
    """Fix wlan1 to ensure it's in AP mode and not managed by wpa_supplicant."""
    success, message = await network_service.ensure_wlan1_ap_mode()
    return {"success": success, "message": message}
