from fastapi import FastAPI, BackgroundTasks
import sqlite3
import pandas as pd
from datetime import datetime
from src.lstm_forecaster import predict_next_temperature, train_lstm
import os

app = FastAPI(title="EV Battery Telemetry API")
DB_PATH = "data/battery_stream.db"

def get_latest_metrics():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM battery_telemetry ORDER BY timestamp DESC LIMIT 1", conn)
    conn.close()
    if df.empty:
        return {}
    return df.iloc[0].to_dict()

def get_anomaly_count_last_hour():
    conn = sqlite3.connect(DB_PATH)
    # 1 hour = 1/24 of a day in julianday
    count = conn.execute("SELECT COUNT(*) FROM anomalies WHERE julianday('now') - julianday(timestamp) <= 1.0/24").fetchone()[0]
    conn.close()
    return count

@app.get("/metrics/latest")
def latest():
    metrics = get_latest_metrics()
    anomaly_count = get_anomaly_count_last_hour()
    health_score = max(0, 100 - (anomaly_count * 5))
    return {**metrics, "anomaly_count_last_hour": anomaly_count, "health_score": health_score}

@app.get("/anomalies")
def anomalies(hours: int = 24):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(f"SELECT timestamp, cycle_id FROM anomalies WHERE julianday('now') - julianday(timestamp) <= {hours}/24.0", conn)
    conn.close()
    return df.to_dict('records')

@app.get("/predict/temp")
def predict_temp(background_tasks: BackgroundTasks):
    pred = predict_next_temperature()
    if pred is None:
        # Check if we can train it on the fly
        if not os.path.exists("models/lstm_temp.h5"):
            try:
                conn = sqlite3.connect(DB_PATH)
                count = conn.execute("SELECT COUNT(*) FROM battery_telemetry").fetchone()[0]
                conn.close()
                if count >= 50:
                    background_tasks.add_task(train_lstm)
                    return {"error": "Training", "message": "LSTM model is currently training in the background. Please wait a few seconds."}
                else:
                    return {"error": "NotEnoughData", "message": f"Not enough telemetry data to train LSTM. Collected {count}/50 points."}
            except Exception as e:
                return {"error": "Error", "message": str(e)}
        return {"error": "NoModel", "message": "Model not trained or not enough sequential data to make a prediction (needs 10 sequential points)."}
    return {"predicted_next_temp_celsius": pred}

