"""
Database models for the Will Generator application.

Enhanced with:
- Submission versioning and locking
- Generation timestamp for determinism
- Audit trail integration
"""

import json
import hashlib
from datetime import datetime
from enum import Enum as PyEnum
from app import db


class SubmissionStatus(PyEnum):
    """Submission lifecycle states."""
    PENDING = 'pending'
    VALIDATING = 'validating'
    GENERATING = 'generating'
    COMPLETED = 'completed'
    ERROR = 'error'
    LOCKED = 'locked'  # Final state - cannot be modified


class Submission(db.Model):
    """
    Stores will generation submissions with versioning and audit metadata.
    """
    __tablename__ = 'submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Generation timestamp for determinism
    # This is set once at creation and used for all rendering
    generation_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Creation metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.String(500), nullable=False)
    
    # Payload and PDF
    payload_json = db.Column(db.Text, nullable=False)
    pdf_path = db.Column(db.String(500), nullable=True)
    pdf_sha256 = db.Column(db.String(64), nullable=True)
    
    # Execution checklist PDF
    checklist_pdf_path = db.Column(db.String(500), nullable=True)
    checklist_pdf_sha256 = db.Column(db.String(64), nullable=True)
    
    # Status and error tracking
    status = db.Column(db.String(20), default=SubmissionStatus.PENDING.value, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    
    # Locking for immutability
    is_locked = db.Column(db.Boolean, default=False, nullable=False)
    locked_at = db.Column(db.DateTime, nullable=True)
    locked_reason = db.Column(db.String(100), nullable=True)
    
    # Versioning for regeneration
    parent_submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=True)
    version_number = db.Column(db.Integer, default=1, nullable=False)
    
    # Email delivery tracking
    email_sent = db.Column(db.Boolean, default=False, nullable=False)
    email_sent_at = db.Column(db.DateTime, nullable=True)
    email_recipient = db.Column(db.String(254), nullable=True)
    email_error = db.Column(db.Text, nullable=True)
    
    # Relationships
    parent = db.relationship('Submission', remote_side=[id], backref='versions')
    audit_logs = db.relationship('AuditLog', backref='submission', lazy='dynamic')
    
    def __repr__(self):
        return f'<Submission {self.id} v{self.version_number} - {self.status}>'
    
    def to_dict(self):
        """Convert submission to dictionary for API responses."""
        return {
            'id': self.id,
            'version_number': self.version_number,
            'parent_submission_id': self.parent_submission_id,
            'generation_timestamp': self.generation_timestamp.isoformat() if self.generation_timestamp else None,
            'created_at': self.created_at.isoformat(),
            'ip_address': self.ip_address,
            'status': self.status,
            'is_locked': self.is_locked,
            'locked_at': self.locked_at.isoformat() if self.locked_at else None,
            'pdf_sha256': self.pdf_sha256,
            'checklist_pdf_sha256': self.checklist_pdf_sha256,
            'has_pdf': self.pdf_path is not None,
            'has_checklist': self.checklist_pdf_path is not None,
            'email_sent': self.email_sent,
            'email_sent_at': self.email_sent_at.isoformat() if self.email_sent_at else None,
            'error_message': self.error_message
        }
    
    def get_payload(self):
        """Deserialize the JSON payload."""
        return json.loads(self.payload_json)
    
    def set_payload(self, payload):
        """Serialize the payload to JSON with stable ordering."""
        self.payload_json = json.dumps(payload, indent=2, sort_keys=True)
    
    def lock(self, reason='generation_complete'):
        """Lock the submission to prevent modifications."""
        self.is_locked = True
        self.locked_at = datetime.utcnow()
        self.locked_reason = reason
        self.status = SubmissionStatus.LOCKED.value
    
    def can_regenerate(self):
        """Check if this submission can be regenerated."""
        return self.status == SubmissionStatus.COMPLETED.value and self.pdf_path is not None
    
    def create_duplicate(self):
        """Create a new version based on this submission."""
        if not self.is_locked:
            raise ValueError("Cannot duplicate unlocked submission")
        
        new_submission = Submission(
            ip_address=self.ip_address,
            user_agent=self.user_agent,
            payload_json=self.payload_json,
            parent_submission_id=self.id,
            version_number=self.version_number + 1,
            status=SubmissionStatus.PENDING.value
        )
        return new_submission


