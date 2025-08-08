"""JWT utilities for Telegram account linking"""

import jwt
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from config import settings


class JWTManager:
    """Handles JWT token creation and verification for Telegram linking"""
    
    def __init__(self):
        self.secret = settings.BACKEND_JWT_SECRET
        self.algorithm = "HS256"
        self.audience = settings.BACKEND_JWT_AUDIENCE
        self.issuer = "fastapi-telegram-link"
    
    def create_link_token(self, telegram_user_id: int, expires_minutes: int = 5) -> Dict[str, str]:
        """
        Create a short-lived link token for Telegram account linking
        
        Args:
            telegram_user_id: The Telegram user ID to link
            expires_minutes: Token expiry time in minutes (default: 5)
        
        Returns:
            Dict containing the token and jti
        """
        now = datetime.now(timezone.utc)
        jti = str(uuid.uuid4())
        
        payload = {
            "sub": "telegram-link",
            "telegram_user_id": telegram_user_id,
            "jti": jti,
            "iat": now,
            "exp": now + timedelta(minutes=expires_minutes),
            "aud": self.audience,
            "iss": self.issuer
        }
        
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return {
            "token": token,
            "jti": jti,
            "expires_at": payload["exp"]
        }
    
    def verify_link_token(self, token: str) -> Optional[Dict]:
        """
        Verify and decode a link token
        
        Args:
            token: The JWT token to verify
        
        Returns:
            Decoded payload if valid, None if invalid
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret, 
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer
            )
            
            # Ensure this is a telegram-link token
            if payload.get("sub") != "telegram-link":
                return None
                
            return payload
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def create_session_token(self, user_id: int, telegram_user_id: int, expires_hours: int = 24) -> str:
        """
        Create a session token after successful linking
        
        Args:
            user_id: The internal user ID
            telegram_user_id: The Telegram user ID
            expires_hours: Session token expiry in hours (default: 24)
        
        Returns:
            JWT session token
        """
        now = datetime.now(timezone.utc)
        
        payload = {
            "sub": str(user_id),
            "telegram_user_id": telegram_user_id,
            "iat": now,
            "exp": now + timedelta(hours=expires_hours),
            "aud": "session",
            "iss": self.issuer
        }
        
        return jwt.encode(payload, settings.SESSION_SECRET, algorithm=self.algorithm)
    
    def verify_session_token(self, token: str) -> Optional[Dict]:
        """
        Verify a session token
        
        Args:
            token: The session JWT token to verify
        
        Returns:
            Decoded payload if valid, None if invalid
        """
        try:
            payload = jwt.decode(
                token, 
                settings.SESSION_SECRET, 
                algorithms=[self.algorithm],
                audience="session",
                issuer=self.issuer
            )
            return payload
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


# Global instance
jwt_manager = JWTManager()