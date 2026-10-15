import os

import httpx
from flask import Blueprint, Response, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import db
from .models import Note

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
    return render_template('teams.html', user=current_user, teams=TEAMS)


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
    )


@views.route('/join-silence/application', methods=['POST'])
def join_application():
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

    application_text = '\n'.join(
        ['SILENCE // ESPORTS PLAYER APPLICATION', '=' * 38, '']
        + [f'{label}: {answers[key]}' for key, label, _ in fields]
        + ['', 'Prepared on this device. This application was not sent to SILENCE.']
    )
    response = Response(application_text, mimetype='text/plain; charset=utf-8')
    response.headers['Content-Disposition'] = 'attachment; filename="silence-player-application.txt"'
    response.headers['Cache-Control'] = 'no-store'
    return response


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

    messages = [
        {
            'role': 'system',
            'content': (
                'You are H.A.R.V.E.Y., a polite, concise assistant on SILENCE, an esports community website. '
                'Help with general questions, gaming and esports topics, and navigating the site. '
                'You cannot access or modify website files, accounts, private notes, or deployments, '
                'so never claim you have performed those actions. Do not request or reveal secrets.'
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