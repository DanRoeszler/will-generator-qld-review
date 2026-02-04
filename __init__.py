"""
Queensland Will Generator Application

A premium, deterministic will generation web application.

Enhanced with:
- CSRF protection
- Rate limiting
- Security headers
- Audit logging
"""

import os
from datetime import datetime
from flask import Flask, request, g
from flask_sqlalchemy import SQLAlchemy

# Initialize extensions
db = SQLAlchemy()


def create_app(test_config=None):
    """Application factory pattern."""
    app = Flask(__name__, instance_relative_config=True)
    
    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///will_generator.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        ADMIN_USERNAME=os.environ.get('ADMIN_USERNAME', ''),
        ADMIN_PASSWORD_HASH=os.environ.get('ADMIN_PASSWORD_HASH', ''),
        SESSION_TYPE='filesystem',
        PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
        
        # CSRF settings
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=3600,  # 1 hour
        WTF_CSRF_SSL_STRICT=False,  # Disabled for development
        
        # Rate limiting settings
        RATELIMIT_STORAGE_URI=os.environ.get('REDIS_URL', 'memory://'),
        RATELIMIT_STRATEGY='fixed-window',
        RATELIMIT_DEFAULT='100 per minute',
        RATELIMIT_HEADERS_ENABLED=True,
        
        # Email settings
        SMTP_HOST=os.environ.get('SMTP_HOST', ''),
        SMTP_PORT=int(os.environ.get('SMTP_PORT', 587)),
        SMTP_USERNAME=os.environ.get('SMTP_USERNAME', ''),
        SMTP_PASSWORD=os.environ.get('SMTP_PASSWORD', ''),
        SMTP_USE_TLS=os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true',
        EMAIL_FROM_ADDRESS=os.environ.get('EMAIL_FROM_ADDRESS', 'wills@example.com'),
        EMAIL_FROM_NAME=os.environ.get('EMAIL_FROM_NAME', 'Will Generator'),
    )
    
    if test_config is None:
        # Load instance config if it exists
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load test config
        app.config.from_mapping(test_config)
    
    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Create PDFs directory
    pdfs_dir = os.path.join(app.instance_path, 'pdfs')
    try:
        os.makedirs(pdfs_dir, exist_ok=True)
    except OSError:
        pass
    
    # Initialize extensions with app
    db.init_app(app)
    
    # Import and initialize security (after db init to avoid circular imports)
    from app.security import csrf, limiter, add_security_headers, init_security
    init_security(app)
    
    # Register blueprints
    from app.routes import main_bp, api_bp, admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    
    # Add security headers to all responses
    @app.after_request
    def after_request(response):
        """Add security headers to all responses."""
        return add_security_headers(response)
    
    # Request logging
    @app.before_request
    def before_request():
        """Log request start."""
        g.request_start_time = datetime.utcnow()
    
    @app.after_request
    def log_request(response):
        """Log request completion."""
        if hasattr(g, 'request_start_time'):
            duration = (datetime.utcnow() - g.request_start_time).total_seconds()
            app.logger.info(
                f'{request.method} {request.path} - {response.status_code} - {duration:.3f}s'
            )
        return response
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create default data retention policy if none exists
        from app.models import DataRetentionPolicy
        if not DataRetentionPolicy.query.first():
            default_policy = DataRetentionPolicy()
            db.session.add(default_policy)
            db.session.commit()
    
    # Template globals
    @app.context_processor
    def inject_globals():
        return {
            'current_year': datetime.utcnow().year,
            'app_name': 'Will Generator'
        }
    
    # Error handlers
    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal errors."""
        db.session.rollback()
        app.logger.error(f'Internal error: {str(error)}')
        return {'ok': False, 'error': 'Internal server error'}, 500
    
    return app
