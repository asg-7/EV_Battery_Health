import streamlit as st
import requests
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go
import os
import sqlite3
from datetime import datetime

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
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS battery_telemetry")
            cursor.execute("DROP TABLE IF EXISTS anomalies")
            conn.commit()
            conn.close()
            
        # Delete old trained model files to force retraining on new telemetry profile
        model_paths = ["models/isolation_forest.pkl", "models/lstm_temp.h5"]
        for p in model_paths:
            if os.path.exists(p):
                os.remove(p)
                
        # Clear rolling state
        if 'pred_history' in st.session_state:
            st.session_state.pred_history = []
            
        return True, f"Successfully loaded **{dataset_name}**! Telemetry DB and models have been reset. **Please restart your stream simulator script.**"
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_telemetry_history():
    db_path = "data/battery_stream.db"
    if not os.path.exists(db_path):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(db_path)
        # Perform LEFT JOIN to get anomaly status directly linked to telemetry cycles
        df = pd.read_sql_query("""
            SELECT t.timestamp, t.cycle_id, t.voltage, t.current, t.temp, t.capacity,
                   CASE WHEN a.timestamp IS NOT NULL THEN 1 ELSE 0 END as is_anomaly
            FROM battery_telemetry t
            LEFT JOIN anomalies a ON t.timestamp = a.timestamp
            ORDER BY t.timestamp DESC
            LIMIT 100
        """, conn)
        conn.close()
        # Reverse to display chronologically in the graphs
        return df.iloc[::-1].reset_index(drop=True)
    except Exception as e:
        print(f"Error querying telemetry: {e}")
        return pd.DataFrame()

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
        
        # Center uploader container inside sidebar
        custom_file = st.file_uploader("", type=["csv"])
        if custom_file is not None:
            if st.button("🚀 Load Custom Dataset", use_container_width=True):
                success, msg = reset_db_and_load_dataset(None, custom_file=custom_file)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    else:
        # Get battery ID
        bid = dataset_option.split()[-1]
        
        # Display specific details about selected NASA battery
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
        
        if st.button(f"🚀 Load NASA {bid} & Reset Stream", use_container_width=True):
            success, msg = reset_db_and_load_dataset(bid)
            if success:
                st.success(msg)
            else:
                st.error(msg)

    st.divider()
    st.markdown("### 🖥️ System Status")
    # Show active services indicators
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

# Fetch latest metrics
latest = {}
try:
    latest = requests.get(f"{API_URL}/metrics/latest").json()
except Exception:
    pass

df_history = get_telemetry_history()

with tab1:
    if not latest:
        st.warning("⏳ Waiting for API connection... Please ensure uvicorn and your stream simulator are running.")
        st.info("💡 To start the telemetry stream, launch: `python -m src.stream_simulator` and `uvicorn src.api:app`.")
    else:
        # --- Live Metrics Bar ---
        health_score = latest.get('health_score', 100)
        voltage = latest.get('voltage', 0.0)
        current = latest.get('current', 0.0)
        temp = latest.get('temp', 0.0)
        capacity = latest.get('capacity', 0.0)
        recent_anoms = latest.get('anomaly_count_last_hour', 0)
        
        health_glow = "glow-green" if health_score >= 80 else ("glow-orange" if health_score >= 50 else "glow-red")
        temp_glow = "glow-orange" if temp < 45 else "glow-red"
        anom_glow = "glow-green" if recent_anoms == 0 else "glow-red"
        
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
            st.info("Telemetry database is empty. Once you run `stream_simulator.py`, the live sensor stream charts will appear here.")
        else:
            st.markdown("### 📉 Live Telemetry Stream Profile")
            st.markdown("Highlighted points in <span style='color:#EF4444; font-weight:700;'>RED</span> denote anomalies detected in real-time by the unsupervised Isolation Forest model.", unsafe_allow_html=True)
            
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
    st.markdown("LSTM Recurrent Neural Network fits on past temperature trends to predict future temperature spikes, assisting in proactive thermal runway protection.")
    
    # Store predictions in state
    if 'pred_history' not in st.session_state:
        st.session_state.pred_history = []
        
    if latest:
        current_ts = latest.get('timestamp')
        if current_ts and (not st.session_state.pred_history or st.session_state.pred_history[-1]['timestamp'] != current_ts):
            actual_t = latest.get('temp')
            pred_t = None
            pred_status = "OK"
            msg = ""
            
            try:
                pred_res = requests.get(f"{API_URL}/predict/temp").json()
                if "predicted_next_temp_celsius" in pred_res:
                    pred_t = pred_res["predicted_next_temp_celsius"]
                elif "error" in pred_res:
                    pred_status = pred_res["error"]
                    msg = pred_res.get("message", "")
            except Exception as e:
                pred_status = "Disconnected"
                
            if actual_t is not None:
                if pred_t is not None:
                    st.session_state.pred_history.append({
                        'timestamp': current_ts,
                        'Actual': actual_t,
                        'Predicted': pred_t
                    })
                    if len(st.session_state.pred_history) > 60:
                        st.session_state.pred_history.pop(0)
                else:
                    # Output status messages on dashboard
                    if pred_status == "Training":
                        st.warning(f"⚙️ {msg}")
                    elif pred_status == "NotEnoughData":
                        st.info(f"📊 {msg}")
                    elif pred_status == "NoModel":
                        st.info("ℹ️ Telemetry database has sufficient points, but the LSTM sequential forecaster model is not ready. Querying...")
    
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
        st.info("Waiting for LSTM model predictions... Once the simulator runs and generates enough records (at least 50 points in the database), the forecast chart will activate automatically.")

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
        
        # Drawing a clean text-based diagram of LSTM gates
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

# Periodically rerun the page to pull live telemetry streams
time.sleep(2)
st.rerun()
