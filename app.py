from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, DateField, TextAreaField
from wtforms.validators import DataRequired, Email, Length
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'travixa-super-secret-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travixa.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Simple Login Manager (no session storage needed for demo)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

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

class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'))
    name = db.Column(db.String(80))
    phone = db.Column(db.String(15))

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

# Forms
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

# Create tables
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    user = current_user
    trips = []
    if user.is_authenticated:
        trips = Trip.query.filter_by(host_id=user.id).all()
    return render_template('index.html', user=user, trips=trips)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered!')
            return render_template('register.html', form=form)
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data)
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.')
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
        flash('Invalid email or password!')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

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
            destination=form.destination.data
        )
        db.session.add(trip)
        db.session.commit()
        flash(f'Trip "{trip.title}" created successfully!')
        return redirect(url_for('trip_detail', trip_id=trip.id))
    return render_template('create_trip.html', form=form)

@app.route('/trip/<int:trip_id>')
@login_required
def trip_detail(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.host_id != current_user.id:
        flash('You can only view your own trips!')
        return redirect(url_for('index'))
    
    participants = Participant.query.filter_by(trip_id=trip_id).all()
    itinerary = ItineraryItem.query.filter_by(trip_id=trip_id).order_by(ItineraryItem.day, ItineraryItem.id).all()
    return render_template('trip_detail.html', trip=trip, participants=participants, itinerary=itinerary)

@app.route('/trip/<int:trip_id>/add-participant', methods=['POST'])
@login_required
def add_participant(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.host_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    name = request.form.get('name')
    phone = request.form.get('phone')
    
    if Participant.query.filter_by(phone=phone).first():
        return jsonify({'error': 'Phone already registered'}), 400
    
    participant = Participant(trip_id=trip_id, name=name, phone=phone)
    db.session.add(participant)
    db.session.commit()
    
    return jsonify({'success': True, 'participant': {'name': name, 'phone': phone}})

@app.route('/trip/<int:trip_id>/generate-itinerary')
@login_required
def generate_itinerary(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.host_id != current_user.id:
        return redirect(url_for('index'))
    
    # Generate demo itinerary with images
    days = (trip.end_date - trip.start_date).days + 1 if trip.end_date and trip.start_date else 3
    activities = [
        "City Tour", "Historical Museum", "Local Market", "Beach Time", 
        "Sunset Cruise", "Night Market", "Cultural Show", "Adventure Park"
    ]
    
    for day in range(1, days + 1):
        for i, activity in enumerate(activities[:3]):  # 3 activities per day
            item = ItineraryItem(
                trip_id=trip.id,
                day=day,
                time=['09:00', '14:00', '19:00'][i],
                place_name=f"{trip.destination} - {activity}",
                description=f"Experience the best of {activity.lower()} in {trip.destination}. Perfect blend of culture, adventure, and relaxation.",
                image_url=f"https://source.unsplash.com/400x250/?{trip.destination},{activity.lower()}",
                duration="3-4 hours",
                cost_estimate=round(20 + (day * 5) + (i * 10), 2)
            )
            db.session.add(item)
    
    trip.status = 'itinerary_generated'
    db.session.commit()
    flash('✨ AI-Powered Itinerary Generated! Check your trip details.')
    return redirect(url_for('trip_detail', trip_id=trip_id))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')