import json
import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, DateField
from wtforms.validators import DataRequired, Email
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'travixa-super-secret-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///travixa.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = True

# ─────────────────────────────────────────────
# Custom Jinja2 filters
# ─────────────────────────────────────────────

from datetime import timedelta

@app.template_filter('timedelta_days')
def timedelta_days_filter(days):
    return timedelta(days=int(days))


db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    trips = db.relationship('Trip', backref='host', lazy=True)


class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    budget = db.Column(db.Float)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    destination = db.Column(db.String(100))
    status = db.Column(db.String(20), default='draft')
    participants = db.relationship('Participant', backref='trip', lazy=True)
    itinerary = db.relationship('ItineraryItem', backref='trip', lazy=True)

    @property
    def days(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 3


class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'))
    name = db.Column(db.String(80))
    phone = db.Column(db.String(20), unique=True)
    survey_step = db.Column(db.Integer, default=0)
    survey_responses = db.Column(db.Text, default='[]')


class ItineraryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'))
    day = db.Column(db.Integer)
    time = db.Column(db.String(10))
    place_name = db.Column(db.String(100))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(200))
    duration = db.Column(db.String(20))
    cost_estimate = db.Column(db.Float)
    category = db.Column(db.String(50), default='general')


# ─────────────────────────────────────────────
# Forms
# ─────────────────────────────────────────────

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')


class TripForm(FlaskForm):
    title = StringField('Trip Title', validators=[DataRequired()])
    destination = StringField('Destination', validators=[DataRequired()])
    budget = FloatField('Total Budget ($)', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    submit = SubmitField('Create Trip')


# ─────────────────────────────────────────────
# DB init & user loader
# ─────────────────────────────────────────────

with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─────────────────────────────────────────────
# Auth routes
# ─────────────────────────────────────────────

@app.route('/')
def index():
    trips = []
    if current_user.is_authenticated:
        trips = Trip.query.filter_by(host_id=current_user.id).all()
    return render_template('index.html', user=current_user, trips=trips)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered!', 'danger')
            return render_template('register.html', form=form)
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data)
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid email or password!', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ─────────────────────────────────────────────
# Trip routes
# ─────────────────────────────────────────────

@app.route('/create-trip', methods=['GET', 'POST'])
@login_required
def create_trip():
    form = TripForm()
    if form.validate_on_submit():
        trip = Trip(
            title=form.title.data,
            host_id=current_user.id,
            budget=form.budget.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            destination=form.destination.data,
            status='draft'
        )
        db.session.add(trip)
        db.session.commit()
        flash(f'Trip "{trip.title}" created successfully!', 'success')
        return redirect(url_for('trip_detail', trip_id=trip.id))
    return render_template('create_trip.html', form=form)


