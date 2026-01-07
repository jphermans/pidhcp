"""Backup API routes."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from backend.services.backup_service import BackupService
from backend.api.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


class BackupCreate(BaseModel):
    name: Optional[str] = None


class BackupRestore(BaseModel):
    name: str


class BackupSyncS3(BaseModel):
    backup_name: str
    access_key: str
    secret_key: str
    bucket: str
    region: str = "us-east-1"


class BackupSyncRsync(BaseModel):
    backup_name: str
    host: str
    user: str = "pi"
    path: str = "~/backups"
    port: int = 22


class BackupSyncFTP(BaseModel):
    backup_name: str
    host: str
    port: int = 21
    user: str
    password: str
    path: str = "/"


class BackupSyncWebDAV(BaseModel):
    backup_name: str
    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    path: str = "/pi-router-backups"
    verify_ssl: bool = True


class SettingsImport(BaseModel):
    settings: Dict[str, Any]


@router.post("/backup/create")
async def create_backup(
    request: BackupCreate,
    _current_user: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a new backup."""
    try:
        service = BackupService()
        result = service.create_backup(request.name)
        return result
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/restore")
async def restore_backup(
    request: BackupRestore,
    _current_user: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Restore a backup."""
    try:
        service = BackupService()
        result = service.restore_backup(request.name)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backup/list")
async def list_backups(_current_user: str = Depends(get_current_user)) -> Dict[str, List]:
    """List all backups."""
    try:
        service = BackupService()
        backups = service.list_backups()
        return {"backups": backups}
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/backup/{name}")
async def delete_backup(
    name: str,
    _current_user: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete a backup."""
    try:
        service = BackupService()
        result = service.delete_backup(name)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/sync/s3")
async def sync_to_s3(
    request: BackupSyncS3,
    _current_user: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Sync backup to AWS S3."""
    try:
        service = BackupService()
        result = service.sync_to_s3(request.backup_name, {
            "access_key": request.access_key,
            "secret_key": request.secret_key,
            "bucket": request.bucket,
            "region": request.region
        })
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync to S3: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/sync/rsync")
async def sync_to_rsync(
    request: BackupSyncRsync,
    _current_user: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Sync backup to remote server via rsync."""
    try:
        service = BackupService()
        result = service.sync_to_rsync(request.backup_name, {
            "host": request.host,
            "user": request.user,
            "path": request.path,
            "port": request.port
        })
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync via rsync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/sync/ftp")
async def sync_to_ftp(
    request: BackupSyncFTP,
    _current_user: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Sync backup to FTP server."""
    try:
        service = BackupService()
        result = service.sync_to_ftp(request.backup_name, {
            "host": request.host,
            "port": request.port,
            "user": request.user,
            "password": request.password,
            "path": request.path
        })
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync to FTP: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/sync/webdav")
async def sync_to_webdav(
    request: BackupSyncWebDAV,
    _current_user: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Sync backup to WebDAV server."""
    try:
        service = BackupService()
        result = service.sync_to_webdav(request.backup_name, {
            "url": request.url,
            "username": request.username,
            "password": request.password,
            "path": request.path,
            "verify_ssl": request.verify_ssl
        })
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync to WebDAV: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backup/export")
async def export_settings(
    _current_user: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Export settings as JSON."""
    try:
        service = BackupService()
        result = service.export_settings()
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/import")
async def import_settings(
    request: SettingsImport,
    _current_user: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Import settings from JSON."""
    try:
        service = BackupService()
        result = service.import_settings({"settings": request.settings})
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
