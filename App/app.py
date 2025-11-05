import os
import requests
from flask import Flask, render_template, request, abort, session, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_KEY = os.environ.get("OPENWEATHER_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your-secret-key-here")  # Set this in .env file for production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///weather_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    favorites = db.relationship('FavoriteLocation', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class FavoriteLocation(db.Model):
    __tablename__ = 'favorite_locations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    city_name = db.Column(db.String(100), nullable=False)
    country_code = db.Column(db.String(2))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'city_name', name='uix_user_city'),
    )

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_weather_data(city):
    """Helper function to fetch weather data for a city"""
    if not API_KEY:
        abort(500, description="OpenWeatherMap API key not configured.")

    params = {
        'q': city,
        'appid': API_KEY,
        'units': 'metric'
    }
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    data = response.json()

    if data['cod'] == 200:
        return {
            'city': data['name'],
            'country': data['sys']['country'],
            'temperature': round(data['main']['temp']),
            'description': data['weather'][0]['description'].capitalize(),
            'icon': data['weather'][0]['icon'],
            'humidity': data['main']['humidity'],
            'wind_speed': data['wind']['speed']
        }
    return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    weather_data = None
    favorites_weather = []
    city = request.form.get('city') if request.method == 'POST' else 'London' # Default city or user input

    if not API_KEY:
        abort(500, description="OpenWeatherMap API key not configured.")

    if city:
        try:
            weather_data = get_weather_data(city)
            if not weather_data:
                return render_template('index.html', error='City not found', city_input=city)
        except requests.exceptions.RequestException as e:
            return render_template('index.html', error=f"Network error: {e}", city_input=city)
        except Exception as e:
            return render_template('index.html', error=f"An unexpected error occurred: {e}", city_input=city)

    # Get weather for favorite cities if user is logged in
    favorites_weather = []
    user_favorites = []
    if current_user.is_authenticated:
        favorites = FavoriteLocation.query.filter_by(user_id=current_user.id).all()
        user_favorites = [fav.city_name for fav in favorites]
        for fav in favorites:
            try:
                weather = get_weather_data(fav.city_name)
                if weather:
                    favorites_weather.append(weather)
            except:
                continue

    return render_template('index.html', 
                         weather=weather_data, 
                         city_input=city,
                         favorites=user_favorites,
                         favorites_weather=favorites_weather,
                         is_authenticated=current_user.is_authenticated)

@app.route('/favorite/add/<city>')
@login_required
def add_favorite(city):
    # Try to get weather data to get country code
    try:
        weather_data = get_weather_data(city)
        if weather_data:
            # Check if already favorited
            existing = FavoriteLocation.query.filter_by(
                user_id=current_user.id,
                city_name=weather_data['city']
            ).first()
            
            if not existing:
                favorite = FavoriteLocation(
                    user_id=current_user.id,
                    city_name=weather_data['city'],
                    country_code=weather_data['country']
                )
                db.session.add(favorite)
                db.session.commit()
                flash(f'Added {weather_data["city"]} to favorites')
    except:
        flash('Could not add city to favorites')
    return redirect(url_for('index'))

@app.route('/favorite/remove/<city>')
@login_required
def remove_favorite(city):
    favorite = FavoriteLocation.query.filter_by(
        user_id=current_user.id,
        city_name=city
    ).first()
    
    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        flash(f'Removed {city} from favorites')
    return redirect(url_for('index'))

def init_db():
    with app.app_context():
        db.create_all()
        print("Database initialized!")

if __name__ == '__main__':
    init_db()  # Initialize database tables
    app.run(debug=True)