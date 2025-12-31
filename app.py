from flask import Flask, jsonify, request
from garminconnect import Garmin
import os
from datetime import date

app = Flask(__name__)

@app.route('/')
def home():
    return "Garmin Bridge is Running!"

# JAVÍTVA: methods= került a hiányzó rész helyére
@app.route('/get_stats', methods=)
def get_stats():
    # Hitelesítési adatok betöltése a környezeti változókból
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    
    if not email or not password:
        return jsonify({"error": "Hianyzik a GARMIN_EMAIL vagy GARMIN_PASSWORD kornyezeti valtozo!"}), 500

    try:
        # Belépés a Garminba
        client = Garmin(email, password)
        client.login()
        
        # Mai dátum lekérése
        today = date.today()
        
        # Adatok lekérése: Napi statisztikák és utolsó 5 edzés
        stats = client.get_stats(today.isoformat())
        activities = client.get_activities(0, 5) 
        
        # Válasz összeállítása JSON formátumban
        data = {
            "daily_summary": stats,
            "recent_activities": activities
        }
        return jsonify(data)
    except Exception as e:
        # Hiba esetén visszaküldjük a hiba okát szövegesen
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
