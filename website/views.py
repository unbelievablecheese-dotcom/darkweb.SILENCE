import csv
import io
import os

import httpx
from flask import Blueprint, Response, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import db
from .models import Note, PlayerApplication

views = Blueprint('views', __name__)

TEAMS = [
    {
        "tag": "01 / SILENCE",
        "name": "SILENCE",
        "discipline": "VALORANT // MAIN ROSTER",
        "description": "The starting five. Quiet focus, fearless plays, one round at a time.",
        "mark": "S",
        "color": "pink",
    },
    {
        "tag": "02 / SHHHH",
        "name": "SHHHH",
        "discipline": "VALORANT // ACADEMY",
        "description": "The next generation, sharpening their game and earning their place.",
        "mark": "H",
        "color": "orange",
    },
    {
        "tag": "03 / SILENCE",
        "name": "SILENCE GC",
        "discipline": "VALORANT // GAME CHANGERS",
        "description": "A roster built on skill, teamwork, and making room for the next voice.",
        "mark": "GC",
        "color": "violet",
    },
    {
        "tag": "04 / SHHHH",
        "name": "SHHHH RISING",
        "discipline": "COMMUNITY // DEVELOPMENT",
        "description": "A place to learn, compete, and grow alongside the SILENCE community.",
        "mark": "R",
        "color": "cyan",
    },
]

VLR_MATCHES = [
    {
        "date": "2026-10-02",
        "opponent": "the chuds",
        "score": "0–2",
        "result": "loss",
        "event": "FunhaverGG: Back to Basics 2.0 #6",
    },
    {
        "date": "2026-10-02",
        "opponent": "Evil Geniuses Academy",
        "score": "0–2",
        "result": "loss",
        "event": "FunhaverGG: Back to Basics 2.0 #6",
    },
    {
        "date": "2026-07-03",
        "opponent": "who is greg",
        "score": "1–2",
        "result": "loss",
        "event": "FunhaverGG: Plain 2.0 #1",
    },
    {
        "date": "2026-07-03",
        "opponent": "4kt",
        "score": "0–2",
        "result": "loss",
        "event": "FunhaverGG: Plain 2.0 #1",
    },
]
VLR_MATCHES_CHECKED = "14 October 2026"

PLAYER_ROSTER = [
    {"name": "Flawed", "url": "https://www.vlr.gg/player/66089/flawed"},
    {"name": "Fizzy", "url": "https://www.vlr.gg/player/65294/fizzy"},
    {"name": "Ghost", "url": "https://www.vlr.gg/player/65296/ghost"},
    {"name": "doom", "url": "https://www.vlr.gg/player/65295/doom"},
    {"name": "miniKong", "url": "https://www.vlr.gg/player/65297/minikong"},
]
PLAYER_ROSTER_CHECKED = "14 October 2026"
APPLICATION_STATUSES = ("new", "reviewing", "shortlisted", "declined")


def configured_coach_emails():
    return {
        email.strip().lower()
        for email in os.environ.get("COACH_EMAILS", "").split(",")
        if email.strip()
    }


