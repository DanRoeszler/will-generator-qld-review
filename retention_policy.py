"""
Data Retention Policy Module

Manages data retention and automatic deletion of old submissions
according to configurable policies.

This module ensures compliance with privacy requirements while
maintaining audit trails for legal purposes.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from sqlalchemy import and_

from app import db
from app.models import Submission, AuditLog, DataRetentionPolicy, AdminSession
from app.audit_logger import log_action


def get_active_policy() -> DataRetentionPolicy:
    """
    Get the currently active retention policy.
    
    Returns:
        The active DataRetentionPolicy, or default if none configured
    """
    policy = DataRetentionPolicy.query.filter_by(is_active=True).first()
    if not policy:
        # Create default policy
        policy = DataRetentionPolicy()
        db.session.add(policy)
        db.session.commit()
    return policy


def calculate_retention_date(policy: DataRetentionPolicy = None) -> datetime:
    """
    Calculate the cutoff date for data retention.
    
    Args:
        policy: The retention policy to use (defaults to active policy)
        
    Returns:
        Datetime before which data should be deleted
    """
    if policy is None:
        policy = get_active_policy()
    
    retention_days = policy.retention_days
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    return cutoff_date


def find_submissions_for_deletion(policy: DataRetentionPolicy = None) -> List[Submission]:
    """
    Find submissions that are eligible for deletion based on retention policy.
    
    Args:
        policy: The retention policy to use
        
    Returns:
        List of submissions eligible for deletion
    """
    if policy is None:
        policy = get_active_policy()
    
    cutoff_date = calculate_retention_date(policy)
    
    # Find submissions older than retention period
    # Only delete completed/locked submissions
    query = Submission.query.filter(
        and_(
            Submission.created_at < cutoff_date,
            Submission.status.in_(['completed', 'locked'])
        )
    )
    
    # Exclude submissions with versions (keep parent records)
    query = query.filter(Submission.parent_submission_id.is_(None))
    
    return query.all()


def delete_submission_pdf(submission: Submission, dry_run: bool = False) -> bool:
    """
    Delete the PDF file for a submission.
    
    Args:
        submission: The submission to delete PDF for
        dry_run: If True, don't actually delete
        
    Returns:
        True if PDF was deleted or doesn't exist
    """
    if submission.pdf_path and os.path.exists(submission.pdf_path):
        if not dry_run:
            try:
                os.remove(submission.pdf_path)
                submission.pdf_path = None
                return True
            except OSError as e:
                # Log error but don't fail
                from flask import current_app
                current_app.logger.error(f'Failed to delete PDF for submission {submission.id}: {e}')
                return False
    return True


def delete_checklist_pdf(submission: Submission, dry_run: bool = False) -> bool:
    """
    Delete the checklist PDF file for a submission.
    
    Args:
        submission: The submission to delete checklist for
        dry_run: If True, don't actually delete
        
    Returns:
        True if checklist was deleted or doesn't exist
    """
    if submission.checklist_pdf_path and os.path.exists(submission.checklist_pdf_path):
        if not dry_run:
            try:
                os.remove(submission.checklist_pdf_path)
                submission.checklist_pdf_path = None
                return True
            except OSError as e:
                from flask import current_app
                current_app.logger.error(f'Failed to delete checklist for submission {submission.id}: {e}')
                return False
    return True


def apply_retention_policy(dry_run: bool = False, actor_id: str = 'system') -> Dict[str, Any]:
    """
    Apply the data retention policy, deleting old data as configured.
    
    Args:
        dry_run: If True, only report what would be deleted
        actor_id: Who initiated the retention run
        
    Returns:
        Dictionary with deletion statistics
    """
    policy = get_active_policy()
    
    if not policy.auto_delete_enabled and not dry_run:
        return {
            'executed': False,
            'reason': 'Auto-delete is disabled',
            'policy': {
                'retention_days': policy.retention_days,
                'auto_delete_enabled': policy.auto_delete_enabled
            }
        }
    
    submissions = find_submissions_for_deletion(policy)
    
    stats = {
        'dry_run': dry_run,
        'policy': {
            'retention_days': policy.retention_days,
            'auto_delete_enabled': policy.auto_delete_enabled,
            'delete_pdfs': policy.delete_pdfs,
            'delete_payloads': policy.delete_payloads,
        },
        'cutoff_date': calculate_retention_date(policy).isoformat(),
        'submissions_found': len(submissions),
        'pdfs_deleted': 0,
        'checklists_deleted': 0,
        'payloads_deleted': 0,
        'errors': []
    }
    
    for submission in submissions:
        submission_stats = {
            'submission_id': submission.id,
            'created_at': submission.created_at.isoformat(),
            'actions': []
        }
        
        # Delete PDF if configured
        if policy.delete_pdfs:
            if submission.pdf_path:
                if delete_submission_pdf(submission, dry_run):
                    stats['pdfs_deleted'] += 1
                    submission_stats['actions'].append('pdf_deleted')
                else:
                    stats['errors'].append(f'Failed to delete PDF for submission {submission.id}')
            
            if submission.checklist_pdf_path:
                if delete_checklist_pdf(submission, dry_run):
                    stats['checklists_deleted'] += 1
                    submission_stats['actions'].append('checklist_deleted')
                else:
                    stats['errors'].append(f'Failed to delete checklist for submission {submission.id}')
        
        # Delete payload if configured
        if policy.delete_payloads:
            if not dry_run:
                submission.payload_json = '{}'
            stats['payloads_deleted'] += 1
            submission_stats['actions'].append('payload_deleted')
        
        # Log the deletion action
        if not dry_run and submission_stats['actions']:
            log_action(
                action='data_retention_deletion',
                action_category='delete',
                actor_type='system',
                actor_id=actor_id,
                submission_id=submission.id,
                resource_type='submission',
                resource_id=str(submission.id),
                details={
                    'actions': submission_stats['actions'],
                    'retention_days': policy.retention_days
                },
                success=True
            )
    
    if not dry_run:
        # Update policy last run time
        policy.last_run_at = datetime.utcnow()
        policy.next_run_at = datetime.utcnow() + timedelta(days=1)
        db.session.commit()
    
    return stats


def clean_expired_admin_sessions(dry_run: bool = False) -> int:
    """
    Clean up expired admin sessions.
    
    Args:
        dry_run: If True, only count without deleting
        
    Returns:
        Number of sessions cleaned
    """
    expired_sessions = AdminSession.query.filter(
        and_(
            AdminSession.is_active == True,
            AdminSession.expires_at < datetime.utcnow()
        )
    ).all()
    
    count = 0
    for session in expired_sessions:
        if not dry_run:
            session.terminate(reason='expired')
        count += 1
    
    if not dry_run and count > 0:
        db.session.commit()
        
        # Log the cleanup
        log_action(
            action='admin_session_cleanup',
            action_category='delete',
            actor_type='system',
            actor_id='system',
            resource_type='admin_session',
            resource_id='multiple',
            details={'count': count},
            success=True
        )
    
    return count


def get_retention_summary() -> Dict[str, Any]:
    """
    Get a summary of current data retention status.
    
    Returns:
        Dictionary with retention statistics
    """
    policy = get_active_policy()
    cutoff_date = calculate_retention_date(policy)
    
    # Count submissions by age
    total_submissions = Submission.query.count()
    old_submissions = Submission.query.filter(Submission.created_at < cutoff_date).count()
    locked_submissions = Submission.query.filter_by(is_locked=True).count()
    
    # Count by status
    from sqlalchemy import func
    status_counts = db.session.query(
        Submission.status,
        func.count(Submission.id)
    ).group_by(Submission.status).all()
    
    # Count storage
    pdf_count = Submission.query.filter(Submission.pdf_path.isnot(None)).count()
    checklist_count = Submission.query.filter(Submission.checklist_pdf_path.isnot(None)).count()
    
    return {
        'policy': {
            'retention_days': policy.retention_days,
            'auto_delete_enabled': policy.auto_delete_enabled,
            'delete_pdfs': policy.delete_pdfs,
            'delete_payloads': policy.delete_payloads,
            'last_run_at': policy.last_run_at.isoformat() if policy.last_run_at else None,
            'next_run_at': policy.next_run_at.isoformat() if policy.next_run_at else None,
        },
        'submissions': {
            'total': total_submissions,
            'older_than_retention': old_submissions,
            'locked': locked_submissions,
            'by_status': {status: count for status, count in status_counts}
        },
        'storage': {
            'pdfs_stored': pdf_count,
            'checklists_stored': checklist_count
        },
        'retention_cutoff': cutoff_date.isoformat()
    }


def update_retention_policy(
    retention_days: int = None,
    auto_delete_enabled: bool = None,
    delete_pdfs: bool = None,
    delete_payloads: bool = None,
    actor_id: str = 'system'
) -> DataRetentionPolicy:
    """
    Update the active retention policy.
    
    Args:
        retention_days: New retention period in days
        auto_delete_enabled: Whether auto-delete is enabled
        delete_pdfs: Whether to delete PDFs
        delete_payloads: Whether to delete payloads
        actor_id: Who made the change
        
    Returns:
        The updated policy
    """
    policy = get_active_policy()
    
    old_values = {
        'retention_days': policy.retention_days,
        'auto_delete_enabled': policy.auto_delete_enabled,
        'delete_pdfs': policy.delete_pdfs,
        'delete_payloads': policy.delete_payloads
    }
    
    if retention_days is not None:
        policy.retention_days = retention_days
    if auto_delete_enabled is not None:
        policy.auto_delete_enabled = auto_delete_enabled
    if delete_pdfs is not None:
        policy.delete_pdfs = delete_pdfs
    if delete_payloads is not None:
        policy.delete_payloads = delete_payloads
    
    db.session.commit()
    
    # Log the change
    log_action(
        action='retention_policy_updated',
        action_category='update',
        actor_type='admin',
        actor_id=actor_id,
        resource_type='data_retention_policy',
        resource_id=str(policy.id),
        details={
            'old_values': old_values,
            'new_values': {
                'retention_days': policy.retention_days,
                'auto_delete_enabled': policy.auto_delete_enabled,
                'delete_pdfs': policy.delete_pdfs,
                'delete_payloads': policy.delete_payloads
            }
        },
        success=True
    )
    
    return policy
