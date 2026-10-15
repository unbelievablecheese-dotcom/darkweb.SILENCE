import os

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from google import genai
from google.genai.errors import APIError
from httpx import HTTPError

from . import db
from .models import Note

views = Blueprint('views', __name__)

PRODUCTS = [
    {
        "id": "desk-lamp",
        "name": "Arc LED Desk Lamp",
        "category": "Home",
        "price": 34.99,
        "rating": 4.8,
        "reviews": 128,
        "icon": "💡",
        "color": "gold",
        "description": "Warm, adjustable light for focused evenings.",
        "badge": "Bestseller",
    },
    {
        "id": "wireless-headphones",
        "name": "Studio Wireless Headphones",
        "category": "Electronics",
        "price": 79.00,
        "rating": 4.7,
        "reviews": 86,
        "icon": "🎧",
        "color": "blue",
        "description": "Comfortable sound for work, play, and travel.",
        "badge": "Popular pick",
    },
    {
        "id": "everyday-bottle",
        "name": "Insulated Everyday Bottle",
        "category": "Outdoors",
        "price": 22.50,
        "rating": 4.6,
        "reviews": 214,
        "icon": "🧴",
        "color": "mint",
        "description": "A sturdy, reusable companion for busy days.",
        "badge": "",
    },
    {
        "id": "canvas-tote",
        "name": "Market Canvas Tote",
        "category": "Fashion",
        "price": 18.00,
        "rating": 4.5,
        "reviews": 63,
        "icon": "👜",
        "color": "rose",
        "description": "A roomy carry-all made for everyday errands.",
        "badge": "",
    },
    {
        "id": "desk-organizer",
        "name": "Bamboo Desk Organizer",
        "category": "Home",
        "price": 27.95,
        "rating": 4.8,
        "reviews": 91,
        "icon": "🗂️",
        "color": "sand",
        "description": "Keep your workspace tidy and essentials close.",
        "badge": "Staff pick",
    },
    {
        "id": "plant-kit",
        "name": "Little Windowsill Garden Kit",
        "category": "Outdoors",
        "price": 24.00,
        "rating": 4.4,
        "reviews": 47,
        "icon": "🪴",
        "color": "mint",
        "description": "An easy-start kit for a greener corner at home.",
        "badge": "",
    },
    {
        "id": "notebook-set",
        "name": "Everyday Notebook Set",
        "category": "Stationery",
        "price": 14.25,
        "rating": 4.9,
        "reviews": 173,
        "icon": "📓",
        "color": "lilac",
        "description": "Three smooth-paper notebooks for plans and ideas.",
        "badge": "Top rated",
    },
    {
        "id": "wireless-charger",
        "name": "Compact Wireless Charger",
        "category": "Electronics",
        "price": 29.99,
        "rating": 4.3,
        "reviews": 58,
        "icon": "🔋",
        "color": "blue",
        "description": "A clean, cable-light spot for compatible devices.",
        "badge": "",
    },
]


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
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
        products=PRODUCTS,
        categories=sorted({product["category"] for product in PRODUCTS}),
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
        'You are H.A.R.V.E.Y., a polite, concise assistant on a personal notes website. '
        'Answer the user conversationally and help with general questions. '
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