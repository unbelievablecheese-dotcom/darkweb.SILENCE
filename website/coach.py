import os
import smtplib
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from urllib.parse import urlparse

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import generate_password_hash

from . import db
from .models import Announcement, CoachRequest, PlayerProfile, ScheduledMatch, User
from .views import PLAYER_ROSTER, is_coach

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


@coach.route('/coach/updates', methods=['GET', 'POST'])
@login_required
def updates():
    if not is_coach(current_user):
        abort(403)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'announcement':
            title = request.form.get('title', '').strip()
            body = request.form.get('body', '').strip()
            if not title or len(title) > 120 or not body or len(body) > 2000:
                flash('Add an announcement title and body within the stated limits.', category='error')
            else:
                db.session.add(Announcement(title=title, body=body))
                db.session.commit()
                flash('Announcement published.', category='success')
                return redirect(url_for('coach.updates'))
        elif action == 'match':
            opponent = request.form.get('opponent', '').strip()
            event = request.form.get('event', '').strip()
            kickoff = request.form.get('starts_at', '').strip()
            stream_url = request.form.get('stream_url', '').strip()
            try:
                starts_at = datetime.fromisoformat(kickoff)
                if starts_at.tzinfo is None:
                    starts_at = starts_at.replace(tzinfo=timezone.utc)
            except ValueError:
                starts_at = None
            parsed_stream = urlparse(stream_url) if stream_url else None
            if (
                not opponent
                or len(opponent) > 120
                or not event
                or len(event) > 160
                or starts_at is None
                or starts_at <= datetime.now(timezone.utc)
            ):
                flash('Enter an opponent, event, and valid match date/time.', category='error')
            elif stream_url and (parsed_stream.scheme not in ('https', 'http') or not parsed_stream.netloc or len(stream_url) > 500):
                flash('Stream link must be a valid HTTP or HTTPS URL.', category='error')
            else:
                db.session.add(
                    ScheduledMatch(
                        opponent=opponent,
                        event=event,
                        starts_at=starts_at,
                        stream_url=stream_url or None,
                    )
                )
                db.session.commit()
                flash('Upcoming match published.', category='success')
                return redirect(url_for('coach.updates'))
        elif action == 'profile':
            slug = request.form.get('slug', '')
            profile = db.session.get(PlayerProfile, slug)
            role = request.form.get('role', '').strip()
            rank = request.form.get('rank', '').strip()
            bio = request.form.get('bio', '').strip()
            social_url = request.form.get('social_url', '').strip()
            settings = request.form.get('settings', '').strip()
            pc_specs = request.form.get('pc_specs', '').strip()
            valid_slug = any(player['slug'] == slug for player in PLAYER_ROSTER)
            parsed_social_url = urlparse(social_url) if social_url else None
            if (
                not valid_slug
                or profile is None
                or len(role) > 120
                or len(rank) > 120
                or len(bio) > 1200
                or len(social_url) > 500
                or len(settings) > 500
                or len(pc_specs) > 500
            ):
                flash('Check the player profile fields and length limits.', category='error')
            elif social_url and (
                parsed_social_url.scheme not in ('https', 'http') or not parsed_social_url.netloc
            ):
                flash('Social profile must be a valid HTTP or HTTPS URL.', category='error')
            else:
                profile.role = role or None
                profile.rank = rank or None
                profile.bio = bio or None
                profile.social_url = social_url or None
                profile.settings = settings or None
                profile.pc_specs = pc_specs or None
                db.session.commit()
                flash('Player profile updated.', category='success')
                return redirect(url_for('coach.updates'))
        else:
            abort(400)
    announcements = db.session.scalars(
        db.select(Announcement).order_by(Announcement.created_at.desc())
    ).all()
    fixtures = db.session.scalars(
        db.select(ScheduledMatch).order_by(ScheduledMatch.starts_at)
    ).all()
    profiles = db.session.scalars(db.select(PlayerProfile).order_by(PlayerProfile.name)).all()
    return render_template(
        'coach_updates.html',
        user=current_user,
        announcements=announcements,
        fixtures=fixtures,
        profiles=profiles,
    )


@coach.route('/coach/updates/<string:content_type>/<int:content_id>/delete', methods=['POST'])
@login_required
def delete_update(content_type, content_id):
    if not is_coach(current_user):
        abort(403)
    model = {'announcement': Announcement, 'match': ScheduledMatch}.get(content_type)
    if model is None:
        abort(404)
    item = db.session.get(model, content_id)
    if item is None:
        abort(404)
    db.session.delete(item)
    db.session.commit()
    flash('SILENCE update removed.', category='success')
    return redirect(url_for('coach.updates'))
