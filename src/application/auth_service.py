"""Authentication and authorization services."""
from datetime import datetime, timedelta
from typing import Optional
import logging
from jose import JWTError, jwt

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication and authorization."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """Initialize auth service.
        
        Args:
            secret_key: Secret key for JWT
            algorithm: JWT algorithm
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_access_token(
        self,
        subject: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create JWT access token.
        
        Args:
            subject: Token subject (usually user ID)
            expires_delta: Token expiration time
            
        Returns:
            JWT token
        """
        try:
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(hours=1)
            
            to_encode = {
                "sub": str(subject),
                "exp": expire,
                "iat": datetime.utcnow(),
            }
            
            encoded_jwt = jwt.encode(
                to_encode,
                self.secret_key,
                algorithm=self.algorithm,
            )
            
            logger.info(f"Created access token for subject {subject}")
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"Error creating access token: {str(e)}")
            raise
    
    def create_refresh_token(
        self,
        subject: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create JWT refresh token.
        
        Args:
            subject: Token subject
            expires_delta: Token expiration time
            
        Returns:
            JWT token
        """
        try:
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(days=7)
            
            to_encode = {
                "sub": str(subject),
                "type": "refresh",
                "exp": expire,
                "iat": datetime.utcnow(),
            }
            
            encoded_jwt = jwt.encode(
                to_encode,
                self.secret_key,
                algorithm=self.algorithm,
            )
            
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"Error creating refresh token: {str(e)}")
            raise
    
    def verify_token(self, token: str) -> Optional[str]:
        """Verify JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Token subject if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            subject: str = payload.get("sub")
            if subject is None:
                return None
            return subject
            
        except JWTError:
            logger.warning(f"Invalid token")
            return None
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            return None


class RBACService:
    """Role-based access control service."""
    
    def __init__(self):
        """Initialize RBAC service."""
        self.roles = {
            "admin": ["read", "write", "delete", "admin"],
            "editor": ["read", "write"],
            "viewer": ["read"],
            "user": ["read"],
        }
    
    def has_permission(
        self,
        user_role: str,
        required_permission: str,
    ) -> bool:
        """Check if user has required permission.
        
        Args:
            user_role: User role
            required_permission: Required permission
            
        Returns:
            True if user has permission
        """
        permissions = self.roles.get(user_role, [])
        return required_permission in permissions
    
    def has_role(self, user_role: str) -> bool:
        """Check if role exists.
        
        Args:
            user_role: User role
            
        Returns:
            True if role exists
        """
        return user_role in self.roles
    
    def add_role(self, role: str, permissions: list):
        """Add new role.
        
        Args:
            role: Role name
            permissions: List of permissions
        """
        self.roles[role] = permissions
        logger.info(f"Added role {role}")
    
    def get_user_permissions(self, user_role: str) -> list:
        """Get all permissions for a role.
        
        Args:
            user_role: User role
            
        Returns:
            List of permissions
        """
        return self.roles.get(user_role, [])
