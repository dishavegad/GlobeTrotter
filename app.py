from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import os

from models import db, User, Trip, Section, ItineraryItem

app = Flask(__name__)
app.secret_key = "globetrotter_secret_123"  # TODO: move to env var before real deployment

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'globetrotter.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

DONUT_COLORS = ['#6C5CE7', '#A29BFE', '#00cec9', '#fdcb6e', '#e17055', '#74b9ff']


def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap


# quick helper, dates in db are plain strings so gotta parse everywhere
def parse_date(d):
    try:
        return datetime.strptime(d, '%Y-%m-%d').date()
    except Exception:
        return None


def trip_progress(trip):
    today = datetime.now().date()
    s = parse_date(trip.start_date)
    e = parse_date(trip.end_date) or s

    if not s:
        return {'status': 'upcoming', 'percent': 0, 'days': 0}

    days = (e - s).days + 1 if e else 1

    if today < s:
        return {'status': 'upcoming', 'percent': 0, 'days': days}
    elif today > e:
        return {'status': 'completed', 'percent': 100, 'days': days}
    else:
        elapsed = (today - s).days + 1
        pct = int((elapsed / days) * 100) if days else 0
        return {'status': 'ongoing', 'percent': min(pct, 100), 'days': days}


def build_conic(segments):
    if not segments:
        return "#E0D3FF"
    parts = []
    cum = 0
    for seg in segments:
        start = cum
        cum += seg['pct']
        parts.append(f"{seg['color']} {start}% {cum}%")
    return "conic-gradient(" + ", ".join(parts) + ")"


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('landing'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('first_name', '') + ' ' + request.form.get('last_name', '')
        email = request.form.get('email')
        username = email.split('@')[0] if email else request.form.get('username')
        raw_pass = request.form.get('password', 'changeme123')

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("User already exists with this email")
            return redirect(url_for('register'))

        try:
            new_user = User(
                name=name.strip(),
                username=username,
                email=email,
                password=generate_password_hash(raw_pass)
            )
            db.session.add(new_user)
            db.session.commit()
            flash("Registered successfully, please login")
            return redirect(url_for('login'))
        except Exception as e:
            print("register failed:", e)
            db.session.rollback()
            flash("Something went wrong, try again")
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form.get('username')
        pwd = request.form.get('password')

        user = User.query.filter_by(username=uname).first()
        if not user:
            user = User.query.filter_by(email=uname).first()  # some ppl type email instead

        if user and check_password_hash(user.password, pwd):
            session['user_id'] = user.id
            session['user_name'] = user.name
            return redirect(url_for('landing'))
        else:
            flash("Invalid username or password")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/landing')
@login_required
def landing():
    trips = Trip.query.filter_by(user_id=session['user_id']).order_by(Trip.id.desc()).all()
    today = datetime.now().date()

    upcoming_count = 0
    completed_count = 0
    total_days = 0
    countries = set()

    for t in trips:
        if t.place:
            countries.add(t.place.strip().lower())
        info = trip_progress(t)
        if info['status'] == 'upcoming':
            upcoming_count += 1
        elif info['status'] == 'completed':
            completed_count += 1
            total_days += info['days']

    latest_trip = trips[0] if trips else None
    donut_segments = []
    total_budget = 0
    preview_items = []

    if latest_trip:
        secs = Section.query.filter_by(trip_id=latest_trip.id).all()
        total_budget = sum(s.budget or 0 for s in secs)
        for idx, s in enumerate(secs):
            pct = round((s.budget / total_budget * 100), 1) if total_budget else 0
            donut_segments.append({
                'title': s.title, 'budget': s.budget,
                'pct': pct, 'color': DONUT_COLORS[idx % len(DONUT_COLORS)]
            })
        preview_items = ItineraryItem.query.filter_by(trip_id=latest_trip.id)\
            .order_by(ItineraryItem.day_number).limit(5).all()

    conic_css = build_conic(donut_segments)

    trip_cards = [{'trip': t, 'info': trip_progress(t)} for t in trips[:3]]

    return render_template('landing.html',
        trip_cards=trip_cards, upcoming_count=upcoming_count, completed_count=completed_count,
        countries_count=len(countries), total_days=total_days, latest_trip=latest_trip,
        donut_segments=donut_segments, total_budget=total_budget, conic_css=conic_css,
        preview_items=preview_items)


@app.route('/create_trip', methods=['GET', 'POST'])
@login_required
def create_trip():
    if request.method == 'POST':
        place = request.form.get('place')
        start = request.form.get('start_date')
        end = request.form.get('end_date')

        if not place or not start:
            flash("Place and start date are required")
            return redirect(url_for('create_trip'))

        trip = Trip(user_id=session['user_id'], place=place, start_date=start, end_date=end)
        db.session.add(trip)
        db.session.commit()
        return redirect(url_for('build_itinerary', trip_id=trip.id))

    return render_template('create_trip.html')


@app.route('/build_itinerary/<int:trip_id>', methods=['GET', 'POST'])
@login_required
def build_itinerary(trip_id):
    trip = Trip.query.get_or_404(trip_id)

    if request.method == 'POST':
        title = request.form.get('title')
        date_range = request.form.get('date_range')
        budget_raw = request.form.get('budget')

        try:
            budget = float(budget_raw)
        except (ValueError, TypeError):
            budget = 0

        sec = Section(trip_id=trip.id, title=title, date_range=date_range, budget=budget)
        db.session.add(sec)
        db.session.commit()
        return redirect(url_for('build_itinerary', trip_id=trip.id))

    sections = Section.query.filter_by(trip_id=trip.id).all()
    return render_template('build_itinerary.html', trip=trip, sections=sections)


@app.route('/itinerary_view/<int:trip_id>', methods=['GET', 'POST'])
@login_required
def itinerary_view(trip_id):
    trip = Trip.query.get_or_404(trip_id)

    if request.method == 'POST':
        day_num = request.form.get('day_number')
        activity = request.form.get('activity')
        expense_raw = request.form.get('expense')

        try:
            day_num = int(day_num)
        except (ValueError, TypeError):
            day_num = 1

        try:
            expense = float(expense_raw)
        except (ValueError, TypeError):
            expense = 0

        item = ItineraryItem(trip_id=trip.id, day_number=day_num, activity=activity, expense=expense)
        db.session.add(item)
        db.session.commit()
        return redirect(url_for('itinerary_view', trip_id=trip.id))

    items = ItineraryItem.query.filter_by(trip_id=trip.id).order_by(ItineraryItem.day_number).all()

    days = {}
    for it in items:
        days.setdefault(it.day_number, []).append(it)

    total_expense = sum(i.expense for i in items) if items else 0
    sections = Section.query.filter_by(trip_id=trip.id).all()
    section_budget = sum(s.budget or 0 for s in sections)

    return render_template('itinerary_view.html', trip=trip, days=days,
        total_expense=total_expense, section_budget=section_budget)


@app.route('/trips')
@login_required
def trip_listing():
    all_trips = Trip.query.filter_by(user_id=session['user_id']).all()

    ongoing, upcoming, completed = [], [], []
    for t in all_trips:
        info = trip_progress(t)
        entry = {'trip': t, 'info': info}
        if info['status'] == 'ongoing':
            ongoing.append(entry)
        elif info['status'] == 'upcoming':
            upcoming.append(entry)
        else:
            completed.append(entry)

    return render_template('trip_listing.html', ongoing=ongoing, upcoming=upcoming, completed=completed)


@app.route('/profile')
@login_required
def profile():
    user = User.query.get(session['user_id'])
    all_trips = Trip.query.filter_by(user_id=user.id).all()

    preplanned, previous = [], []
    for t in all_trips:
        info = trip_progress(t)
        if info['status'] == 'completed':
            previous.append(t)
        else:
            preplanned.append(t)

    return render_template('profile.html', user=user, preplanned=preplanned, previous=previous)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
