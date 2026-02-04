"""
Security hardening module.

Provides CSRF protection, rate limiting, input sanitization,
and session security for the application.
"""

import re
import html
import secrets
from functools import wraps
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from flask import request, session, current_app, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, generate_csrf


# Initialize extensions at module level
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)


def generate_csrf_token() -> str:
    """
    Generate a new CSRF token.
    
    Returns:
        A new CSRF token string
    """
    return secrets.token_urlsafe(32)


def validate_csrf_token(token: str, expected_token: str = None) -> bool:
    """
    Validate a CSRF token.
    
    Args:
        token: The token to validate
        expected_token: The expected token (if None, uses session token)
    
    Returns:
        True if valid, False otherwise
    """
    if not token:
        return False
    
    if expected_token is None:
        expected_token = session.get('csrf_token')
    
    if not expected_token:
        return False
    
    return token == expected_token


# Security configuration defaults
DEFAULT_CONFIG = {
    'SESSION_COOKIE_SECURE': True,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'PERMANENT_SESSION_LIFETIME': timedelta(hours=1),
    'WTF_CSRF_TIME_LIMIT': 3600,  # 1 hour
    'WTF_CSRF_SSL_STRICT': True,
}


def add_security_headers(response):
    """
    Add security headers to response.
    This is a standalone function that can be used as an after_request handler.
    """
    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self';"
    )
    
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response


def init_security(app):
    """Initialize security extensions with the app."""
    # Apply default security config
    for key, value in DEFAULT_CONFIG.items():
        if key not in app.config:
            app.config[key] = value
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Initialize rate limiter
    limiter.init_app(app)


# Rate limit configurations
RATE_LIMITS = {
    'generate': "10 per hour",
    'validate': "60 per hour",
    'admin_login': "5 per minute",
    'admin_actions': "30 per minute",
}


def rate_limit_generate():
    """Decorator for generation endpoint rate limiting."""
    return limiter.limit(RATE_LIMITS['generate'])


def rate_limit_validate():
    """Decorator for validation endpoint rate limiting."""
    return limiter.limit(RATE_LIMITS['validate'])


def rate_limit_admin_login():
    """Decorator for admin login rate limiting."""
    return limiter.limit(RATE_LIMITS['admin_login'])


def rate_limit_admin():
    """Decorator for general admin actions rate limiting."""
    return limiter.limit(RATE_LIMITS['admin_actions'])


# Input sanitization
HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
SCRIPT_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.DOTALL | re.IGNORECASE)
EVENT_HANDLER_PATTERN = re.compile(r'on\w+\s*=', re.IGNORECASE)


def sanitize_string(value: str, max_length: int = 10000) -> str:
    """
    Sanitize a string value for safe storage and display.
    
    Args:
        value: Input string
        max_length: Maximum allowed length
    
    Returns:
        Sanitized string
    """
    if value is None:
        return ''
    
    if not isinstance(value, str):
        value = str(value)
    
    # Remove script tags
    value = SCRIPT_PATTERN.sub('', value)
    
    # Remove event handlers
    value = EVENT_HANDLER_PATTERN.sub('', value)
    
    # Remove all HTML tags
    value = HTML_TAG_PATTERN.sub('', value)
    
    # Limit length
    value = value[:max_length]
    
    # Strip whitespace
    value = value.strip()
    
    return value


def sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize all string values in a payload.
    
    Args:
        payload: Dictionary to sanitize
    
    Returns:
        Sanitized dictionary
    """
    if isinstance(payload, dict):
        return {k: sanitize_payload(v) for k, v in payload.items()}
    elif isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    elif isinstance(payload, str):
        return sanitize_string(payload)
    else:
        return payload


# Admin session management
ADMIN_SESSION_DURATION = timedelta(hours=1)


def create_admin_session(username: str, ip_address: str, user_agent: str) -> str:
    """
    Create a new admin session.
    
    Args:
        username: Admin username
        ip_address: Client IP address
        user_agent: Client user agent
    
    Returns:
        Session token
    """
    # Import here to avoid circular import
    from app.models import AdminSession
    
    session_token = secrets.token_urlsafe(32)
    
    admin_session = AdminSession(
        session_token=session_token,
        admin_username=username,
        expires_at=datetime.utcnow() + ADMIN_SESSION_DURATION,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    # Import db here to avoid circular import
    from app import db
    db.session.add(admin_session)
    db.session.commit()
    
    # Store in Flask session
    session['admin_session_token'] = session_token
    session['admin_username'] = username
    session.permanent = True
    
    return session_token


def validate_admin_session(session_token: str = None) -> Optional[Any]:
    """
    Validate the current admin session.
    
    Args:
        session_token: Optional session token to validate. If None, uses session from flask session.
    
    Returns:
        AdminSession if valid, None otherwise
    """
    # Import here to avoid circular import
    from app.models import AdminSession
    from app import db
    
    if session_token is None:
        session_token = session.get('admin_session_token')
    
    if not session_token:
        return None
    
    admin_session = AdminSession.query.filter_by(
        session_token=session_token,
        is_active=True
    ).first()
    
    if not admin_session:
        return None
    
    if admin_session.is_expired():
        admin_session.terminate('expired')
        db.session.commit()
        return None
    
    # Update last activity
    admin_session.last_activity_at = datetime.utcnow()
    db.session.commit()
    
    return admin_session


def terminate_admin_session(reason: str = 'logout'):
    """Terminate the current admin session."""
    # Import here to avoid circular import
    from app.models import AdminSession
    from app import db
    
    session_token = session.get('admin_session_token')
    
    if session_token:
        admin_session = AdminSession.query.filter_by(session_token=session_token).first()
        if admin_session:
            admin_session.terminate(reason)
            db.session.commit()
    
    # Clear Flask session
    session.pop('admin_session_token', None)
    session.pop('admin_username', None)


def admin_required(f):
    """Decorator to require valid admin session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if admin credentials are configured
        admin_user = current_app.config.get('ADMIN_USERNAME', '')
        admin_pass = current_app.config.get('ADMIN_PASSWORD_HASH', '')
        
        if not admin_user or not admin_pass:
            abort(503, 'Admin access is not configured')
        
        # Validate session
        admin_session = validate_admin_session()
        if not admin_session:
            return abort(401, 'Session expired or invalid')
        
        # Store for use in view
        request.admin_session = admin_session
        request.admin_username = admin_session.admin_username
        
        return f(*args, **kwargs)
    return decorated_function


def get_client_ip() -> str:
    """Get the client IP address, handling proxies."""
    # Check for forwarded header (if behind proxy)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # Get first IP in chain
        return forwarded_for.split(',')[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get('X-Real-Ip')
    if real_ip:
        return real_ip
    
    # Fall back to remote address
    return request.remote_addr or 'unknown'


# Abuse prevention
class AbuseDetector:
    """Simple in-memory abuse detection."""
    
    def __init__(self, request_threshold: int = 100, block_duration_minutes: int = 60):
        self._requests: Dict[str, List[Dict]] = {}
        self._blocked_ips: Dict[str, datetime] = {}
        self.request_threshold = request_threshold
        self.block_duration_minutes = block_duration_minutes
    
    def record_request(self, identifier: str):
        """Record a request from an identifier."""
        now = datetime.utcnow()
        
        if identifier not in self._requests:
            self._requests[identifier] = []
        
        self._requests[identifier].append({'timestamp': now})
        
        # Clean old entries (older than 1 hour)
        self.cleanup_old_requests()
        
        # Check if should block (>= threshold to match test expectations)
        if len(self._requests[identifier]) >= self.request_threshold:
            expiry = now + timedelta(minutes=self.block_duration_minutes)
            self._blocked_ips[identifier] = expiry
    
    def record_attempt(self, identifier: str):
        """Alias for record_request for backward compatibility."""
        self.record_request(identifier)
    
    def get_request_count(self, identifier: str) -> int:
        """Get the number of requests from an identifier."""
        if identifier not in self._requests:
            return 0
        return len(self._requests[identifier])
    
    def is_blocked(self, identifier: str) -> bool:
        """Check if identifier is currently blocked."""
        if identifier not in self._blocked_ips:
            return False
        
        expiry = self._blocked_ips[identifier]
        if datetime.utcnow() > expiry:
            # Block has expired
            del self._blocked_ips[identifier]
            return False
        
        return True
    
    def is_abusive(self, identifier: str, threshold: int = None) -> bool:
        """Check if identifier has exceeded abuse threshold."""
        if threshold is None:
            threshold = self.request_threshold
        return self.get_request_count(identifier) > threshold
    
    def cleanup_old_requests(self):
        """Remove old request records."""
        cutoff = datetime.utcnow() - timedelta(hours=1)
        for identifier in list(self._requests.keys()):
            self._requests[identifier] = [
                r for r in self._requests[identifier] if r['timestamp'] > cutoff
            ]
            if not self._requests[identifier]:
                del self._requests[identifier]


abuse_detector = AbuseDetector()


def check_abuse(identifier: str = None) -> bool:
    """
    Check if current request is potentially abusive.
    
    Args:
        identifier: Optional identifier to check (defaults to IP)
    
    Returns:
        True if abusive, False otherwise
    """
    if identifier is None:
        identifier = get_client_ip()
    
    abuse_detector.record_attempt(identifier)
    return abuse_detector.is_abusive(identifier)


# Environment detection
def is_production() -> bool:
    """Check if running in production environment."""
    return current_app.config.get('FLASK_ENV') == 'production'


def is_development() -> bool:
    """Check if running in development environment."""
    return current_app.config.get('FLASK_ENV') == 'development'
