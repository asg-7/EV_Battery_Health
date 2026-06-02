import streamlit as st
import requests
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go
import os
import sqlite3
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Industrial EV Battery Telemetry", layout="wide", initial_sidebar_state="expanded")

# --- CSS Theme Injection ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
    background-color: #0B0F19; /* Solid deep slate dark background */
    color: #F8FAFC;
}

/* Header styling */
.main-header {
    background: linear-gradient(90deg, #10B981 0%, #3B82F6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    font-weight: 800;
    font-size: 2.75rem;
    margin-bottom: 5px;
}

.sub-header {
    text-align: center;
    color: #94A3B8;
    font-size: 1.1rem;
    margin-bottom: 30px;
    font-weight: 400;
}

/* Glassmorphic Metrics Card */
.metric-card {
    background: rgba(17, 24, 39, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    backdrop-filter: blur(10px);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    margin-bottom: 15px;
}

.metric-card:hover {
    transform: translateY(-3px);
    border-color: rgba(255, 255, 255, 0.15);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
}

.metric-title {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748B;
    margin-bottom: 6px;
    font-weight: 600;
}

.metric-value-container {
    display: flex;
    align-items: baseline;
}

.metric-value {
    font-size: 1.85rem;
    font-weight: 700;
    line-height: 1.1;
}

.metric-unit {
    font-size: 0.95rem;
    color: #475569;
    margin-left: 3px;
    font-weight: 500;
}

.metric-icon {
    float: right;
    font-size: 1.35rem;
    opacity: 0.8;
}

/* Glowing card frames */
.glow-green {
    box-shadow: 0 0 15px rgba(16, 185, 129, 0.15);
    border-left: 4px solid #10B981;
}
.glow-green .metric-value {
    color: #10B981;
}

.glow-blue {
    box-shadow: 0 0 15px rgba(59, 130, 246, 0.15);
    border-left: 4px solid #3B82F6;
}
.glow-blue .metric-value {
    color: #3B82F6;
}

.glow-purple {
    box-shadow: 0 0 15px rgba(139, 92, 246, 0.15);
    border-left: 4px solid #8B5CF6;
}
.glow-purple .metric-value {
    color: #8B5CF6;
}

.glow-orange {
    box-shadow: 0 0 15px rgba(245, 158, 11, 0.15);
    border-left: 4px solid #F59E0B;
}
.glow-orange .metric-value {
    color: #F59E0B;
}

.glow-red {
    box-shadow: 0 0 15px rgba(239, 68, 68, 0.15);
    border-left: 4px solid #EF4444;
}
.glow-red .metric-value {
    color: #EF4444;
}

.glow-pink {
    box-shadow: 0 0 15px rgba(236, 72, 153, 0.15);
    border-left: 4px solid #EC4899;
}
.glow-pink .metric-value {
    color: #EC4899;
}

/* Centered Uploader and Buttons */
.stFileUploader {
    background: rgba(17, 24, 39, 0.5) !important;
    border: 2px dashed rgba(255, 255, 255, 0.1) !important;
    border-radius: 14px !important;
    padding: 20px !important;
    max-width: 600px;
    margin: 0 auto !important;
    text-align: center;
}

.stFileUploader section {
    justify-content: center !important;
}

/* Custom styled tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 30px;
    background-color: transparent;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    margin-bottom: 25px;
}

.stTabs [data-baseweb="tab"] {
    background-color: transparent;
    color: #64748B;
    font-size: 16px;
    font-weight: 600;
    padding: 12px 16px;
    transition: all 0.2s ease;
}

.stTabs [aria-selected="true"] {
    color: #10B981 !important;
    border-bottom-color: #10B981 !important;
}

/* Documentation styling */
.docs-card {
    background: rgba(17, 24, 39, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 25px;
    margin-bottom: 20px;
}

.math-formula {
    background: rgba(15, 23, 42, 0.8);
    border-radius: 8px;
    padding: 15px;
    font-family: 'Courier New', Courier, monospace;
    font-size: 1.05rem;
    color: #38BDF8;
    margin: 15px 0;
    border-left: 4px solid #38BDF8;
}
</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def render_metric_card(title, value, unit, icon, glow_class):
    card_html = f"""
    <div class="metric-card {glow_class}">
        <span class="metric-icon">{icon}</span>
        <div class="metric-title">{title}</div>
        <div class="metric-value-container">
            <span class="metric-value">{value}</span>
            <span class="metric-unit">{unit}</span>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def pretrain_and_populate_models():
    """Trains Isolation Forest and LSTM forecaster immediately using the loaded data."""
    try:
        # 1. Train Isolation Forest
        from src.anomaly_detector import train_initial_model, MODEL_PATH, DB_PATH
        model = train_initial_model()
        
        # 2. Pre-detect anomalies across the entire dataset
        if model is not None and os.path.exists(MODEL_PATH):
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query("SELECT timestamp, cycle_id, voltage, current, temp, capacity FROM battery_telemetry", conn)
            if not df.empty:
                features = df[['voltage', 'current', 'temp', 'capacity']].ffill()
                preds = model.predict(features)
                anomalies = df[preds == -1]
                
                # Clear and insert all detected anomalies
                conn.execute("DELETE FROM anomalies")
                for _, row in anomalies.iterrows():
                    conn.execute("INSERT INTO anomalies (timestamp, cycle_id) VALUES (?,?)",
                                 (row['timestamp'], int(row['cycle_id'])))
                conn.commit()
            conn.close()
            
        # 3. Train LSTM temperature forecaster
        from src.lstm_forecaster import train_lstm
        train_lstm()
        
        # 4. Initialize prediction history using all available points
        if 'pred_history' in st.session_state:
            st.session_state.pred_history = []
            
        return True
    except Exception as e:
        st.error(f"Failed to pre-train models: {e}")
        return False

def reset_db_and_load_dataset(battery_id, custom_file=None):
    import shutil
    try:
        os.makedirs("data", exist_ok=True)
        dest_csv = "data/Battery.csv"
        
        # Load custom file or NASA file
        if custom_file is not None:
            with open(dest_csv, "wb") as f:
                f.write(custom_file.getbuffer())
            dataset_name = "Custom Uploaded Dataset"
        else:
            src_csv = f"Sample data/NASA_Battery_{battery_id}.csv"
            if not os.path.exists(src_csv):
                return False, f"Source dataset {src_csv} not found."
            shutil.copyfile(src_csv, dest_csv)
            dataset_name = f"NASA Battery {battery_id}"
        
        # Reset database tables
        db_path = "data/battery_stream.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS battery_telemetry")
        cursor.execute("DROP TABLE IF EXISTS anomalies")
        
        # Recreate tables immediately
        cursor.execute('''CREATE TABLE battery_telemetry (
                        timestamp TEXT,
                        cycle_id INTEGER,
                        voltage REAL,
                        current REAL,
                        temp REAL,
                        capacity REAL
                    )''')
        cursor.execute('''CREATE TABLE anomalies (
                        timestamp TEXT,
                        cycle_id INTEGER
                    )''')
        conn.commit()
        
        # 1. Pre-populate database with all telemetry rows from Battery.csv
        df = pd.read_csv(dest_csv)
        df = df.rename(columns={
            'Voltage_measured': 'voltage',
            'Current_measured': 'current',
            'Temperature_measured': 'temp',
            'Capacity': 'capacity',
            'cycle': 'cycle_id'
        })
        
        # Insert records sequentially with increments to construct a clean history timeline
        start_time = datetime.now() - timedelta(minutes=len(df) * 2)
        for idx, row in df.iterrows():
            ts = (start_time + timedelta(minutes=idx * 2)).isoformat()
            cursor.execute("INSERT INTO battery_telemetry VALUES (?,?,?,?,?,?)",
                         (ts, int(row['cycle_id']), float(row['voltage']),
                          float(row['current']), float(row['temp']), float(row['capacity'])))
        conn.commit()
        conn.close()
        
        # 2. Pre-train models immediately on load so forecast / anomalies are populated right away
        with st.spinner("Pre-populating historical stream database & pre-training safety ML models..."):
            pretrain_and_populate_models()
            
        # 3. Reload session prediction cache
        load_rolling_predictions()
            
        return True, f"Successfully loaded **{dataset_name}**! Telemetry database populated and ML models pre-trained successfully."
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_telemetry_history():
    db_path = "data/battery_stream.db"
    if not os.path.exists(db_path):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("""
            SELECT t.timestamp, t.cycle_id, t.voltage, t.current, t.temp, t.capacity,
                   CASE WHEN a.timestamp IS NOT NULL THEN 1 ELSE 0 END as is_anomaly
            FROM battery_telemetry t
            LEFT JOIN anomalies a ON t.timestamp = a.timestamp
            ORDER BY t.timestamp DESC
            LIMIT 150
        """, conn)
        conn.close()
        return df.iloc[::-1].reset_index(drop=True)
    except Exception as e:
        print(f"Error querying telemetry: {e}")
        return pd.DataFrame()

def load_rolling_predictions():
    """Generates the actual vs predicted history using the newly trained LSTM model."""
    st.session_state.pred_history = []
    db_path = "data/battery_stream.db"
    if not os.path.exists(db_path) or not os.path.exists("models/lstm_temp.h5"):
        return
        
    try:
        # Load model and prepare sequences using TensorFlow
        import tensorflow as tf
        model = tf.keras.models.load_model("models/lstm_temp.h5")
        
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT timestamp, temp FROM battery_telemetry ORDER BY timestamp", conn)
        conn.close()
        
        if len(df) < 15:
            return
            
        temps = df['temp'].values
        # Create rolling predictions for the last 50 points
        for i in range(max(10, len(df) - 50), len(df) - 1):
            seq = temps[i-10:i].reshape(1, 10, 1)
            pred = float(model.predict(seq, verbose=0)[0][0])
            st.session_state.pred_history.append({
                'timestamp': df.iloc[i+1]['timestamp'],
                'Actual': temps[i+1],
                'Predicted': pred
            })
    except Exception as e:
        print(f"Error generating rolling prediction history: {e}")

# --- Main Layout ---
st.markdown('<div class="main-header">⚡ EV BATTERY DIAGNOSTICS & TELEMETRY</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Industrial monitoring dashboard featuring unsupervised ML anomaly detection and LSTM thermal forecasting</div>', unsafe_allow_html=True)

# --- Sidebar Controls ---
with st.sidebar:
    st.markdown("### 🛠️ Telemetry Control Center")
    st.markdown("Swap active datasets to check different battery degradation patterns.")
    
    dataset_option = st.selectbox(
        "Select Active Dataset",
        ["NASA Battery B0005", "NASA Battery B0006", "NASA Battery B0007", "NASA Battery B0018", "Upload Custom CSV Dataset"]
    )
    
    st.divider()
    
    if dataset_option == "Upload Custom CSV Dataset":
        st.markdown("**Upload Custom Battery Dataset**")
        st.markdown("CSV must contain columns: `Voltage_measured`, `Current_measured`, `Temperature_measured`, `Capacity`, `cycle`.")
        
        # Centered file uploader
        custom_file = st.file_uploader("", type=["csv"])
        if custom_file is not None:
            if st.button("🚀 Load Custom Dataset", use_container_width=True):
                success, msg = reset_db_and_load_dataset(None, custom_file=custom_file)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    else:
        bid = dataset_option.split()[-1]
        
        details = {
            "B0005": {"temp": "24°C", "charge": "CC-CV charging, 1.5A to 4.2V", "discharge": "Constant current discharge at 2A to 2.7V", "cycles": "168 cycles"},
            "B0006": {"temp": "24°C", "charge": "CC-CV charging, 1.5A to 4.2V", "discharge": "Constant current discharge at 2A to 2.5V", "cycles": "168 cycles"},
            "B0007": {"temp": "24°C", "charge": "CC-CV charging, 1.5A to 4.2V", "discharge": "Constant current discharge at 2A to 2.2V", "cycles": "168 cycles"},
            "B0018": {"temp": "24°C", "charge": "CC-CV charging, 1.5A to 4.2V", "discharge": "Constant current discharge at 2A to 2.5V", "cycles": "132 cycles (accelerated decay)"}
        }
        
        st.markdown(f"**Battery Profile: {bid}**")
        st.markdown(f"- **Ambient Temp:** {details[bid]['temp']}")
        st.markdown(f"- **Charge Scheme:** {details[bid]['charge']}")
        st.markdown(f"- **Discharge Cutoff:** {details[bid]['discharge']}")
        st.markdown(f"- **Total Lifecycle:** {details[bid]['cycles']}")
        
        if st.button(f"🚀 Initialize NASA {bid} Profile", use_container_width=True):
            success, msg = reset_db_and_load_dataset(bid)
            if success:
                st.success(msg)
            else:
                st.error(msg)

    st.divider()
    
    # --- Live Mode Toggles (OFF by default) ---
    st.markdown("### 🖥️ Dashboard Live Mode")
    live_mode = st.toggle("Enable Live Telemetry Stream", value=False)
    
    # Manual Refresh button for when Live Mode is disabled
    if not live_mode:
        if st.button("🔄 Refresh Dashboard Data", use_container_width=True):
            st.rerun()

    st.divider()
    st.markdown("### 📡 API Connection")
    try:
        res = requests.get(f"{API_URL}/metrics/latest")
        if res.status_code == 200:
            st.success("● FastAPI Service: CONNECTED")
        else:
            st.warning("● FastAPI Service: UNHEALTHY")
    except Exception:
        st.error("● FastAPI Service: DISCONNECTED")

# --- Main Dashboard Tabs ---
tab1, tab2, tab3 = st.tabs(["📊 Real-Time Monitor", "💡 LSTM Predictions & Thermal Analytics", "🧮 How Calculations Work"])

# Fetch latest metrics from backend
latest = {}
try:
    latest = requests.get(f"{API_URL}/metrics/latest").json()
except Exception:
    pass

df_history = get_telemetry_history()

with tab1:
    if not latest and df_history.empty:
        st.warning("⏳ Waiting for API connection... Please ensure uvicorn and your stream simulator are running.")
        st.info("💡 To start the telemetry stream, launch: `python -m src.stream_simulator` and `uvicorn src.api:app`.")
    else:
        # If DB is populated but latest is empty, extract latest values directly from DB history
        if not latest and not df_history.empty:
            last_row = df_history.iloc[-1]
            # Estimate anomalies in the last hour
            recent_anoms = int(df_history['is_anomaly'].iloc[-30:].sum())
            health_score = max(0, 100 - (recent_anoms * 5))
            latest = {
                'health_score': health_score,
                'voltage': last_row['voltage'],
                'current': last_row['current'],
                'temp': last_row['temp'],
                'capacity': last_row['capacity'],
                'anomaly_count_last_hour': recent_anoms
            }
            
        health_score = latest.get('health_score', 100)
        voltage = latest.get('voltage', 0.0)
        current = latest.get('current', 0.0)
        temp = latest.get('temp', 0.0)
        capacity = latest.get('capacity', 0.0)
        recent_anoms = latest.get('anomaly_count_last_hour', 0)
        
        health_glow = "glow-green" if health_score >= 80 else ("glow-orange" if health_score >= 50 else "glow-red")
        temp_glow = "glow-orange" if temp < 45 else "glow-red"
        anom_glow = "glow-green" if recent_anoms == 0 else "glow-red"
        
        # --- Live Metrics Bar ---
        m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)
        with m_col1:
            render_metric_card("❤️ Health Score", f"{health_score}", "%", "❤️", health_glow)
        with m_col2:
            render_metric_card("⚡ Voltage", f"{voltage:.3f}", "V", "⚡", "glow-blue")
        with m_col3:
            render_metric_card("🔌 Current", f"{current:.3f}", "A", "🔌", "glow-purple")
        with m_col4:
            render_metric_card("🌡️ Cell Temp", f"{temp:.2f}", "°C", "🌡️", temp_glow)
        with m_col5:
            render_metric_card("📦 Capacity", f"{capacity:.4f}", "Ah", "📦", "glow-pink")
        with m_col6:
            render_metric_card("⚠️ Recent Alerts", f"{recent_anoms}", "last hr", "⚠️", anom_glow)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- Charts Section ---
        if df_history.empty:
            st.info("Telemetry database is empty. Once you load a dataset or start the simulator, charts will appear.")
        else:
            st.markdown("### 📉 Telemetry Stream Profile")
            st.markdown("Highlighted points in <span style='color:#EF4444; font-weight:700;'>RED</span> denote anomalies detected by the unsupervised Isolation Forest model.", unsafe_allow_html=True)
            
            anom_subset = df_history[df_history['is_anomaly'] == 1]
            
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                # Voltage Line Plot
                fig_v = go.Figure()
                fig_v.add_trace(go.Scatter(x=df_history['timestamp'], y=df_history['voltage'], name='Voltage', line=dict(color='#3B82F6', width=2.5)))
                if not anom_subset.empty:
                    fig_v.add_trace(go.Scatter(x=anom_subset['timestamp'], y=anom_subset['voltage'], mode='markers',
                                              marker=dict(color='#EF4444', size=9, symbol='circle-open', line=dict(width=2)), name='Anomaly'))
                fig_v.update_layout(
                    title='⚡ Terminal Voltage (V)', 
                    paper_bgcolor='rgba(15,23,42,0.3)', 
                    plot_bgcolor='rgba(15,23,42,0.1)',
                    margin=dict(l=20, r=20, t=40, b=20), 
                    font=dict(color='#94A3B8'),
                    showlegend=False
                )
                fig_v.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
                fig_v.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
                st.plotly_chart(fig_v, use_container_width=True)
                
            with c_col2:
                # Temperature Line Plot
                fig_t = go.Figure()
                fig_t.add_trace(go.Scatter(x=df_history['timestamp'], y=df_history['temp'], name='Temperature', line=dict(color='#F59E0B', width=2.5)))
                if not anom_subset.empty:
                    fig_t.add_trace(go.Scatter(x=anom_subset['timestamp'], y=anom_subset['temp'], mode='markers',
                                              marker=dict(color='#EF4444', size=9, symbol='circle-open', line=dict(width=2)), name='Anomaly'))
                fig_t.update_layout(
                    title='🌡️ Cell Temperature (°C)', 
                    paper_bgcolor='rgba(15,23,42,0.3)', 
                    plot_bgcolor='rgba(15,23,42,0.1)',
                    margin=dict(l=20, r=20, t=40, b=20), 
                    font=dict(color='#94A3B8'),
                    showlegend=False
                )
                fig_t.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
                fig_t.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
                st.plotly_chart(fig_t, use_container_width=True)
                
            c_col3, c_col4 = st.columns(2)
            with c_col3:
                # Current Line Plot
                fig_c = go.Figure()
                fig_c.add_trace(go.Scatter(x=df_history['timestamp'], y=df_history['current'], name='Current', line=dict(color='#8B5CF6', width=2.5)))
                if not anom_subset.empty:
                    fig_c.add_trace(go.Scatter(x=anom_subset['timestamp'], y=anom_subset['current'], mode='markers',
                                              marker=dict(color='#EF4444', size=9, symbol='circle-open', line=dict(width=2)), name='Anomaly'))
                fig_c.update_layout(
                    title='🔌 Measured Current (A)', 
                    paper_bgcolor='rgba(15,23,42,0.3)', 
                    plot_bgcolor='rgba(15,23,42,0.1)',
                    margin=dict(l=20, r=20, t=40, b=20), 
                    font=dict(color='#94A3B8'),
                    showlegend=False
                )
                fig_c.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
                fig_c.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
                st.plotly_chart(fig_c, use_container_width=True)
                
            with c_col4:
                # Capacity Decay Plot
                fig_cap = go.Figure()
                fig_cap.add_trace(go.Scatter(x=df_history['timestamp'], y=df_history['capacity'], name='Capacity', line=dict(color='#EC4899', width=2.5)))
                fig_cap.update_layout(
                    title='📦 Discharge Capacity fading (Ah)', 
                    paper_bgcolor='rgba(15,23,42,0.3)', 
                    plot_bgcolor='rgba(15,23,42,0.1)',
                    margin=dict(l=20, r=20, t=40, b=20), 
                    font=dict(color='#94A3B8'),
                    showlegend=False
                )
                fig_cap.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
                fig_cap.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
                st.plotly_chart(fig_cap, use_container_width=True)

with tab2:
    st.markdown("### 🌡️ Thermal Analytics & LSTM Forecasting")
    st.markdown("LSTM Recurrent Neural Network fits on past temperature trends to predict future temperature spikes, assisting in proactive thermal runaway protection.")
    
    # Check if prediction history is in session state; if not, initialize and load
    if 'pred_history' not in st.session_state or not st.session_state.pred_history:
        load_rolling_predictions()
        
    # Append latest live updates if in live mode
    if live_mode and latest:
        current_ts = latest.get('timestamp')
        if current_ts and (not st.session_state.pred_history or st.session_state.pred_history[-1]['timestamp'] != current_ts):
            actual_t = latest.get('temp')
            pred_t = None
            try:
                pred_res = requests.get(f"{API_URL}/predict/temp").json()
                if "predicted_next_temp_celsius" in pred_res:
                    pred_t = pred_res["predicted_next_temp_celsius"]
            except Exception:
                pass
                
            if actual_t is not None and pred_t is not None:
                st.session_state.pred_history.append({
                    'timestamp': current_ts,
                    'Actual': actual_t,
                    'Predicted': pred_t
                })
                if len(st.session_state.pred_history) > 60:
                    st.session_state.pred_history.pop(0)
    
    if st.session_state.pred_history:
        df_pred = pd.DataFrame(st.session_state.pred_history)
        
        # Plotly Actual vs Predicted
        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(x=df_pred['timestamp'], y=df_pred['Actual'], name='Actual Cell Temp', line=dict(color='#F59E0B', width=2.5)))
        fig_pred.add_trace(go.Scatter(x=df_pred['timestamp'], y=df_pred['Predicted'], name='LSTM Forecast (Next Step)', line=dict(color='#10B981', width=2, dash='dash')))
        
        # Calculate error margin
        mae = (df_pred['Actual'] - df_pred['Predicted']).abs().mean()
        
        p_col1, p_col2 = st.columns([3, 1])
        
        with p_col1:
            fig_pred.update_layout(
                title='Thermal Forecast Timeline', 
                paper_bgcolor='rgba(15,23,42,0.3)', 
                plot_bgcolor='rgba(15,23,42,0.1)',
                margin=dict(l=20, r=20, t=40, b=20), 
                font=dict(color='#94A3B8'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig_pred.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
            fig_pred.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
            st.plotly_chart(fig_pred, use_container_width=True)
            
        with p_col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            render_metric_card("🎯 Model MAE", f"{mae:.3f}", "°C", "🎯", "glow-green")
            st.markdown("""
            **Forecast Analysis:**
            - A low **Mean Absolute Error (MAE)** indicates that the LSTM model has successfully captured the cells' thermal thermodynamics.
            - Divergences can indicate unusual external heating, cooling malfunctions, or high internal cell resistance.
            """)
    else:
        st.info("Waiting for LSTM model predictions... Ensure that the database contains at least 50 points so the pre-training loop executes.")

with tab3:
    st.markdown("### 🧮 What is this system calculating?")
    
    st.markdown("""
    This platform acts as an automated battery management diagnostics layer. It runs calculations across three key metrics:
    """)
    
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        st.markdown('<div class="docs-card">', unsafe_allow_html=True)
        st.markdown("#### 1. Unsupervised Anomaly Detection")
        st.markdown("""
        We employ an unsupervised **Isolation Forest (iForest)** machine learning algorithm to monitor the battery telemetry stream for anomalies.
        
        * **Features Monitored:** Terminal Voltage ($V_m$), Current ($I_m$), Cell Temperature ($T_m$), and Capacity ($Q$).
        * **Isolation Logic:** Traditional anomaly detectors model normal points and identify deviations. Isolation Forest isolates anomalies directly. It recursively partitions the dataset by randomly selecting a feature and a split value. 
        * An outlier requires fewer splits to isolate because it lies far from clusters. Thus, path length is shorter:
        """)
        
        st.markdown('<div class="math-formula">s(x, n) = 2^{- \frac{E(h(x))}{c(n)}}</div>', unsafe_allow_html=True)
        
        st.markdown("""
        Where $h(x)$ is the path length of observation $x$, $E(h(x))$ is the average path length across all isolation trees, and $c(n)$ is the average path length of an unsuccessful search in a Binary Search Tree.
        * **Contamination:** Set to $5\\%$ ($0.05$). This bounds the expectation of abnormal operations (e.g. over-voltage drops, thermal runaways, or current spikes).
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="docs-card">', unsafe_allow_html=True)
        st.markdown("#### 2. Battery State of Health (SOH)")
        st.markdown("""
        State of Health (SOH) is simulated in real-time based on the frequency of recent anomalies:
        
        * Every anomaly detected by the Isolation Forest within the **last 1 hour** causes a **5% penalty** to the health score.
        * The formula is bounding:
        """)
        st.markdown('<div class="math-formula">SOH_{score} = \max(0, 100 - (Count_{anomalies, 1hr} \\times 5))</div>', unsafe_allow_html=True)
        st.markdown("""
        This provides instant warning indicators to fleet operators if cells start showing volatile thermal or electrical behaviors repeatedly.
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_d2:
        st.markdown('<div class="docs-card">', unsafe_allow_html=True)
        st.markdown("#### 3. Long Short-Term Memory (LSTM) Thermal Forecaster")
        st.markdown("""
        To predict the next thermal step, a recurrent neural network using **LSTM cells** is implemented. 
        
        * **Memory Cell Structure:** LSTMs are equipped with gating units that decide what historical information to keep or forget. This prevents gradient vanishing during sequence training.
        """)
        
        st.markdown("""
        ```
         [Input sequence X(t-10)...X(t)] 
                       │
                       ▼
          ┌─────────────────────────┐
          │     Forget Gate (f)     │ ──► Decides what past temp to drop
          └─────────────────────────┘
                       │
                       ▼
          ┌─────────────────────────┐
          │      Input Gate (i)     │ ──► Decides what new temp trend to store
          └─────────────────────────┘
                       │
                       ▼
          ┌─────────────────────────┐
          │     Output Gate (o)     │ ──► Yields forecast temperature T(t+1)
          └─────────────────────────┘
                       │
                       ▼
              [Predicted Temp]
        ```
        """)
        
        st.markdown("""
        * **Feature Structure:** The model reads the past 10 seconds of temperature readings:
        """)
        st.markdown('<div class="math-formula">X_{seq} = [T_{t-9}, T_{t-8}, \\dots, T_{t-1}, T_t]</div>', unsafe_allow_html=True)
        st.markdown("""
        And maps it to:
        """)
        st.markdown('<div class="math-formula">y_{target} = T_{t+1}</div>', unsafe_allow_html=True)
        st.markdown("""
        * **Model Architecture:** The neural net consists of a 50-neuron LSTM layer with a ReLU activation, followed by a dense output node representing the predicted temperature in Celsius. It compiles with the Adam optimizer minimizing Mean Squared Error (MSE).
        """)
        st.markdown('</div>', unsafe_allow_html=True)

# Run st.rerun() periodically only if Live Mode is toggled ON
if live_mode:
    time.sleep(2)
    st.rerun()
