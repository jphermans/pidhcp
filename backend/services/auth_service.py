"""Authentication service for web UI login."""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# JWT configuration
SECRET_KEY = "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication and authorization."""

    def __init__(self, secret_key: str = SECRET_KEY):
        self.secret_key = secret_key
        self.algorithm = ALGORITHM
        self.access_token_expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES

        # Default admin credentials (should be overridden by config)
        self.users_db: Dict[str, dict] = {
            "admin": {
                "username": "admin",
                "hashed_password": self.get_password_hash("admin123")
            }
        }

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)

    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Authenticate a user."""
        user = self.users_db.get(username)
        if not user:
            return None
        if not self.verify_password(password, user["hashed_password"]):
            return None
        return user

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[str]:
        """Verify a JWT token and return the username."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            if username is None:
                return None
            return username
        except JWTError:
            return None

    def update_password(self, username: str, new_password: str) -> bool:
        """Update a user's password."""
        if username not in self.users_db:
            return False
        self.users_db[username]["hashed_password"] = self.get_password_hash(new_password)
        logger.info(f"Password updated for user: {username}")
        return True

    def load_users_from_config(self, users: dict) -> None:
        """Load users from configuration."""
        self.users_db = {}
        for username, data in users.items():
            self.users_db[username] = {
                "username": username,
                "hashed_password": data.get("hashed_password", self.get_password_hash(data.get("password", "admin123")))
            }
        logger.info(f"Loaded {len(self.users_db)} users from configuration")