def is_coach(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.email.lower() in configured_coach_emails()


def summarize_match_record(matches):
    wins = sum(match["result"] == "win" for match in matches)
    losses = sum(match["result"] == "loss" for match in matches)
    played = wins + losses
    win_percent = wins / played * 100 if played else 0

    return {
        "played": played,
        "wins": wins,
        "losses": losses,
        "win_percent": win_percent,
        "loss_percent": 100 - win_percent if played else 0,
    }


@views.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('Sign in to save a private note.', category='error')
            return redirect(url_for('auth.login', next=url_for('views.notes')))

        note = request.form.get('note', '').strip()

        if not note:
            flash('Note is too short!', category='error')
        elif len(note) > 10000:
            flash('Note must be 10,000 characters or fewer.', category='error')
        else:
            new_note = Note(data=note, user_id=current_user.id)
            db.session.add(new_note)
            db.session.commit()
            flash('Note added!', category='success')
            return redirect(url_for('views.notes'))

    return render_template('home.html', user=current_user, teams=TEAMS[:3])


@views.route('/teams')
def teams():
    return render_template(
        'teams.html',
        user=current_user,
        teams=TEAMS,
        player_roster=PLAYER_ROSTER,
        roster_checked=PLAYER_ROSTER_CHECKED,
    )


@views.route('/merch')
def merch():
    return render_template('merch.html', user=current_user)


@views.route('/content')
def content():
    return render_template('content.html', user=current_user)


@views.route('/community')
def community():
    record = summarize_match_record(VLR_MATCHES)
    return render_template(
        'community.html',
        user=current_user,
        matches=VLR_MATCHES,
        record=record,
        matches_checked=VLR_MATCHES_CHECKED,
        is_coach=is_coach,
        applications_enabled=bool(configured_coach_emails()),
    )


@views.route('/join-silence/application', methods=['POST'])
def join_application():
    if not configured_coach_emails():
        flash('Player applications are not open until SILENCE staff access is configured.', category='error')
        return redirect(url_for('views.community') + '#join-silence')

    fields = (
        ('name', 'Name / gamer tag', 100),
        ('email', 'Contact email', 254),
        ('game', 'Game and platform', 100),
        ('role', 'Preferred role', 100),
        ('rank', 'Current rank / level', 100),
        ('region', 'Region and time zone', 100),
        ('experience', 'Competitive experience', 1200),
        ('availability', 'Practice availability', 500),
        ('profile', 'Tracker / profile / VOD links', 500),
        ('motivation', 'Why do you want to join SILENCE?', 1200),
    )
    answers = {}
    for key, label, max_length in fields:
        value = request.form.get(key, '').strip()
        if not value:
            flash(f'{label} is required.', category='error')
            return redirect(url_for('views.community') + '#join-silence')
        if len(value) > max_length:
            flash(f'{label} must be {max_length} characters or fewer.', category='error')
            return redirect(url_for('views.community') + '#join-silence')
        answers[key] = value

    email_parts = answers['email'].split('@')
    if (
        len(email_parts) != 2
        or not email_parts[0]
        or '.' not in email_parts[1]
        or email_parts[1].startswith('.')
        or email_parts[1].endswith('.')
        or any(character.isspace() for character in answers['email'])
    ):
        flash('Enter a valid contact email.', category='error')
        return redirect(url_for('views.community') + '#join-silence')

    if request.form.get('consent') != 'yes':
        flash('Please confirm that SILENCE may store your application for coach review.', category='error')
        return redirect(url_for('views.community') + '#join-silence')

    application = PlayerApplication()
    for key, value in answers.items():
        setattr(application, key, value)
    db.session.add(application)
    db.session.commit()
    flash('Your player questionnaire was submitted for coach review.', category='success')
    return redirect(url_for('views.community') + '#join-silence')


def filtered_applications():
    statement = db.select(PlayerApplication)
    role = request.args.get('role', '').strip()[:100]
    rank = request.args.get('rank', '').strip()[:100]
    status = request.args.get('status', '').strip()
    if role:
        statement = statement.where(PlayerApplication.role.ilike(f'%{role}%'))
    if rank:
        statement = statement.where(PlayerApplication.rank.ilike(f'%{rank}%'))
    if status in APPLICATION_STATUSES:
        statement = statement.where(PlayerApplication.status == status)
    statement = statement.order_by(PlayerApplication.submitted_at.desc())
    return statement, {
        'role': role,
        'rank': rank,
        'status': status if status in APPLICATION_STATUSES else '',
    }


@views.route('/coach/applications')
@login_required
def coach_applications():
    if not is_coach(current_user):
        abort(403)
    query, filters = filtered_applications()
    return render_template(
        'coach_applications.html',
        user=current_user,
        applications=db.session.scalars(query).all(),
        statuses=APPLICATION_STATUSES,
        filters=filters,
    )


@views.route('/coach/applications.csv')
@login_required
def coach_applications_csv():
    if not is_coach(current_user):
        abort(403)
    query, _ = filtered_applications()
    output = io.StringIO()
    writer = csv.writer(output)
    fields = (
        'id', 'submitted_at', 'name', 'email', 'game', 'role', 'rank',
        'region', 'experience', 'availability', 'profile', 'motivation', 'status',
    )
    writer.writerow(fields)
    for application in db.session.scalars(query).all():
        row = [getattr(application, field) for field in fields]
        writer.writerow([
            f"'{value}" if isinstance(value, str) and value.startswith(('=', '+', '-', '@')) else value
            for value in row
        ])
    response = Response('\ufeff' + output.getvalue(), mimetype='text/csv; charset=utf-8')
    response.headers['Content-Disposition'] = 'attachment; filename="silence-player-applications.csv"'
    response.headers['Cache-Control'] = 'no-store'
    return response


@views.route('/coach/applications/<int:application_id>/status', methods=['POST'])
@login_required
def update_application_status(application_id):
    if not is_coach(current_user):
        abort(403)
    status = request.form.get('status', '')
    if status not in APPLICATION_STATUSES:
        abort(400)
    application = db.session.get(PlayerApplication, application_id)
    if application is None:
        abort(404)
    application.status = status
    db.session.commit()
    flash('Application status updated.', category='success')
    return redirect(url_for('views.coach_applications'))


@views.route('/notes', methods=['GET', 'POST'])
@login_required
def notes():
    if request.method == 'POST':
        note_text = request.form.get('note', '').strip()
        if not note_text:
            flash('Your note cannot be empty.', category='error')
        elif len(note_text) > 10000:
            flash('Note must be 10,000 characters or fewer.', category='error')
        else:
            db.session.add(Note(data=note_text, user_id=current_user.id))
            db.session.commit()
            flash('Note saved.', category='success')
            return redirect(url_for('views.notes'))

    return render_template('notes.html', user=current_user)


@views.route('/delete-note', methods=['POST'])
@login_required
def delete_note():
    payload = request.get_json(silent=True)
    note_id = payload.get('noteId') if isinstance(payload, dict) else None
    if isinstance(note_id, bool) or not isinstance(note_id, int) or note_id < 1:
        return jsonify(error='A valid noteId is required.'), 400

    note = db.session.get(Note, note_id)
    if note is None or note.user_id != current_user.id:
        return jsonify(error='Note not found.'), 404

    db.session.delete(note)
    db.session.commit()
    return jsonify(success=True)


@views.route('/harvey-chat', methods=['POST'])
@login_required
def harvey_chat():
    payload = request.get_json(silent=True)
    message = payload.get('message') if isinstance(payload, dict) else None

    if not isinstance(message, str) or not message.strip() or len(message) > 2000:
        return jsonify(error='Send a message of 1–2000 characters.'), 400

    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        return jsonify(error='H.A.R.V.E.Y. needs a GROQ_API_KEY environment variable to connect to GroqCloud.'), 503

    roster_context = '\n'.join(
        f"- {player['name']} — current VLR-listed SILENCE roster. Public profile: {player['url']}. "
        "PC specifications, in-game settings, and current rank are not verified in this site data."
        for player in PLAYER_ROSTER
    )
    messages = [
        {
            'role': 'system',
            'content': (
                'You are H.A.R.V.E.Y., a polite, concise assistant on SILENCE, an esports community website. '
                'Help with general questions, gaming and esports topics, and navigating the site. '
                'You cannot access or modify website files, accounts, private notes, or deployments, '
                'so never claim you have performed those actions. Do not request or reveal secrets. '
                'When asked about a player, answer only from the roster information below. '
                'Do not guess ranks, PC specifications, hardware, or in-game settings; say when details '
                'are not listed and link to the public profile. Clarify that the roster was checked '
                f'{PLAYER_ROSTER_CHECKED} and may change.\n\nVLR-listed SILENCE roster:\n{roster_context}'
            ),
        },
        {'role': 'user', 'content': message.strip()},
    ]

    try:
        api_response = httpx.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}'},
            json={
                'model': os.environ.get('GROQ_MODEL', 'openai/gpt-oss-120b'),
                'messages': messages,
                'max_completion_tokens': 1024,
            },
            timeout=30,
        )
        api_response.raise_for_status()
    except httpx.HTTPStatusError as error:
        current_app.logger.error('Groq API returned HTTP %s', error.response.status_code)
        return jsonify(error='H.A.R.V.E.Y. could not get a response from GroqCloud. Check the API key, model, and account limits.'), 502
    except (httpx.HTTPError, TimeoutError):
        current_app.logger.exception('Groq API request failed')
        return jsonify(error='H.A.R.V.E.Y. could not connect to GroqCloud. Please try again.'), 502

    try:
        reply = api_response.json()['choices'][0]['message']['content']
    except (ValueError, KeyError, IndexError, TypeError):
        current_app.logger.error('Groq returned a response without message text')
        return jsonify(error='GroqCloud returned an empty or unreadable response. Please try again.'), 502
    if not isinstance(reply, str) or not reply.strip():
        current_app.logger.error('Groq returned an empty text response')
        return jsonify(error='GroqCloud returned an empty response. Please try again.'), 502

    return jsonify(reply=reply.strip())