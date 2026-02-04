"""
Flask routes for the Will Generator application.

Enhanced with:
- Explainability endpoints
- Email delivery
- Submission regeneration
- Audit log viewing
- CSRF protection
- Rate limiting
"""

import os
import hashlib
import io
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint, render_template, request, jsonify, 
    session, redirect, url_for, flash, send_file,
    current_app, g
)
import werkzeug

from app import db
from app.models import Submission, SubmissionStatus, AuditLog
from app.validation import validate_payload, ValidationResult
from app.context_builder import build_context
from app.clause_renderer import render_document_plan, document_plan_to_dict
from app.pdf_generator import generate_pdf_with_footer, verify_pdf_integrity
from app.execution_checklist import generate_execution_checklist
from app.email_service import EmailService, send_will_email
from app.audit_logger import (
    log_submission_created, log_pdf_generated, log_email_sent,
    log_validation_result, log_admin_login, log_action
)
from app.security import (
    csrf, limiter, sanitize_payload, validate_csrf_token,
    create_admin_session, validate_admin_session, AbuseDetector
)
from app.explainability import (
    generate_will_summary, generate_clause_explainability,
    generate_execution_checklist_summary
)
from app.utils import calculate_sha256


# Create blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Initialize abuse detector
abuse_detector = AbuseDetector()


