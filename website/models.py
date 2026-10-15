from flask_login import UserMixin
from sqlalchemy.sql import func

from . import db


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000), nullable=False)
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class PlayerApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=False, default=func.now())
    status_code_hash = db.Column(db.String(64), unique=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    game = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=False, index=True)
    rank = db.Column(db.String(100), nullable=False, index=True)
    region = db.Column(db.String(100), nullable=False)
    experience = db.Column(db.String(1200), nullable=False)
    availability = db.Column(db.String(500), nullable=False)
    profile = db.Column(db.String(500), nullable=False)
    motivation = db.Column(db.String(1200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='new', index=True)


class CoachRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True, index=True)
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=False, default=func.now())
    last_email_sent_at = db.Column(db.Integer)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
    user = db.relationship('User', backref=db.backref('coach_request', uselist=False))


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.String(2000), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=func.now(), index=True)


class ScheduledMatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    opponent = db.Column(db.String(120), nullable=False)
    event = db.Column(db.String(160), nullable=False)
    starts_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    stream_url = db.Column(db.String(500))


class PlayerProfile(db.Model):
    slug = db.Column(db.String(40), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(120))
    rank = db.Column(db.String(120))
    bio = db.Column(db.String(1200))
    social_url = db.Column(db.String(500))
    settings = db.Column(db.String(500))
    pc_specs = db.Column(db.String(500))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(150), nullable=False)
    notes = db.relationship(
        'Note',
        backref='user',
        cascade='all, delete-orphan',
        order_by='Note.date',
    )