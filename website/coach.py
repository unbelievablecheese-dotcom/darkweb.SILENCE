import os
import smtplib
import time
from email.message import EmailMessage
from urllib.parse import urlparse

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import generate_password_hash

from . import db
from .models import CoachRequest, User

coach = Blueprint('coach', __name__)
APPROVAL_EMAIL = 'unbelievablecheese@gmail.com'
TOKEN_MAX_AGE = 7 * 24 * 60 * 60


def mail_configuration():
    host = os.environ.get('SMTP_HOST', '').strip()
    username = os.environ.get('SMTP_USERNAME', '').strip()
    password = os.environ.get('SMTP_PASSWORD', '')
    sender = os.environ.get('SMTP_FROM', username).strip()
    base_url = os.environ.get('PUBLIC_BASE_URL', '').strip().rstrip('/')
    parsed_base_url = urlparse(base_url)
    if (
        not host
        or not username
        or not password
        or not sender
        or parsed_base_url.scheme != 'https'
        or not parsed_base_url.netloc
        or parsed_base_url.path not in ('', '/')
        or parsed_base_url.query
        or parsed_base_url.fragment
        or parsed_base_url.username is not None
        or parsed_base_url.password is not None
    ):
        return None
    return host, username, password, sender, base_url


def approval_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='silence-coach-approval-v1')


def send_approval_email(coach_request):
    configuration = mail_configuration()
    if configuration is None:
        raise RuntimeError('Coach approval email settings are incomplete.')

    host, username, password, sender, base_url = configuration
    token = approval_serializer().dumps({'request_id': coach_request.id})
    approval_url = f"{base_url}{url_for('coach.approve_request', token=token)}"

    message = EmailMessage()
    message['Subject'] = 'SILENCE coach account approval requested'
    message['From'] = sender
    message['To'] = APPROVAL_EMAIL
    message.set_content(
        f"A coach account is awaiting your approval.\n\n"
        f"Name: {coach_request.user.first_name}\n"
        f"Email: {coach_request.user.email}\n\n"
        "Review the request using this secure link. Opening the link will not approve it; "
        "you must click APPROVE on the page. The link expires in 7 days.\n\n"
        f"{approval_url}\n\n"
        "If you did not expect this request, ignore this email."
    )

    port = int(os.environ.get('SMTP_PORT', '587'))
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15) as server:
            server.login(username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(username, password)
            server.send_message(message)
    coach_request.last_email_sent_at = int(time.time())
    db.session.commit()


def pending_request_from_token(token):
    try:
        payload = approval_serializer().loads(token, max_age=TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get('request_id'), int):
        return None
    coach_request = db.session.get(CoachRequest, payload['request_id'])
    if coach_request is None or coach_request.status != 'pending':
        return None
    return coach_request


def register_coach_account():
    email = request.form.get('email', '').strip().lower()
    first_name = request.form.get('firstName', '').strip()
    password1 = request.form.get('password1', '')
    password2 = request.form.get('password2', '')

    existing_user = db.session.scalar(db.select(User).where(User.email == email)) if email else None
    if existing_user:
        flash('An account with that email already exists. Sign in to that account before requesting coach access.', category='error')
    elif not email or len(email) > 150 or '@' not in email or email.startswith('@') or email.endswith('@'):
        flash('Enter a valid email address.', category='error')
    elif not first_name or len(first_name) > 150:
        flash('Enter a name (up to 150 characters).', category='error')
    elif password1 != password2:
        flash("Passwords don't match.", category='error')
    elif len(password1) < 7:
        flash('Password must be at least 7 characters.', category='error')
    else:
        account = User(
            email=email,
            first_name=first_name,
            password=generate_password_hash(password1),
        )
        db.session.add(account)
        db.session.flush()
        coach_request = CoachRequest(user_id=account.id)
        db.session.add(coach_request)
        db.session.commit()
        login_user(account, remember=True)

        try:
            send_approval_email(coach_request)
        except (OSError, smtplib.SMTPException, RuntimeError, ValueError):
            current_app.logger.exception('Could not email the SILENCE coach approval request')
            flash(
                'Your account and coach request were saved, but the approval email could not be sent. '
                'Check mail configuration or use the resend option.',
                category='error',
            )
        else:
            flash('Coach request submitted. You will receive coach access after owner approval.', category='success')
        return redirect(url_for('coach.request_status'))

    return None


@coach.route('/coach-sign-up', methods=['GET', 'POST'])
def sign_up():
    if current_user.is_authenticated:
        flash('Sign out before creating another account.', category='error')
        return redirect(url_for('views.home'))

    mail_ready = mail_configuration() is not None
    if request.method == 'POST':
        if not mail_ready:
            flash('Coach applications are temporarily unavailable because approval email is not configured.', category='error')
        else:
            response = register_coach_account()
            if response is not None:
                return response
    return render_template(
        'sign_up.html',
        user=current_user,
        coach_mode=True,
        coach_signup_unavailable=not mail_ready,
    ), 503 if not mail_ready else 200


@coach.route('/coach-request/status')
@login_required
def request_status():
    coach_request = db.session.scalar(
        db.select(CoachRequest).where(CoachRequest.user_id == current_user.id)
    )
    if coach_request is None:
        abort(404)
    return render_template(
        'coach_request_status.html',
        user=current_user,
        coach_request=coach_request,
        mail_ready=mail_configuration() is not None,
    )


@coach.route('/coach-request/resend', methods=['POST'])
@login_required
def resend_request_email():
    coach_request = db.session.scalar(
        db.select(CoachRequest).where(CoachRequest.user_id == current_user.id)
    )
    if coach_request is None:
        abort(404)
    if coach_request.status != 'pending':
        flash('This coach request is no longer awaiting approval.', category='error')
        return redirect(url_for('coach.request_status'))
    if coach_request.last_email_sent_at and time.time() - coach_request.last_email_sent_at < 300:
        flash('An approval email was sent recently. Please wait five minutes before requesting another.', category='error')
        return redirect(url_for('coach.request_status'))
    try:
        send_approval_email(coach_request)
    except (OSError, smtplib.SMTPException, RuntimeError, ValueError):
        current_app.logger.exception('Could not resend the SILENCE coach approval request')
        flash('The approval email could not be sent. Check mail settings and try again.', category='error')
    else:
        flash('A new approval email was sent to the site owner.', category='success')
    return redirect(url_for('coach.request_status'))


@coach.route('/coach-approval/<token>', methods=['GET', 'POST'])
def approve_request(token):
    coach_request = pending_request_from_token(token)
    if coach_request is None:
        return render_template('coach_approval.html', user=current_user, coach_request=None), 410
    if request.method == 'POST':
        coach_request.status = 'approved'
        db.session.commit()
    return render_template('coach_approval.html', user=current_user, coach_request=coach_request)