# Admin authentication decorator
def admin_required(f):
    """Decorator to require admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if admin credentials are configured
        admin_user = current_app.config.get('ADMIN_USERNAME', '')
        admin_pass = current_app.config.get('ADMIN_PASSWORD_HASH', '')
        
        if not admin_user or not admin_pass:
            return render_template('admin_login.html', 
                                 error='Admin access is not configured'), 503
        
        # Check session token
        session_token = session.get('admin_session_token')
        if not session_token or not validate_admin_session(session_token):
            session.pop('admin_logged_in', None)
            session.pop('admin_session_token', None)
            return redirect(url_for('admin.login'))
        
        return f(*args, **kwargs)
    return decorated_function


def verify_admin_password(password: str, password_hash: str) -> bool:
    """Verify admin password against hash."""
    hashed = hashlib.sha256(password.encode()).hexdigest()
    return hashed == password_hash


# Before request handler for abuse detection
@main_bp.before_request
@api_bp.before_request
def check_abuse():
    """Check for potential abuse before processing request."""
    ip_address = request.remote_addr or 'unknown'
    
    # Check if IP is blocked
    if abuse_detector.is_blocked(ip_address):
        return jsonify({
            'ok': False,
            'error': 'Access temporarily restricted due to excessive requests'
        }), 429
    
    # Record this request
    abuse_detector.record_request(ip_address)


# Main routes
@main_bp.route('/')
def index():
    """Render the main will generator form."""
    return render_template('index.html')


# API Routes
@api_bp.route('/validate', methods=['POST'])
@limiter.limit("30 per minute")
def api_validate():
    """
    Validate a will payload.
    
    Returns:
        JSON response with validation result
    """
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({
                'ok': False,
                'errors': [{'field': '', 'message': 'No JSON payload provided', 'code': 'missing_payload'}]
            }), 400
        
        # Sanitize payload
        payload = sanitize_payload(payload)
        
        result = validate_payload(payload)
        
        # Log validation result
        log_validation_result(
            actor_id=request.remote_addr or 'unknown',
            payload=payload,
            result=result,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        if result.is_valid:
            return jsonify({'ok': True, 'errors': [], 'warnings': result.warnings}), 200
        else:
            return jsonify(result.to_dict()), 422
    
    except Exception as e:
        current_app.logger.error(f'Validation error: {str(e)}')
        return jsonify({
            'ok': False,
            'errors': [{'field': '', 'message': 'Internal validation error', 'code': 'internal_error'}]
        }), 500


@api_bp.route('/explain', methods=['POST'])
@limiter.limit("20 per minute")
def api_explain():
    """
    Generate a plain-English explanation of what the will will do.
    
    Returns:
        JSON response with will summary, warnings, and exclusions
    """
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({
                'ok': False,
                'errors': [{'field': '', 'message': 'No JSON payload provided', 'code': 'missing_payload'}]
            }), 400
        
        # Sanitize payload
        payload = sanitize_payload(payload)
        
        # Validate payload (but allow through with warnings)
        result = validate_payload(payload)
        
        # Build context
        context = build_context(payload)
        
        # Generate summary
        summary = generate_will_summary(context)
        
        # Generate clause explainability
        clause_explain = generate_clause_explainability(context)
        
        # Generate execution checklist summary
        execution_summary = generate_execution_checklist_summary(context)
        
        return jsonify({
            'ok': True,
            'summary': summary.to_dict(),
            'clauses': clause_explain,
            'execution': execution_summary,
            'validation': {
                'is_valid': result.is_valid,
                'errors': result.errors if not result.is_valid else [],
                'warnings': result.warnings
            }
        }), 200
    
    except Exception as e:
        current_app.logger.error(f'Explain error: {str(e)}')
        return jsonify({
            'ok': False,
            'errors': [{'field': '', 'message': 'Failed to generate explanation', 'code': 'explain_error'}]
        }), 500


@api_bp.route('/generate', methods=['POST'])
@limiter.limit("10 per minute")
def api_generate():
    """
    Generate a will PDF.
    
    Validates the payload, persists the submission, generates the PDF,
    and returns either the PDF file or JSON response based on Accept header.
    
    Returns:
        PDF file or JSON response
    """
    payload = None
    submission = None
    
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({
                'ok': False,
                'errors': [{'field': '', 'message': 'No JSON payload provided', 'code': 'missing_payload'}]
            }), 400
        
        # Sanitize payload
        payload = sanitize_payload(payload)
        
        # Validate payload
        result = validate_payload(payload)
        if not result.is_valid:
            return jsonify(result.to_dict()), 422
        
        # Create submission record early for determinism
        submission = Submission(
            ip_address=request.remote_addr or 'unknown',
            user_agent=request.headers.get('User-Agent', 'unknown'),
            status=SubmissionStatus.VALIDATING.value,
            email_recipient=payload.get('will_maker', {}).get('email')
        )
        submission.set_payload(payload)
        db.session.add(submission)
        db.session.commit()
        
        # Log submission creation
        log_submission_created(
            submission_id=submission.id,
            actor_id=request.remote_addr or 'unknown',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Update status
        submission.status = SubmissionStatus.GENERATING.value
        db.session.commit()
        
        # Build context
        context = build_context(payload)
        
        # Render document plan
        document_plan = render_document_plan(context)
        
        # Generate PDF with stored timestamp for determinism
        pdf_bytes, pdf_hash = generate_pdf_with_footer(
            context, 
            document_plan,
            generation_timestamp=submission.generation_timestamp
        )
        
        # Save PDF file
        pdf_filename = f'will_{submission.id:08d}_{submission.generation_timestamp.strftime("%Y%m%d_%H%M%S")}.pdf'
        pdf_dir = os.path.join(current_app.instance_path, 'pdfs')
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        
        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        
        submission.pdf_path = pdf_path
        submission.pdf_sha256 = pdf_hash
        
        # Generate execution checklist PDF
        checklist_bytes, checklist_hash = generate_execution_checklist(
            context,
            generation_timestamp=submission.generation_timestamp
        )
        
        checklist_filename = f'checklist_{submission.id:08d}_{submission.generation_timestamp.strftime("%Y%m%d_%H%M%S")}.pdf'
        checklist_path = os.path.join(pdf_dir, checklist_filename)
        
        with open(checklist_path, 'wb') as f:
            f.write(checklist_bytes)
        
        submission.checklist_pdf_path = checklist_path
        submission.checklist_pdf_sha256 = checklist_hash
        
        # Lock the submission
        submission.lock(reason='generation_complete')
        
        # Update status
        submission.status = SubmissionStatus.COMPLETED.value
        db.session.commit()
        
        # Log PDF generation
        log_pdf_generated(
            submission_id=submission.id,
            actor_id=request.remote_addr or 'unknown',
            pdf_hash=pdf_hash,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Check Accept header
        accept_header = request.headers.get('Accept', '')
        
        if 'application/json' in accept_header:
            # Return JSON response
            return jsonify({
                'ok': True,
                'submission_id': submission.id,
                'download_url': f'/api/download/{submission.id}',
                'checklist_url': f'/api/checklist/{submission.id}',
                'pdf_hash': pdf_hash,
                'message': 'Will generated successfully'
            }), 200
        else:
            # Return PDF file
            return send_file(
                io.BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'Last_Will_and_Testament.pdf'
            )
    
    except Exception as e:
        current_app.logger.error(f'Generation error: {str(e)}')
        
        # Update submission with error
        if submission:
            try:
                submission.status = SubmissionStatus.ERROR.value
                submission.error_message = str(e)
                db.session.commit()
            except Exception as db_error:
                current_app.logger.error(f'Failed to update error status: {str(db_error)}')
        else:
            # Create error submission record
            try:
                error_submission = Submission(
                    ip_address=request.remote_addr or 'unknown',
                    user_agent=request.headers.get('User-Agent', 'unknown'),
                    status=SubmissionStatus.ERROR.value,
                    error_message=str(e)
                )
                if payload:
                    error_submission.set_payload(payload)
                db.session.add(error_submission)
                db.session.commit()
            except Exception as db_error:
                current_app.logger.error(f'Failed to log error: {str(db_error)}')
        
        return jsonify({
            'ok': False,
            'errors': [{'field': '', 'message': 'Failed to generate will', 'code': 'generation_error'}]
        }), 500


@api_bp.route('/regenerate/<int:submission_id>', methods=['POST'])
@limiter.limit("5 per minute")
def api_regenerate(submission_id: int):
    """
    Regenerate a will from a locked submission.
    
    Creates a new version of the submission with the same payload
    but generates a new PDF (useful for template updates).
    
    Args:
        submission_id: The original submission ID
        
    Returns:
        JSON response with new submission details
    """
    try:
        original = Submission.query.get_or_404(submission_id)
        
        # Check if can regenerate
        if not original.can_regenerate():
            return jsonify({
                'ok': False,
                'error': 'Submission cannot be regenerated (not completed or no PDF)'
            }), 400
        
        # Create new version
        new_submission = original.create_duplicate()
        new_submission.ip_address = request.remote_addr or 'unknown'
        new_submission.user_agent = request.headers.get('User-Agent', 'unknown')
        
        db.session.add(new_submission)
        db.session.commit()
        
        # Log regeneration
        log_action(
            action='submission_regenerated',
            action_category='create',
            actor_type='user',
            actor_id=request.remote_addr or 'unknown',
            submission_id=new_submission.id,
            resource_type='submission',
            resource_id=str(new_submission.id),
            details={
                'parent_submission_id': submission_id,
                'version_number': new_submission.version_number
            },
            success=True,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Get payload and generate
        payload = new_submission.get_payload()
        
        # Build context
        context = build_context(payload)
        
        # Render document plan
        document_plan = render_document_plan(context)
        
        # Generate PDF
        pdf_bytes, pdf_hash = generate_pdf_with_footer(
            context, 
            document_plan,
            generation_timestamp=new_submission.generation_timestamp
        )
        
        # Save PDF file
        pdf_filename = f'will_{new_submission.id:08d}_{new_submission.generation_timestamp.strftime("%Y%m%d_%H%M%S")}.pdf'
        pdf_dir = os.path.join(current_app.instance_path, 'pdfs')
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        
        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        
        new_submission.pdf_path = pdf_path
        new_submission.pdf_sha256 = pdf_hash
        
        # Generate checklist
        checklist_bytes, checklist_hash = generate_execution_checklist(
            context,
            generation_timestamp=new_submission.generation_timestamp
        )
        
        checklist_filename = f'checklist_{new_submission.id:08d}_{new_submission.generation_timestamp.strftime("%Y%m%d_%H%M%S")}.pdf'
        checklist_path = os.path.join(pdf_dir, checklist_filename)
        
        with open(checklist_path, 'wb') as f:
            f.write(checklist_bytes)
        
        new_submission.checklist_pdf_path = checklist_path
        new_submission.checklist_pdf_sha256 = checklist_hash
        
        # Lock and complete
        new_submission.lock(reason='regeneration_complete')
        new_submission.status = SubmissionStatus.COMPLETED.value
        db.session.commit()
        
        # Log PDF generation
        log_pdf_generated(
            submission_id=new_submission.id,
            actor_id=request.remote_addr or 'unknown',
            pdf_hash=pdf_hash,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'ok': True,
            'submission_id': new_submission.id,
            'parent_submission_id': submission_id,
            'version_number': new_submission.version_number,
            'download_url': f'/api/download/{new_submission.id}',
            'checklist_url': f'/api/checklist/{new_submission.id}',
            'pdf_hash': pdf_hash,
            'message': 'Will regenerated successfully'
        }), 200
    
    except Exception as e:
        current_app.logger.error(f'Regeneration error: {str(e)}')
        return jsonify({
            'ok': False,
            'error': 'Failed to regenerate will'
        }), 500


@api_bp.route('/email/<int:submission_id>', methods=['POST'])
@limiter.limit("3 per minute")
def api_email(submission_id: int):
    """
    Email the will PDF to the will maker.
    
    Args:
        submission_id: The submission ID
        
    Returns:
        JSON response with email status
    """
    try:
        submission = Submission.query.get_or_404(submission_id)
        
        # Check if PDF exists
        if not submission.pdf_path or not os.path.exists(submission.pdf_path):
            return jsonify({
                'ok': False,
                'error': 'PDF not found for this submission'
            }), 404
        
        # Get recipient email
        data = request.get_json() or {}
        recipient = data.get('email') or submission.email_recipient
        
        if not recipient:
            return jsonify({
                'ok': False,
                'error': 'No email address provided or stored'
            }), 400
        
        # Initialize email service
        email_service = EmailService()
        
        # Get will maker name from payload
        payload = submission.get_payload()
        will_maker_name = payload.get('will_maker', {}).get('full_name', 'Valued Client')
        
        # Send email
        success, error = send_will_email(
            email_service=email_service,
            recipient_email=recipient,
            recipient_name=will_maker_name,
            will_pdf_path=submission.pdf_path,
            checklist_pdf_path=submission.checklist_pdf_path,
            submission_id=submission.id
        )
        
        if success:
            # Update submission
            submission.email_sent = True
            submission.email_sent_at = datetime.utcnow()
            submission.email_recipient = recipient
            db.session.commit()
            
            # Log email sent
            log_email_sent(
                submission_id=submission.id,
                actor_id=request.remote_addr or 'unknown',
                recipient=recipient,
                success=True,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            return jsonify({
                'ok': True,
                'message': f'Will emailed successfully to {recipient}',
                'recipient': recipient,
                'sent_at': submission.email_sent_at.isoformat()
            }), 200
        else:
            # Log email failure
            log_email_sent(
                submission_id=submission.id,
                actor_id=request.remote_addr or 'unknown',
                recipient=recipient,
                success=False,
                error_message=error,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            submission.email_error = error
            db.session.commit()
            
            return jsonify({
                'ok': False,
                'error': f'Failed to send email: {error}'
            }), 500
    
    except Exception as e:
        current_app.logger.error(f'Email error: {str(e)}')
        return jsonify({
            'ok': False,
            'error': 'Failed to send email'
        }), 500


@api_bp.route('/download/<int:submission_id>')
@limiter.limit("30 per minute")
def api_download(submission_id: int):
    """
    Download a generated PDF by submission ID.
    
    Args:
        submission_id: The submission ID
    
    Returns:
        PDF file
    """
    submission = Submission.query.get_or_404(submission_id)
    
    if not submission.pdf_path or not os.path.exists(submission.pdf_path):
        return jsonify({
            'ok': False,
            'error': 'PDF not found'
        }), 404
    
    # Verify integrity
    try:
        with open(submission.pdf_path, 'rb') as f:
            current_hash = calculate_sha256(f.read())
        
        if current_hash != submission.pdf_sha256:
            current_app.logger.error(f'PDF integrity check failed for submission {submission_id}')
            return jsonify({
                'ok': False,
                'error': 'PDF integrity check failed'
            }), 500
    except Exception as e:
        current_app.logger.error(f'Integrity check error: {str(e)}')
    
    return send_file(
        submission.pdf_path,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'Last_Will_and_Testament_{submission.id}.pdf'
    )


@api_bp.route('/checklist/<int:submission_id>')
@limiter.limit("30 per minute")
def api_checklist(submission_id: int):
    """
    Download the execution checklist PDF by submission ID.
    
    Args:
        submission_id: The submission ID
    
    Returns:
        PDF file
    """
    submission = Submission.query.get_or_404(submission_id)
    
    if not submission.checklist_pdf_path or not os.path.exists(submission.checklist_pdf_path):
        return jsonify({
            'ok': False,
            'error': 'Checklist PDF not found'
        }), 404
    
    return send_file(
        submission.checklist_pdf_path,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'Will_Execution_Checklist_{submission.id}.pdf'
    )


@api_bp.route('/verify/<int:submission_id>')
def api_verify(submission_id: int):
    """
    Verify the integrity of a generated PDF.
    
    Args:
        submission_id: The submission ID
        
    Returns:
        JSON response with verification result
    """
    submission = Submission.query.get_or_404(submission_id)
    
    if not submission.pdf_path or not os.path.exists(submission.pdf_path):
        return jsonify({
            'ok': False,
            'error': 'PDF not found'
        }), 404
    
    try:
        with open(submission.pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        current_hash = calculate_sha256(pdf_bytes)
        is_valid = current_hash == submission.pdf_sha256
        
        return jsonify({
            'ok': True,
            'submission_id': submission_id,
            'is_valid': is_valid,
            'stored_hash': submission.pdf_sha256,
            'current_hash': current_hash,
            'message': 'PDF integrity verified' if is_valid else 'PDF has been modified'
        }), 200
    
    except Exception as e:
        current_app.logger.error(f'Verification error: {str(e)}')
        return jsonify({
            'ok': False,
            'error': 'Failed to verify PDF'
        }), 500


# Admin routes
@admin_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """Admin login page."""
    # Check if admin is configured
    admin_user = current_app.config.get('ADMIN_USERNAME', '')
    admin_pass = current_app.config.get('ADMIN_PASSWORD_HASH', '')
    
    if not admin_user or not admin_pass:
        return render_template('admin_login.html', 
                             error='Admin access is not configured'), 503
    
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if username == admin_user and verify_admin_password(password, admin_pass):
            # Create secure session
            session_token = create_admin_session(
                username=username,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', 'unknown')
            )
            
            session['admin_logged_in'] = True
            session['admin_session_token'] = session_token
            session.permanent = True
            
            # Log login
            log_admin_login(
                username=username,
                success=True,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            return redirect(url_for('admin.list_submissions'))
        else:
            # Log failed login
            log_admin_login(
                username=username,
                success=False,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            flash('Invalid username or password', 'error')
    
    return render_template('admin_login.html')


@admin_bp.route('/logout')
def logout():
    """Admin logout."""
    session_token = session.get('admin_session_token')
    if session_token:
        # Terminate session in database
        from app.security import terminate_admin_session
        terminate_admin_session(session_token, reason='logout')
    
    session.pop('admin_logged_in', None)
    session.pop('admin_session_token', None)
    return redirect(url_for('admin.login'))


@admin_bp.route('/submissions')
@admin_required
def list_submissions():
    """List all submissions with pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status_filter = request.args.get('status', '')
    
    # Limit per_page
    per_page = min(per_page, 100)
    
    query = Submission.query
    
    if status_filter:
        query = query.filter(Submission.status == status_filter)
    
    pagination = query.order_by(Submission.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin_list.html', 
                         submissions=pagination.items,
                         pagination=pagination,
                         status_filter=status_filter)


