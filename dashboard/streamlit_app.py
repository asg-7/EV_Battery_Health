import streamlit as st
import requests
import pandas as pd
import time
import plotly.express as px

API_URL = "http://localhost:8000"

st.set_page_config(page_title="EV Battery Telemetry", layout="wide")
st.title("🔋 Real‑time EV Battery Health Platform")

placeholder = st.empty()

while True:
    try:
        latest = requests.get(f"{API_URL}/metrics/latest").json()
        anomalies = requests.get(f"{API_URL}/anomalies?hours=24").json()
        
        with placeholder.container():
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Health Score", f"{latest.get('health_score', 0)}/100")
            col2.metric("Voltage (V)", f"{latest.get('voltage', 'N/A')}")
            col3.metric("Temperature (°C)", f"{latest.get('temp', 'N/A')}")
            col4.metric("Anomalies (last hour)", latest.get('anomaly_count_last_hour', 0))
            
            st.subheader("📉 Anomaly Timeline (last 24 hours)")
            if anomalies and len(anomalies) > 0:
                df_anom = pd.DataFrame(anomalies)
                if not df_anom.empty:
                    fig = px.scatter(df_anom, x='timestamp', y='cycle_id', title='Detected Anomalies')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No anomalies in last 24 hours")
            else:
                st.info("No anomalies data yet")
        
        time.sleep(5)
    except Exception as e:
        st.error(f"API not reachable: {e}")
        time.sleep(2)
