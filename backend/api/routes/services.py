"""Service management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import logging
import asyncio

from services.network_service import NetworkService
from services.system_service import SystemService
from services.auth_service import AuthService
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return username


class ServiceActionRequest(BaseModel):
    """Service action request."""
    service: str  # hostapd, dnsmasq, wpa_supplicant@wlan0
    action: str  # restart, start, stop


@router.post("/control")
async def control_service(
    request: ServiceActionRequest,
    _current_user: str = Depends(get_current_user)
):
    """Control a system service."""
    logger.info(f"Service {request.action} requested for {request.service}")

    valid_services = ["hostapd", "dnsmasq", "wpa_supplicant@wlan0"]
    valid_actions = ["restart", "start", "stop"]

    if request.service not in valid_services:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid service. Valid services: {', '.join(valid_services)}"
        )

    if request.action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action. Valid actions: {', '.join(valid_actions)}"
        )

    # Execute action
    success, message = await system_service.run_command([
        "sudo", "systemctl", request.action, request.service
    ])

    if success:
        return {"success": True, "message": f"Service {request.service} {request.action}ed successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )


@router.get("/logs/{service}")
async def get_service_logs(
    service: str,
    lines: int = 50,
    _current_user: str = Depends(get_current_user)
):
    """Get logs for a service."""
    valid_services = ["hostapd", "dnsmasq", "wpa_supplicant@wlan0"]

    if service not in valid_services:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid service. Valid services: {', '.join(valid_services)}"
        )

    logs = await system_service.get_service_logs(service, lines)
    return {"service": service, "logs": logs}


@router.post("/setup-nat")
async def setup_nat(_current_user: str = Depends(get_current_user)):
    """Setup NAT and IP forwarding."""
    logger.info("Setting up NAT and IP forwarding")

    # Enable IP forwarding
    success, message = await network_service.enable_ip_forwarding()
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable IP forwarding: {message}"
        )

    # Setup nftables
    success, message = await network_service.setup_nat()
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup NAT: {message}"
        )

    return {"success": True, "message": "NAT and IP forwarding configured successfully"}


@router.post("/reboot")
async def reboot_system(_current_user: str = Depends(get_current_user)):
    """Reboot the system."""
    logger.warning(f"System reboot requested by user: {_current_user}")

    # Execute reboot in background after response
    asyncio.create_task(_delayed_reboot())

    return {
        "success": True,
        "message": "System is rebooting... You will lose connection shortly."
    }


async def _delayed_reboot():
    """Execute reboot after a short delay."""
    await asyncio.sleep(2)
    success, message = await system_service.run_command(["sudo", "reboot"])
    if not success:
        logger.error(f"Failed to reboot: {message}")


@router.post("/shutdown")
async def shutdown_system(_current_user: str = Depends(get_current_user)):
    """Shutdown the system."""
    logger.warning(f"System shutdown requested by user: {_current_user}")

    # Execute shutdown in background after response
    asyncio.create_task(_delayed_shutdown())

    return {
        "success": True,
        "message": "System is shutting down... Goodbye!"
    }


async def _delayed_shutdown():
    """Execute shutdown after a short delay."""
    await asyncio.sleep(2)
    success, message = await system_service.run_command(["sudo", "shutdown", "-h", "now"])
    if not success:
        logger.error(f"Failed to shutdown: {message}")