@admin_bp.route('/submissions/<int:submission_id>')
@admin_required
def view_submission(submission_id: int):
    """View a single submission."""
    submission = Submission.query.get_or_404(submission_id)
    
    # Get payload for display
    payload = submission.get_payload()
    
    # Get audit logs for this submission
    audit_logs = AuditLog.query.filter_by(submission_id=submission_id).order_by(AuditLog.timestamp.desc()).all()
    
    return render_template('admin_detail.html',
                         submission=submission,
                         payload=payload,
                         audit_logs=audit_logs)


@admin_bp.route('/submissions/<int:submission_id>/pdf')
@admin_required
def download_submission_pdf(submission_id: int):
    """Download PDF for a submission."""
    submission = Submission.query.get_or_404(submission_id)
    
    if not submission.pdf_path or not os.path.exists(submission.pdf_path):
        flash('PDF not found for this submission', 'error')
        return redirect(url_for('admin.view_submission', submission_id=submission_id))
    
    return send_file(
        submission.pdf_path,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'will_submission_{submission.id}.pdf'
    )


@admin_bp.route('/audit-logs')
@admin_required
def list_audit_logs():
    """List audit logs with pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    action_filter = request.args.get('action', '')
    
    per_page = min(per_page, 100)
    
    query = AuditLog.query
    
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    
    pagination = query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get unique actions for filter
    actions = db.session.query(AuditLog.action).distinct().all()
    actions = [a[0] for a in actions]
    
    return render_template('admin_audit_logs.html',
                         audit_logs=pagination.items,
                         pagination=pagination,
                         actions=actions,
                         action_filter=action_filter)


@admin_bp.route('/stats')
@admin_required
def admin_stats():
    """View system statistics."""
    from sqlalchemy import func
    
    # Submission stats
    total_submissions = Submission.query.count()
    completed_submissions = Submission.query.filter_by(status=SubmissionStatus.COMPLETED.value).count()
    error_submissions = Submission.query.filter_by(status=SubmissionStatus.ERROR.value).count()
    locked_submissions = Submission.query.filter_by(is_locked=True).count()
    
    # Email stats
    emails_sent = Submission.query.filter_by(email_sent=True).count()
    
    # Recent activity (last 24 hours)
    from datetime import timedelta
    day_ago = datetime.utcnow() - timedelta(days=1)
    recent_submissions = Submission.query.filter(Submission.created_at >= day_ago).count()
    
    # Audit log stats
    total_audit_logs = AuditLog.query.count()
    failed_actions = AuditLog.query.filter_by(success=False).count()
    
    stats = {
        'submissions': {
            'total': total_submissions,
            'completed': completed_submissions,
            'error': error_submissions,
            'locked': locked_submissions,
            'recent_24h': recent_submissions
        },
        'emails': {
            'sent': emails_sent
        },
        'audit': {
            'total_logs': total_audit_logs,
            'failed_actions': failed_actions
        }
    }
    
    return render_template('admin_stats.html', stats=stats)


# Error handlers
@main_bp.errorhandler(404)
@api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    return render_template('base.html', error='Page not found'), 404


@main_bp.errorhandler(500)
@api_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    db.session.rollback()
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'ok': False, 'error': 'Internal server error'}), 500
    return render_template('base.html', error='Internal server error'), 500


@main_bp.errorhandler(429)
@api_bp.errorhandler(429)
def rate_limit_handler(error):
    """Handle rate limit errors."""
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({
            'ok': False,
            'error': 'Rate limit exceeded. Please try again later.'
        }), 429
    return render_template('base.html', error='Too many requests. Please try again later.'), 429
