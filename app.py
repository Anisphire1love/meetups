from datetime import datetime

from flask import (Flask, abort, flash, redirect, render_template, request,
                   url_for)
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)

from models import Event, Profile, User, db

app = Flask(__name__, instance_relative_config=True)
app.config["SECRET_KEY"] = "dev-only-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///meetups.db"
app.config.from_pyfile("config.py", silent=True)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Войдите, чтобы выполнить это действие."


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    location = request.args.get("location", "").strip()
    when = request.args.get("when", "upcoming")
    if when not in ("upcoming", "past", "all"):
        when = "upcoming"

    query = Event.query
    if q:
        query = query.filter(Event.title.ilike(f"%{q}%") | Event.description.ilike(f"%{q}%"))
    if location:
        query = query.filter(Event.location.ilike(f"%{location}%"))
    now = datetime.now()
    if when == "upcoming":
        query = query.filter(Event.date >= now)
    elif when == "past":
        query = query.filter(Event.date < now)
    events = query.order_by(Event.date).all()
    return render_template("index.html", events=events, q=q, location=location, when=when)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        if len(username) < 3 or len(password) < 6:
            flash("Логин от 3 символов, пароль от 6.", "error")
        elif User.query.filter_by(username=username).first():
            flash("Такой логин уже занят.", "error")
        else:
            user = User(username=username, profile=Profile(full_name=full_name))
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Добро пожаловать!", "success")
            return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username", "").strip()).first()
        if user and user.check_password(request.form.get("password", "")):
            login_user(user)
            nxt = request.args.get("next", "")
            safe = nxt.startswith("/") and not nxt.startswith("//")
            return redirect(nxt if safe else url_for("index"))
        flash("Неверный логин или пароль.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


def parse_event_form(form):
    title = form.get("title", "").strip()
    location = form.get("location", "").strip()
    try:
        date = datetime.strptime(form.get("date", ""), "%Y-%m-%dT%H:%M")
    except ValueError:
        return None, "Укажите корректную дату и время."
    if not title or not location:
        return None, "Название и место обязательны."
    cap = form.get("capacity", "").strip()
    if cap and (not cap.isdigit() or int(cap) < 1):
        return None, "Лимит мест — положительное число."
    return dict(title=title, location=location, date=date,
                description=form.get("description", "").strip(),
                capacity=int(cap) if cap else None), None


@app.route("/events/new", methods=["GET", "POST"])
@login_required
def create_event():
    if request.method == "POST":
        data, err = parse_event_form(request.form)
        if err:
            flash(err, "error")
        else:
            event = Event(organizer=current_user, **data)
            db.session.add(event)
            db.session.commit()
            flash("Мероприятие создано.", "success")
            return redirect(url_for("event_detail", event_id=event.id))
    return render_template("event_form.html", event=None)


@app.route("/events/<int:event_id>")
def event_detail(event_id):
    event = db.get_or_404(Event, event_id)
    joined = current_user.is_authenticated and current_user in event.attendees
    return render_template("event_detail.html", event=event, joined=joined)


@app.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    event = db.get_or_404(Event, event_id)
    if event.organizer_id != current_user.id:
        abort(403)
    if request.method == "POST":
        data, err = parse_event_form(request.form)
        if err:
            flash(err, "error")
        else:
            for k, v in data.items():
                setattr(event, k, v)
            db.session.commit()
            flash("Изменения сохранены.", "success")
            return redirect(url_for("event_detail", event_id=event.id))
    return render_template("event_form.html", event=event)


@app.route("/events/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_event(event_id):
    event = db.get_or_404(Event, event_id)
    if event.organizer_id != current_user.id:
        abort(403)
    db.session.delete(event)
    db.session.commit()
    flash("Мероприятие удалено.", "success")
    return redirect(url_for("index"))


@app.route("/events/<int:event_id>/join", methods=["POST"])
@login_required
def join_event(event_id):
    event = db.get_or_404(Event, event_id)
    if current_user in event.attendees:
        flash("Вы уже зарегистрированы.", "error")
    elif event.is_full:
        flash("Свободных мест нет.", "error")
    else:
        event.attendees.append(current_user)
        db.session.commit()
        flash("Вы зарегистрированы на мероприятие.", "success")
    return redirect(url_for("event_detail", event_id=event_id))


@app.route("/events/<int:event_id>/leave", methods=["POST"])
@login_required
def leave_event(event_id):
    event = db.get_or_404(Event, event_id)
    if current_user in event.attendees:
        event.attendees.remove(current_user)
        db.session.commit()
        flash("Регистрация отменена.", "success")
    return redirect(url_for("event_detail", event_id=event_id))


@app.route("/my")
@login_required
def my_events():
    return render_template("my_events.html",
                           organized=sorted(current_user.organized, key=lambda e: e.date),
                           attending=current_user.attending.all())


@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", message="Доступ запрещён."), 403


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", message="Страница не найдена."), 404


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