@app.route('/trip/<int:trip_id>')
@login_required
def trip_detail(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.host_id != current_user.id:
        flash('You can only view your own trips!', 'danger')
        return redirect(url_for('index'))
    participants = Participant.query.filter_by(trip_id=trip_id).all()
    itinerary = ItineraryItem.query.filter_by(trip_id=trip_id).order_by(
        ItineraryItem.day, ItineraryItem.id
    ).all()
    return render_template('trip_detail.html', trip=trip, participants=participants, itinerary=itinerary)


@app.route('/trip/<int:trip_id>/add-participant', methods=['POST'])
@login_required
def add_participant(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.host_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()

    if not name or not phone:
        return jsonify({'error': 'Name and phone are required'}), 400

    if Participant.query.filter_by(phone=phone).first():
        return jsonify({'error': 'Phone already registered'}), 400

    participant = Participant(trip_id=trip_id, name=name, phone=phone)
    db.session.add(participant)

    if trip.status == 'draft':
        trip.status = 'participants_added'

    db.session.commit()
    return jsonify({'success': True, 'participant': {'name': name, 'phone': phone}})


@app.route('/trip/<int:trip_id>/generate-itinerary')
@login_required
def generate_itinerary(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.host_id != current_user.id:
        return redirect(url_for('index'))

    # Delete existing items to avoid duplicates on re-generate
    ItineraryItem.query.filter_by(trip_id=trip_id).delete()
    db.session.commit()  # commit the delete first

    # Try AI generation
    ai_success = False
    try:
        from trip_ai import TripAI
        ai = TripAI()
        ai_success = ai.generate_smart_itinerary(trip_id)
    except Exception as e:
        print(f"AI generation error: {e}")

    # Always run fallback if AI didn't produce items
    if not ai_success:
        destination_activities = {
            'goa':    [("Baga Beach", "09:00", "nature", "Relax on Goa's most famous beach with golden sand and clear waters."),
                       ("Old Goa Churches", "13:00", "culture", "Explore UNESCO-listed Baroque churches dating back to the 16th century."),
                       ("Night Market Arpora", "19:00", "food", "Browse local crafts, taste Goan cuisine and enjoy live music.")],
            'manali': [("Rohtang Pass", "08:00", "adventure", "Scenic mountain pass at 3978m with breathtaking Himalayan views."),
                       ("Hadimba Temple", "13:00", "culture", "Ancient wooden temple nestled in a cedar forest, built in 1553."),
                       ("Old Manali Market", "18:00", "food", "Explore cafes, local shops and taste authentic Himachali food.")],
            'default':[("City Sightseeing", "09:00", "sightseeing", f"Explore the iconic landmarks and hidden gems of {trip.destination}."),
                       ("Local Museum", "13:00", "culture", f"Discover the rich history and culture of {trip.destination}."),
                       ("Food & Night Market", "19:00", "food", f"Taste the best local cuisine {trip.destination} has to offer.")],
        }
        dest_key = trip.destination.lower().strip()
        activities = destination_activities.get(dest_key, destination_activities['default'])
        num_participants = max(len(trip.participants), 1)
        per_person_per_activity = round(trip.budget / (trip.days * 3 * num_participants), 2)

        for day in range(1, trip.days + 1):
            for act_name, time, category, description in activities:
                item = ItineraryItem(
                    trip_id=trip.id,
                    day=day,
                    time=time,
                    place_name=f"{act_name}",
                    description=description,
                    image_url=f"https://source.unsplash.com/400x250/?{trip.destination.replace(' ', '+')},{category}",
                    duration="3-4 hours",
                    cost_estimate=per_person_per_activity,
                    category=category
                )
                db.session.add(item)

    trip.status = 'itinerary_generated'
    db.session.commit()
    flash('✨ AI Itinerary Generated! Check your trip details below.', 'success')
    return redirect(url_for('trip_detail', trip_id=trip_id))


# ─────────────────────────────────────────────
# SMS / Survey routes
# ─────────────────────────────────────────────

@app.route('/sms', methods=['POST'])
def sms_incoming():
    from sms_service import SMSSurvey
    from twilio.twiml.messaging_response import MessagingResponse

    from_phone = request.values.get('From', '')
    body = request.values.get('Body', '').strip()

    survey = SMSSurvey()
    participant = Participant.query.filter_by(phone=from_phone).first()
    response_text = survey.process_reply(participant, body, db)

    resp = MessagingResponse()
    resp.message(response_text)
    return str(resp)


@app.route('/trip/<int:trip_id>/send-surveys', methods=['POST'])
@login_required
def send_trip_surveys(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.host_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    from sms_service import SMSSurvey
    survey = SMSSurvey()

    sent = 0
    for p in trip.participants:
        try:
            if survey.start_survey(p):
                p.survey_step = 1
                p.survey_responses = '[]'
                sent += 1
        except Exception as e:
            print(f"SMS error for {p.name}: {e}")

    trip.status = 'surveys_sent'
    db.session.commit()
    return jsonify({'success': True, 'sent': sent, 'total': len(trip.participants)})


@app.route('/trip/<int:trip_id>/survey-status')
@login_required
def survey_status(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.host_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    complete = sum(
        1 for p in trip.participants
        if len(json.loads(p.survey_responses or '[]')) >= 4
    )
    return jsonify({'complete': complete, 'total': len(trip.participants)})


# ─────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
