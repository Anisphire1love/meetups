import secrets
from datetime import datetime

from app import app
from models import Event, Profile, User, db

EVENTS = [
    ("Концерт Григория Лепса", datetime(2026, 10, 11, 19, 0)),
    ("Todes. Превью", datetime(2026, 11, 12, 19, 0)),
    ("Группа t.A.T.u.", datetime(2026, 11, 13, 20, 0)),
]

with app.app_context():
    org = User.query.filter_by(username="afisha").first()
    if not org:
        password = secrets.token_urlsafe(8)
        org = User(username="afisha", profile=Profile(full_name="Афиша Иркутска"))
        org.set_password(password)
        db.session.add(org)
        print(f"Создан организатор: afisha / {password}")
    for title, date in EVENTS:
        if not Event.query.filter_by(title=title, date=date).first():
            db.session.add(Event(title=title, date=date, location="Иркутск", organizer=org))
    db.session.commit()
    print("Готово.")
