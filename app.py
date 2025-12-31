from flask import Flask, jsonify, request
from garminconnect import Garmin
import os
from datetime import date

app = Flask(__name__)

@app.route('/')
def home():
    return "Garmin Bridge is Running!"

@app.route('/get_stats', methods=)
def get_stats():
    # Hitelesítési adatok betöltése a környezeti változókból
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    
    try:
        # Belépés a Garminba
        client = Garmin(email, password)
        client.login()
        
        # Mai dátum lekérése
        today = date.today()
        
        # Adatok lekérése: Napi statisztikák és utolsó edzések
        stats = client.get_stats(today.isoformat())
        activities = client.get_activities(0, 5) # Utolsó 5 edzés
        
        # Válasz összeállítása JSON formátumban
        data = {
            "daily_summary": stats,
            "recent_activities": activities
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
