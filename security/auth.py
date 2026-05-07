#!/usr/bin/env python3
"""JWT Token Authentication for Integration Endpoints"""
import jwt
import os
import time
from functools import wraps

class TokenAuth:
    """JWT token authentication."""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or os.getenv('JWT_SECRET_KEY', 'default-jwt-secret-change-in-prod')
        self.algorithm = 'HS256'
    
    def generate_token(self, user_id: str, expires_in: int = 3600) -> str:
        """Generate JWT token."""
        payload = {
            'user_id': user_id,
            'exp': time.time() + expires_in,
            'iat': time.time()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> dict:
        """Verify JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return {'valid': True, 'payload': payload}
        except jwt.ExpiredSignatureError:
            return {'valid': False, 'error': 'Token expired'}
        except jwt.InvalidTokenError:
            return {'valid': False, 'error': 'Invalid token'}
    
    def require_token(self, func):
        """Decorator to require token authentication."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check for token in environment or kwargs
            token = kwargs.get('token') or os.getenv('API_TOKEN')
            
            if not token:
                raise PermissionError('No authentication token provided')
            
            result = self.verify_token(token)
            if not result['valid']:
                raise PermissionError(f"Authentication failed: {result.get('error')}")
            
            return func(*args, **kwargs)
        return wrapper

# Global auth instance
_auth = None

def get_auth() -> TokenAuth:
    """Get or create global auth instance."""
    global _auth
    if _auth is None:
        _auth = TokenAuth()
    return _auth

def verify_token(token: str) -> bool:
    """Convenience function to verify token."""
    result = get_auth().verify_token(token)
    return result['valid']

def require_auth(func):
    """Decorator for requiring authentication."""
    return get_auth().require_token(func)