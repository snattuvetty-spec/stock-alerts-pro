import streamlit as st
import requests
import json
import os
import time
from datetime import datetime
import pandas as pd

ALERTS_FILE = "web_alerts.json"

# Page configuration
st.set_page_config(
    page_title="Stock Price Alerts",
    page_icon="📊",
    layout="wide"
)

def get_stock_price(symbol):
    """Fetch stock price using Yahoo Finance API"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        if 'chart' in data and 'result' in data['chart']:
            result = data['chart']['result'][0]
            current_price = result['meta']['regularMarketPrice']
            
            # Get additional info
            previous_close = result['meta'].get('chartPreviousClose', current_price)
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100 if previous_close else 0
            
            return {
                'price': current_price,
                'change': change,
                'change_percent': change_percent,
                'previous_close': previous_close
            }
        return None
    except Exception as e:
        return None

def load_alerts():
    """Load alerts from JSON file"""
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_alerts(alerts):
    """Save alerts to JSON file"""
    try:
        with open(ALERTS_FILE, 'w') as f:
            json.dump(alerts, f, indent=2)
        return True
    except:
        return False

# Initialize session state
if 'alerts' not in st.session_state:
    st.session_state.alerts = load_alerts()

# Header
st.title("📊 Stock Price Alert System")
st.markdown("---")

# Sidebar - Add New Alert
with st.sidebar:
    st.header("➕ Add New Alert")
    
    new_symbol = st.text_input("Stock Symbol", placeholder="e.g., AAPL", key="new_symbol").upper()
    
    if new_symbol:
        # Validate and show current price
        stock_info = get_stock_price(new_symbol)
        if stock_info:
            st.success(f"✅ Current Price: ${stock_info['price']:.2f}")
            
            new_target = st.number_input("Target Price ($)", min_value=0.01, value=float(stock_info['price']), step=0.01)
            new_type = st.selectbox("Alert Type", ["above", "below"])
            
            if st.button("Add Alert", type="primary"):
                new_alert = {
                    'symbol': new_symbol,
                    'target': new_target,
                    'type': new_type,
                    'enabled': True,
                    'created': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.alerts.append(new_alert)
                save_alerts(st.session_state.alerts)
                st.success(f"✅ Alert added for {new_symbol}!")
                time.sleep(1)
                st.rerun()
        else:
            st.error(f"❌ Invalid symbol: {new_symbol}")
    
    st.markdown("---")
    st.markdown("### Popular Stocks")
    st.markdown("""
    - **Tech**: AAPL, MSFT, GOOGL, META, NVDA
    - **Auto**: TSLA, F, GM
    - **Finance**: JPM, BAC, GS
    - **Retail**: AMZN, WMT
    """)

# Main content - Display Alerts
if not st.session_state.alerts:
    st.info("👋 No alerts yet! Add your first alert using the sidebar.")
else:
    # Auto-refresh checkbox
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"Your Alerts ({len(st.session_state.alerts)})")
    with col2:
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
    
    # Create a table of alerts with current prices
    alert_data = []
    alerts_triggered = []
    
    for idx, alert in enumerate(st.session_state.alerts):
        stock_info = get_stock_price(alert['symbol'])
        
        if stock_info:
            current_price = stock_info['price']
            change_percent = stock_info['change_percent']
            
            # Check if alert condition is met
            alert_status = "⏳ Waiting"
            if alert['type'] == 'above' and current_price >= alert['target']:
                alert_status = "🚀 TRIGGERED!"
                alerts_triggered.append(alert)
            elif alert['type'] == 'below' and current_price <= alert['target']:
                alert_status = "📉 TRIGGERED!"
                alerts_triggered.append(alert)
            
            # Color code the change
            change_color = "🟢" if stock_info['change'] >= 0 else "🔴"
            
            alert_data.append({
                'Symbol': alert['symbol'],
                'Current': f"${current_price:.2f}",
                'Change': f"{change_color} {change_percent:+.2f}%",
                'Target': f"${alert['target']:.2f}",
                'Type': alert['type'].upper(),
                'Status': alert_status,
                'Index': idx
            })
        else:
            alert_data.append({
                'Symbol': alert['symbol'],
                'Current': "Error",
                'Change': "-",
                'Target': f"${alert['target']:.2f}",
                'Type': alert['type'].upper(),
                'Status': "⚠️ Error",
                'Index': idx
            })
    
    # Display triggered alerts prominently
    if alerts_triggered:
        st.success("🎯 **ALERTS TRIGGERED!**")
        for alert in alerts_triggered:
            stock_info = get_stock_price(alert['symbol'])
            if stock_info:
                st.warning(f"**{alert['symbol']}** is ${stock_info['price']:.2f} - {alert['type'].upper()} your target of ${alert['target']:.2f}!")
    
    # Display table
    df = pd.DataFrame(alert_data)
    df_display = df.drop('Index', axis=1)
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    # Delete buttons
    st.markdown("---")
    st.subheader("🗑️ Manage Alerts")
    
    cols = st.columns(4)
    for idx, alert in enumerate(st.session_state.alerts):
        col = cols[idx % 4]
        with col:
            if st.button(f"❌ Delete {alert['symbol']}", key=f"del_{idx}"):
                st.session_state.alerts.pop(idx)
                save_alerts(st.session_state.alerts)
                st.rerun()
    
    # Clear all button
    st.markdown("---")
    if st.button("🗑️ Clear All Alerts", type="secondary"):
        st.session_state.alerts = []
        save_alerts(st.session_state.alerts)
        st.rerun()

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Auto-refresh logic
if 'auto_refresh' in locals() and auto_refresh and st.session_state.alerts:
    time.sleep(30)
    st.rerun()
