import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
import sqlite3
import os

DB_PATH = "data/battery_stream.db"
MODEL_PATH = "models/lstm_temp.h5"

def prepare_sequences(data, seq_length=10):
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i:i+seq_length])
        y.append(data[i+seq_length])
    return np.array(X), np.array(y)

def train_lstm():
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT temp FROM battery_telemetry ORDER BY timestamp", conn)
        conn.close()
    except (sqlite3.OperationalError, pd.errors.DatabaseError):
        return None
    if len(df) < 50:
        return None
    values = df['temp'].values.reshape(-1, 1)
    seq_len = 10
    X, y = prepare_sequences(values, seq_len)
    if len(X) == 0:
        return None
    model = Sequential([
        LSTM(50, activation='relu', input_shape=(seq_len, 1)),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    model.fit(X, y, epochs=10, verbose=0)
    model.save(MODEL_PATH)
    return model

def predict_next_temperature():
    if not os.path.exists(MODEL_PATH):
        return None
    model = tf.keras.models.load_model(MODEL_PATH)
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT temp FROM battery_telemetry ORDER BY timestamp DESC LIMIT 10", conn)
        conn.close()
    except (sqlite3.OperationalError, pd.errors.DatabaseError):
        return None
    if len(df) < 10:
        return None
    last_10 = df['temp'].values[::-1].reshape(1, 10, 1)
    pred = model.predict(last_10, verbose=0)
    return float(pred[0][0])
