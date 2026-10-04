from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def sqlite_lower(conn, record):
    conn.create_function("lower", 1, lambda s: s.lower() if s else s)


registrations = db.Table(
    "registrations",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True),
    db.Column("registered_at", db.DateTime, default=datetime.now),
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    profile = db.relationship("Profile", back_populates="user", uselist=False,
                              cascade="all, delete-orphan")
    organized = db.relationship("Event", back_populates="organizer",
                                cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    full_name = db.Column(db.String(100), default="")
    bio = db.Column(db.Text, default="")

    user = db.relationship("User", back_populates="profile")


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    capacity = db.Column(db.Integer)
    organizer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    organizer = db.relationship("User", back_populates="organized")
    attendees = db.relationship("User", secondary=registrations,
                                backref=db.backref("attending", lazy="dynamic"))

    @property
    def is_full(self):
        return self.capacity is not None and len(self.attendees) >= self.capacity
