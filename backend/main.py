"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import status as http_status
import uvicorn

from config.manager import ConfigManager
from services.auth_service import AuthService
from services.network_service import NetworkService
from services.system_service import SystemService
from database.db import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global services
config_manager = None
auth_service = None
network_service = None
system_service = None
database = None


# Dependency functions for FastAPI
def get_config_manager():
    """Get config manager instance."""
    return config_manager


def get_auth_service():
    """Get auth service instance."""
    return auth_service


def get_network_service():
    """Get network service instance."""
    return network_service


def get_system_service():
    """Get system service instance."""
    return system_service


def get_database():
    """Get database instance."""
    return database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global config_manager, auth_service, network_service, system_service, database

    logger.info("Starting Pi Router API...")

    # Initialize database
    database = Database()
    await database.init()
    logger.info("Database initialized")

    # Initialize services
    config_manager = ConfigManager()
    app_config = config_manager.load_app_config()

    auth_service = AuthService(secret_key=app_config.secret_key)
    # Don't pass config_dir - let NetworkService use environment variable
    network_service = NetworkService()
    system_service = SystemService()

    logger.info("Services initialized")

    # Setup NAT and IP forwarding on startup (required for wlan1 clients to access internet)
    logger.info("Setting up NAT and IP forwarding...")
    nat_success, nat_msg = await network_service.enable_ip_forwarding()
    if nat_success:
        logger.info("IP forwarding enabled")
    else:
        logger.warning(f"Failed to enable IP forwarding: {nat_msg}")

    nat_success, nat_msg = await network_service.setup_nat()
    if nat_success:
        logger.info("NAT rules configured")
    else:
        logger.warning(f"Failed to setup NAT: {nat_msg}")

    yield

    logger.info("Shutting down Pi Router API...")


# Create FastAPI app
app = FastAPI(
    title="Pi Router API",
    description="Wi-Fi Router Management API for Raspberry Pi",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# Import routes after app creation to avoid circular imports
# Import here and include routers
from api.routes import auth, status, config, services, portal, backup

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(status.router, prefix="/api/status", tags=["Status"])
app.include_router(config.router, prefix="/api/config", tags=["Configuration"])
app.include_router(services.router, prefix="/api/services", tags=["Services"])
app.include_router(portal.router, prefix="/api/portal", tags=["Captive Portal"])
app.include_router(backup.router, prefix="/api", tags=["Backup"])

# Mount static files (frontend)
try:
    app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="frontend")
    logger.info("Frontend mounted at /")
except Exception as e:
    logger.warning(f"Could not mount frontend: {e}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "pi-router-api"}


def main():
    """Run the application."""
    app_config = config_manager.load_app_config() if config_manager else ConfigManager().load_app_config()

    uvicorn.run(
        "main:app",
        host=app_config.host,
        port=app_config.port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
