from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120))
    password = db.Column(db.String(200), nullable=False)

    trips = db.relationship('Trip', backref='owner', lazy=True)


class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    place = db.Column(db.String(120))
    start_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))

    sections = db.relationship('Section', backref='trip', lazy=True, cascade="all, delete-orphan")
    items = db.relationship('ItineraryItem', backref='trip', lazy=True, cascade="all, delete-orphan")


# a "section" is one block in the Build Itinerary screen (hotel, travel, activity etc)
class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    title = db.Column(db.String(100))
    date_range = db.Column(db.String(50))
    budget = db.Column(db.Float, default=0)


# actual day wise activity + expense shown in the itinerary view screen
class ItineraryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    day_number = db.Column(db.Integer, default=1)
    activity = db.Column(db.String(200))
    expense = db.Column(db.Float, default=0)
