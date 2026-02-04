"""
Audit logging module for immutable audit trail.

All significant actions are logged with integrity verification.
This module is append-only - records are never modified or deleted.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from flask import request, current_app

from app import db
from app.models import AuditLog


class AuditAction:
    """Constants for audit actions."""
    # Submission actions
    SUBMISSION_CREATED = 'submission_created'
    SUBMISSION_UPDATED = 'submission_updated'
    SUBMISSION_LOCKED = 'submission_locked'
    SUBMISSION_DUPLICATED = 'submission_duplicated'
    
    # Generation actions
    VALIDATION_STARTED = 'validation_started'
    VALIDATION_PASSED = 'validation_passed'
    VALIDATION_FAILED = 'validation_failed'
    PDF_GENERATED = 'pdf_generated'
    CHECKLIST_GENERATED = 'checklist_generated'
    REGENERATION_STARTED = 'regeneration_started'
    
    # Email actions
    EMAIL_SENT = 'email_sent'
    EMAIL_FAILED = 'email_failed'
    
    # Admin actions
    ADMIN_LOGIN = 'admin_login'
    ADMIN_LOGIN_FAILED = 'admin_login_failed'
    ADMIN_LOGOUT = 'admin_logout'
    ADMIN_SESSION_TERMINATED = 'admin_session_terminated'
    ADMIN_SUBMISSION_VIEWED = 'admin_submission_viewed'
    ADMIN_SUBMISSION_DOWNLOADED = 'admin_submission_downloaded'
    ADMIN_AUDIT_LOG_VIEWED = 'admin_audit_log_viewed'
    
    # System actions
    RETENTION_POLICY_EXECUTED = 'retention_policy_executed'
    ERROR_OCCURRED = 'error_occurred'


class AuditCategory:
    """Constants for audit action categories."""
    CREATE = 'create'
    READ = 'read'
    UPDATE = 'update'
    DELETE = 'delete'
    GENERATE = 'generate'
    SEND = 'send'
    AUTH = 'auth'
    SYSTEM = 'system'


def log_action(
    action: str,
    action_category: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    submission_id: Optional[int] = None,
    actor_type: str = 'system',
    actor_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
    error_message: Optional[str] = None
) -> AuditLog:
    """
    Log an action to the audit trail.
    
    Args:
        action: The action performed (use AuditAction constants)
        action_category: Category of action (use AuditCategory constants)
        resource_type: Type of resource affected
        resource_id: Identifier of the resource
        submission_id: Associated submission ID if applicable
        actor_type: Type of actor ('user', 'admin', 'system')
        actor_id: Identifier of the actor (IP, username, etc.)
        details: Additional structured details
        success: Whether the action succeeded
        error_message: Error message if action failed
    
    Returns:
        The created AuditLog record
    """
    try:
        # Get request context if available
        ip_address = None
        user_agent = None
        
        try:
            if request:
                ip_address = request.remote_addr
                user_agent = request.headers.get('User-Agent')
                
                # Infer actor from request if not provided
                if actor_type == 'user' and not actor_id:
                    actor_id = ip_address
        except RuntimeError:
            # Outside request context
            pass
        
        # Create audit log
        audit_log = AuditLog(
            action=action,
            action_category=action_category,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            submission_id=submission_id,
            actor_type=actor_type,
            actor_id=actor_id,
            details_json=json.dumps(details, sort_keys=True) if details else None,
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Compute integrity hash
        audit_log.integrity_hash = audit_log.compute_integrity_hash()
        
        # Save to database
        db.session.add(audit_log)
        db.session.commit()
        
        return audit_log
    
    except Exception as e:
        # Log to application logger if audit logging fails
        current_app.logger.error(f'Failed to create audit log: {str(e)}')
        # Don't re-raise - audit logging should not break functionality
        return None


def log_submission_created(submission_id: int, ip_address: str, user_agent: str) -> AuditLog:
    """Log submission creation."""
    return log_action(
        action=AuditAction.SUBMISSION_CREATED,
        action_category=AuditCategory.CREATE,
        resource_type='submission',
        resource_id=str(submission_id),
        submission_id=submission_id,
        actor_type='user',
        actor_id=ip_address,
        details={'user_agent': user_agent}
    )


def log_validation_result(submission_id: int, passed: bool, errors: list = None) -> AuditLog:
    """Log validation result."""
    return log_action(
        action=AuditAction.VALIDATION_PASSED if passed else AuditAction.VALIDATION_FAILED,
        action_category=AuditCategory.SYSTEM,
        resource_type='submission',
        resource_id=str(submission_id),
        submission_id=submission_id,
        actor_type='system',
        details={'error_count': len(errors) if errors else 0, 'errors': errors} if errors else None,
        success=passed
    )


def log_pdf_generated(submission_id: int, pdf_hash: str, is_regeneration: bool = False) -> AuditLog:
    """Log PDF generation."""
    return log_action(
        action=AuditAction.REGENERATION_STARTED if is_regeneration else AuditAction.PDF_GENERATED,
        action_category=AuditCategory.GENERATE,
        resource_type='pdf',
        resource_id=pdf_hash[:16],
        submission_id=submission_id,
        actor_type='system',
        details={'pdf_hash': pdf_hash, 'is_regeneration': is_regeneration}
    )


def log_submission_locked(submission_id: int, reason: str = 'generation_complete') -> AuditLog:
    """Log submission locking."""
    return log_action(
        action=AuditAction.SUBMISSION_LOCKED,
        action_category=AuditCategory.UPDATE,
        resource_type='submission',
        resource_id=str(submission_id),
        submission_id=submission_id,
        actor_type='system',
        details={'lock_reason': reason}
    )


def log_email_sent(submission_id: int, recipient: str, success: bool, error: str = None) -> AuditLog:
    """Log email delivery."""
    return log_action(
        action=AuditAction.EMAIL_SENT if success else AuditAction.EMAIL_FAILED,
        action_category=AuditCategory.SEND,
        resource_type='email',
        resource_id=recipient,
        submission_id=submission_id,
        actor_type='system',
        details={'recipient': recipient},
        success=success,
        error_message=error
    )


def log_admin_login(username: str, success: bool, ip_address: str, error: str = None) -> AuditLog:
    """Log admin login attempt."""
    return log_action(
        action=AuditAction.ADMIN_LOGIN if success else AuditAction.ADMIN_LOGIN_FAILED,
        action_category=AuditCategory.AUTH,
        resource_type='admin_session',
        resource_id=username,
        actor_type='admin',
        actor_id=username,
        success=success,
        error_message=error
    )


def log_admin_logout(username: str) -> AuditLog:
    """Log admin logout."""
    return log_action(
        action=AuditAction.ADMIN_LOGOUT,
        action_category=AuditCategory.AUTH,
        resource_type='admin_session',
        resource_id=username,
        actor_type='admin',
        actor_id=username
    )


def log_admin_submission_viewed(submission_id: int, admin_username: str) -> AuditLog:
    """Log admin viewing a submission."""
    return log_action(
        action=AuditAction.ADMIN_SUBMISSION_VIEWED,
        action_category=AuditCategory.READ,
        resource_type='submission',
        resource_id=str(submission_id),
        submission_id=submission_id,
        actor_type='admin',
        actor_id=admin_username
    )


def log_admin_submission_downloaded(submission_id: int, admin_username: str, document_type: str) -> AuditLog:
    """Log admin downloading a submission PDF."""
    return log_action(
        action=AuditAction.ADMIN_SUBMISSION_DOWNLOADED,
        action_category=AuditCategory.READ,
        resource_type=document_type,
        resource_id=str(submission_id),
        submission_id=submission_id,
        actor_type='admin',
        actor_id=admin_username,
        details={'document_type': document_type}
    )


def log_retention_policy_executed(deleted_count: int, errors: list = None) -> AuditLog:
    """Log retention policy execution."""
    return log_action(
        action=AuditAction.RETENTION_POLICY_EXECUTED,
        action_category=AuditCategory.SYSTEM,
        resource_type='retention_policy',
        actor_type='system',
        details={
            'deleted_count': deleted_count,
            'errors': errors
        },
        success=len(errors) == 0 if errors else True
    )


def verify_audit_integrity() -> tuple:
    """
    Verify integrity of all audit log records.
    
    Returns:
        Tuple of (valid_count, invalid_count, invalid_ids)
    """
    logs = AuditLog.query.all()
    valid_count = 0
    invalid_count = 0
    invalid_ids = []
    
    for log in logs:
        if log.verify_integrity():
            valid_count += 1
        else:
            invalid_count += 1
            invalid_ids.append(log.id)
    
    return valid_count, invalid_count, invalid_ids


def get_audit_trail_for_submission(submission_id: int) -> list:
    """
    Get complete audit trail for a submission.
    
    Args:
        submission_id: The submission ID
    
    Returns:
        List of audit log dictionaries
    """
    logs = AuditLog.query.filter_by(submission_id=submission_id) \
                         .order_by(AuditLog.timestamp.asc()) \
                         .all()
    return [log.to_dict() for log in logs]
