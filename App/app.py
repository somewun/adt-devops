import os
import requests
from flask import Flask, render_template, request, abort
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_KEY = os.environ.get("OPENWEATHER_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    weather_data = None
    city = request.form.get('city') if request.method == 'POST' else 'London' # Default city or user input

    if not API_KEY:
        abort(500, description="OpenWeatherMap API key not configured.")

    if city:
        params = {
            'q': city,
            'appid': API_KEY,
            'units': 'metric'  # Use 'imperial' for Fahrenheit
        }
        try:
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status() # Raise an exception for bad status codes
            data = response.json()

            if data['cod'] == 200:
                weather_data = {
                    'city': data['name'],
                    'country': data['sys']['country'],
                    'temperature': round(data['main']['temp']),
                    'description': data['weather'][0]['description'].capitalize(),
                    'icon': data['weather'][0]['icon'],
                    'humidity': data['main']['humidity'],
                    'wind_speed': data['wind']['speed']
                }
            else:
                # Handle city not found or other API specific errors
                return render_template('index.html', error=data.get('message', 'City not found'), city_input=city)

        except requests.exceptions.RequestException as e:
            return render_template('index.html', error=f"Network error: {e}", city_input=city)
        except Exception as e:
            return render_template('index.html', error=f"An unexpected error occurred: {e}", city_input=city)

    return render_template('index.html', weather=weather_data, city_input=city)

if __name__ == '__main__':
    app.run(debug=True)