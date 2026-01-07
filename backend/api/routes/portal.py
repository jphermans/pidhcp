"""Captive portal management routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict
import logging

from services.portal_service import PortalService
from services.auth_service import AuthService
from main import auth_service

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


class PortalLoginRequest(BaseModel):
    """Portal login request."""
    portal_url: str = Field(..., description="URL of the captive portal")
    username: Optional[str] = Field(None, description="Username for portal login")
    password: Optional[str] = Field(None, description="Password for portal login")
    form_data: Optional[Dict] = Field(None, description="Additional form data")


@router.get("/detect")
async def detect_portal(_current_user: str = Depends(get_current_user)):
    """Detect if behind a captive portal."""
    portal_service = PortalService()
    try:
        result = await portal_service.detect_captive_portal()
        return result
    except Exception as e:
        logger.error(f"Portal detection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        await portal_service.close()


@router.post("/login")
async def submit_portal_login(
    request: PortalLoginRequest,
    _current_user: str = Depends(get_current_user)
):
    """Submit login to captive portal."""
    portal_service = PortalService()
    try:
        result = await portal_service.submit_portal_login(
            portal_url=request.portal_url,
            username=request.username,
            password=request.password,
            form_data=request.form_data
        )
        return result
    except Exception as e:
        logger.error(f"Portal login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        await portal_service.close()


@router.post("/html")
async def get_portal_html(
    portal_url: str,
    _current_user: str = Depends(get_current_user)
):
    """Get the HTML content of a captive portal."""
    portal_service = PortalService()
    try:
        html = await portal_service.get_portal_html(portal_url)
        if html:
            return {"html": html}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch portal HTML"
            )
    except Exception as e:
        logger.error(f"Get portal HTML error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        await portal_service.close()


@router.post("/check-connectivity")
async def check_connectivity(_current_user: str = Depends(get_current_user)):
    """Check internet connectivity after portal login."""
    portal_service = PortalService()
    try:
        has_internet = await portal_service.check_internet_after_login()
        return {"has_internet": has_internet}
    except Exception as e:
        logger.error(f"Connectivity check error: {e}")
        return {"has_internet": False, "error": str(e)}
    finally:
        await portal_service.close()
