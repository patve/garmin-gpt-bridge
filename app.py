from flask import Flask, jsonify, request
from garminconnect import Garmin
import os
from functools import lru_cache
import logging
import shutil
import time

# Configure logging (don't log sensitive data)
logging.basicConfig(level=logging.INFO)
logging.getLogger('garminconnect').setLevel(logging.WARNING)

app = Flask(__name__)

_client = None
_client_login_ts = 0
def get_client():
    """Logs in once per process; reuses the session in-memory."""
    global _client, _client_login_ts

    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    tokenstore = os.getenv("GARMINTOKENS", "/tmp/.garminconnect")

    if not email or not password:
        raise ValueError("GARMIN_EMAIL and GARMIN_PASSWORD must be set")

    # Reuse client for e.g. 30 minutes to avoid repeated MFA on multiple endpoints
    if _client and (time.time() - _client_login_ts) < 30 * 60:
        return _client

    # Avoid partial/old tokens causing OAuth refresh errors (free Render has ephemeral FS anyway)
    try:
        shutil.rmtree(tokenstore, ignore_errors=True)
    except Exception:
        pass

    client = Garmin(email, password, tokenstore=tokenstore)  # supported by python-garminconnect example :contentReference[oaicite:3]{index=3}
    client.login()  # MFA email happens here when needed
    _client = client
    _client_login_ts = time.time()
    print("✅ Garmin client authenticated successfully")
    return _client
def require_auth(f):
    """Decorator to check API key"""
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        expected = f"Bearer {os.getenv('API_KEY')}"
        
        if not auth_header or auth_header != expected:
            return jsonify({"error": "Unauthorized"}), 401
        
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

@app.route('/')
def home():
    return jsonify({
        "service": "Garmin Connect API Proxy",
        "status": "running",
        "endpoints": [
            "/api/activities?limit=30",
            "/api/sleep?date=2025-12-30",
            "/api/body_composition?start_date=2025-12-01&end_date=2025-12-30",
            "/api/user_summary?date=2025-12-30",
            "/api/heart_rate?date=2025-12-30",
            "/api/hrv?date=2025-12-30",
            "/api/stress?date=2025-12-30",
            "/api/stats?date=2025-12-30",
            "/api/steps?date=2025-12-30",
            "/api/hydration?date=2025-12-30",
            "/api/user_profile",
            "/api/spo2?date=2025-12-30",
            "/api/respiration?date=2025-12-30",
            "/api/training_status?date=2025-12-30",
            "/api/training_readiness?date=2025-12-30"
        ]
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/api/<path:endpoint>')
@require_auth
def proxy(endpoint):
    try:
        client = get_client()
        
        # Get date parameter (default to today)
        from datetime import date as dt
        date = request.args.get('date', dt.today().isoformat())
        
        # Route to appropriate method
        if endpoint == 'activities':
            limit = int(request.args.get('limit', 30))
            start = int(request.args.get('start', 0))
            data = client.get_activities(start, limit)
        
        elif endpoint == 'sleep':
            raw_data = client.get_sleep_data(date)
            
            # Filter to summary data only (GPT can't handle full response)
            if raw_data:
                daily_sleep = raw_data.get('dailySleepDTO', {})
                data = {
                    'date': date,
                    'sleep_time_seconds': daily_sleep.get('sleepTimeSeconds'),
                    'sleep_time_hours': round(daily_sleep.get('sleepTimeSeconds', 0) / 3600, 2) if daily_sleep.get('sleepTimeSeconds') else None,
                    'deep_sleep_seconds': daily_sleep.get('deepSleepSeconds'),
                    'light_sleep_seconds': daily_sleep.get('lightSleepSeconds'),
                    'rem_sleep_seconds': daily_sleep.get('remSleepSeconds'),
                    'awake_seconds': daily_sleep.get('awakeSleepSeconds'),
                    'sleep_start': daily_sleep.get('sleepStartTimestampGMT'),
                    'sleep_end': daily_sleep.get('sleepEndTimestampGMT'),
                    'sleep_start_local': daily_sleep.get('sleepStartTimestampLocal'),
                    'sleep_end_local': daily_sleep.get('sleepEndTimestampLocal'),
                    'sleep_scores': daily_sleep.get('sleepScores'),
                    'avg_spo2': daily_sleep.get('averageSpO2Value'),
                    'lowest_spo2': daily_sleep.get('lowestSpO2Value'),
                    'avg_respiration': daily_sleep.get('avgSleepRespirationValue'),
                    'resting_heart_rate': daily_sleep.get('restingHeartRate'),
                    'sleep_quality': daily_sleep.get('sleepQualityTypePK')
                }
            else:
                data = {"message": "No sleep data available for this date"}
        
        elif endpoint == 'body_composition':
            start_date = request.args.get('start_date', date)
            end_date = request.args.get('end_date', date)
            raw_data = client.get_body_composition(start_date, end_date)
            
            # Simplify body composition data
            if raw_data and 'dateWeightList' in raw_data:
                data = {
                    'start_date': start_date,
                    'end_date': end_date,
                    'measurements': [
                        {
                            'date': m.get('calendarDate'),
                            'weight_kg': round(m.get('weight', 0) / 1000, 2) if m.get('weight') else None,
                            'bmi': m.get('bmi'),
                            'body_fat_pct': m.get('bodyFat'),
                            'body_water_pct': m.get('bodyWater'),
                            'bone_mass_kg': round(m.get('boneMass', 0) / 1000, 2) if m.get('boneMass') else None,
                            'muscle_mass_kg': round(m.get('muscleMass', 0) / 1000, 2) if m.get('muscleMass') else None
                        }
                        for m in raw_data.get('dateWeightList', [])
                    ]
                }
            else:
                data = raw_data
        
        elif endpoint == 'user_summary':
            data = client.get_user_summary(date)
        
        elif endpoint == 'heart_rate':
            data = client.get_heart_rates(date)
        
        elif endpoint == 'hrv':
            data = client.get_hrv_data(date)
        
        elif endpoint == 'stress':
            data = client.get_stress_data(date)
        
        elif endpoint == 'stats':
            data = client.get_stats(date)
        
        elif endpoint == 'steps':
            data = client.get_steps_data(date)
        
        elif endpoint == 'hydration':
            data = client.get_hydration_data(date)
        
        elif endpoint == 'user_profile':
            data = {
                'full_name': client.get_full_name(),
                'unit_system': client.get_unit_system()
            }
        
        elif endpoint == 'spo2':
            data = client.get_spo2_data(date)
        
        elif endpoint == 'respiration':
            data = client.get_respiration_data(date)
        
        elif endpoint == 'training_status':
            data = client.get_training_status(date)
        
        elif endpoint == 'training_readiness':
            data = client.get_training_readiness(date)
        
        else:
            return jsonify({"error": f"Endpoint '{endpoint}' not found"}), 404
        
        return jsonify(data)
    
    except Exception as e:
        print(f"Error on {endpoint}: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
