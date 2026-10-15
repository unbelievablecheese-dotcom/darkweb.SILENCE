import os

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from google import genai
from google.genai.errors import APIError
from httpx import HTTPError

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

@views.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('Sign in to save a private note.', category='error')
            return redirect(url_for('auth.login', next=url_for('views.home', _anchor='your-notes')))

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
            return redirect(url_for('views.home'))

    return render_template(
        'home.html',
        user=current_user,
        teams=TEAMS,
    )


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

    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return jsonify(error='H.A.R.V.E.Y. AI is not configured yet.'), 503

    prompt = (
        'You are H.A.R.V.E.Y., a polite, concise assistant on SILENCE, an esports community website. '
        'Help with general questions, gaming and esports topics, and the user’s private notes. '
        'You cannot access or modify website files, accounts, or deployments, so never '
        'claim that you have performed those actions. Do not request or reveal secrets. '
        f'\n\nUser message:\n{message.strip()}'
    )

    try:
        client = genai.Client(api_key=api_key)
        interaction = client.interactions.create(
            model=os.environ.get('GEMINI_MODEL', 'gemini-3.8-flash'),
            input=prompt,
        )
    except (APIError, HTTPError, TimeoutError):
        current_app.logger.exception('Gemini API request failed')
        return jsonify(error='H.A.R.V.E.Y. could not get a response from Gemini.'), 502

    reply = interaction.output_text
    if not isinstance(reply, str) or not reply.strip():
        current_app.logger.error('Gemini returned an empty text response')
        return jsonify(error='Gemini returned an empty response. Please try again.'), 502

    return jsonify(reply=reply.strip())