class AuditLog(db.Model):
    """
    Immutable audit trail for all significant actions.
    
    This table is append-only. Records are never modified or deleted.
    """
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # When the action occurred
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Who performed the action
    actor_type = db.Column(db.String(20), nullable=False)  # 'user', 'admin', 'system'
    actor_id = db.Column(db.String(100), nullable=True)  # IP address, admin username, or None for system
    
    # What was done
    action = db.Column(db.String(50), nullable=False)  # 'submission_created', 'pdf_generated', 'email_sent', etc.
    action_category = db.Column(db.String(20), nullable=False)  # 'create', 'read', 'update', 'delete', 'generate', 'send'
    
    # What was affected
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=True)
    resource_type = db.Column(db.String(50), nullable=False)  # 'submission', 'pdf', 'admin_session', etc.
    resource_id = db.Column(db.String(100), nullable=True)
    
    # Details (structured JSON)
    details_json = db.Column(db.Text, nullable=True)
    
    # Outcome
    success = db.Column(db.Boolean, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    
    # Request context
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    
    # Integrity hash (prevents tampering)
    integrity_hash = db.Column(db.String(64), nullable=False)
    
    def __repr__(self):
        return f'<AuditLog {self.id} - {self.action} by {self.actor_type}>'
    
    def to_dict(self):
        """Convert audit log to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'actor_type': self.actor_type,
            'actor_id': self.actor_id,
            'action': self.action,
            'action_category': self.action_category,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'submission_id': self.submission_id,
            'details': json.loads(self.details_json) if self.details_json else None,
            'success': self.success,
            'error_message': self.error_message
        }
    
    def compute_integrity_hash(self):
        """Compute hash of this record's content for tamper detection."""
        content = f"{self.timestamp}{self.actor_type}{self.actor_id}{self.action}{self.resource_type}{self.resource_id}{self.details_json}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def verify_integrity(self):
        """Verify this record has not been tampered with."""
        return self.integrity_hash == self.compute_integrity_hash()


class AdminSession(db.Model):
    """
    Tracks admin sessions for security auditing.
    """
    __tablename__ = 'admin_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Session metadata
    session_token = db.Column(db.String(64), unique=True, nullable=False)
    admin_username = db.Column(db.String(100), nullable=False)
    
    # Timing
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    last_activity_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    terminated_at = db.Column(db.DateTime, nullable=True)
    termination_reason = db.Column(db.String(100), nullable=True)
    
    # Context
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.String(500), nullable=False)
    
    def __repr__(self):
        return f'<AdminSession {self.id} - {self.admin_username}>'
    
    def is_expired(self):
        """Check if session has expired."""
        return datetime.utcnow() > self.expires_at
    
    def terminate(self, reason='logout'):
        """Terminate this session."""
        self.is_active = False
        self.terminated_at = datetime.utcnow()
        self.termination_reason = reason


class DataRetentionPolicy(db.Model):
    """
    Configuration for data retention policies.
    """
    __tablename__ = 'data_retention_policies'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Policy settings
    retention_days = db.Column(db.Integer, default=2555, nullable=False)  # 7 years default
    auto_delete_enabled = db.Column(db.Boolean, default=False, nullable=False)
    
    # What to delete
    delete_pdfs = db.Column(db.Boolean, default=True, nullable=False)
    delete_payloads = db.Column(db.Boolean, default=False, nullable=False)  # Keep for legal
    delete_audit_logs = db.Column(db.Boolean, default=False, nullable=False)  # Never delete audit logs
    
    # Timing
    last_run_at = db.Column(db.DateTime, nullable=True)
    next_run_at = db.Column(db.DateTime, nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f'<DataRetentionPolicy {self.retention_days} days>'
