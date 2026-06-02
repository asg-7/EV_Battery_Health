import sqlite3
import pandas as pd
from sklearn.ensemble import IsolationForest
import pickle
import time
import os

DB_PATH = "data/battery_stream.db"
MODEL_PATH = "models/isolation_forest.pkl"

def train_initial_model():
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT voltage, current, temp, capacity FROM battery_telemetry", conn)
        conn.close()
    except (sqlite3.OperationalError, pd.errors.DatabaseError):
        return None
    if df.shape[0] < 100:
        return None
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(df[['voltage', 'current', 'temp', 'capacity']])
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    return model

def create_anomalies_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS anomalies (
                    timestamp TEXT,
                    cycle_id INTEGER
                )''')
    conn.close()

def detect_anomalies_window(window_minutes=2):
    try:
        conn = sqlite3.connect(DB_PATH)
        # Use julianday for time difference (works on SQLite)
        df = pd.read_sql_query(f"""
            SELECT timestamp, cycle_id, voltage, current, temp, capacity 
            FROM battery_telemetry 
            WHERE julianday('now') - julianday(timestamp) <= {window_minutes}/1440.0
        """, conn)
        conn.close()
    except (sqlite3.OperationalError, pd.errors.DatabaseError):
        return []
    if df.empty or not os.path.exists(MODEL_PATH):
        return []
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    features = df[['voltage', 'current', 'temp', 'capacity']].ffill()
    preds = model.predict(features)
    anomalies = df[preds == -1]
    # Insert anomalies into table
    conn = sqlite3.connect(DB_PATH)
    for _, row in anomalies.iterrows():
        conn.execute("INSERT INTO anomalies (timestamp, cycle_id) VALUES (?,?)",
                     (row['timestamp'], row['cycle_id']))
    conn.commit()
    conn.close()
    return anomalies.to_dict('records')

if __name__ == "__main__":
    create_anomalies_table()
    print("Anomaly detector service started...")
    while True:
        if not os.path.exists(MODEL_PATH):
            model = train_initial_model()
            if model is not None:
                print("Successfully trained Isolation Forest model!")
            else:
                # Silently wait or print status
                pass
        
        # Detect anomalies in the last window
        anomalies = detect_anomalies_window()
        if anomalies:
            print(f"Detected {len(anomalies)} anomalies")
        time.sleep(5) # Check every 5 seconds for more responsive real-time dashboard updates

