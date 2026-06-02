import pandas as pd
import time
import sqlite3
from datetime import datetime

DB_PATH = "data/battery_stream.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS battery_telemetry (
                    timestamp TEXT,
                    cycle_id INTEGER,
                    voltage REAL,
                    current REAL,
                    temp REAL,
                    capacity REAL
                )''')
    conn.close()

def stream_data(csv_path="data/Battery.csv", delay=0.5):
    df = pd.read_csv(csv_path)
    # Map columns to our schema
    df = df.rename(columns={
        'Voltage_measured': 'voltage',
        'Current_measured': 'current',
        'Temperature_measured': 'temp',
        'Capacity': 'capacity',
        'cycle': 'cycle_id'
    })
    init_db()
    for _, row in df.iterrows():
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO battery_telemetry VALUES (?,?,?,?,?,?)",
                     (datetime.now().isoformat(), row['cycle_id'], row['voltage'],
                      row['current'], row['temp'], row['capacity']))
        conn.commit()
        conn.close()
        print(f"Inserted cycle {row['cycle_id']} at {datetime.now()}")
        time.sleep(delay)

if __name__ == "__main__":
    stream_data()
