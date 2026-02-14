import streamlit as st
import requests
import json
import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

ALERTS_FILE = "web_alerts_premium.json"
SETTINGS_FILE = "user_settings.json"

# Page configuration
st.set_page_config(
    page_title="Stock Price Alerts Pro",
    page_icon="📊",
    layout="wide"
)

def load_settings():
    """Load user settings"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'email': '', 'notifications_enabled': False}
    return {'email': '', 'notifications_enabled': False}

def save_settings(settings):
    """Save user settings"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except:
        return False

def send_email_alert(recipient_email, subject, message):
    """Send email alert"""
    try:
        sender_email = os.getenv('EMAIL_SENDER')
        sender_password = os.getenv('EMAIL_PASSWORD')
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        
        if not sender_email or not sender_password:
            return False, "Email not configured. Check .env file"
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # HTML email body
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2 style="color: #2E86AB;">Stock Price Alert</h2>
                <div style="background-color: #f0f0f0; padding: 20px; border-radius: 5px;">
                    {message}
                </div>
                <p style="color: #666; font-size: 12px; margin-top: 20px;">
                    Sent from your Stock Alert System
                </p>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        return True, "Email sent successfully"
        
    except Exception as e:
        return False, f"Error sending email: {str(e)}"

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

def check_and_send_alerts(alerts, settings):
    """Check alerts and send notifications if triggered"""
    triggered_alerts = []
    
    for alert in alerts:
        if not alert.get('enabled', True):
            continue
            
        stock_info = get_stock_price(alert['symbol'])
        if not stock_info:
            continue
        
        current_price = stock_info['price']
        
        # Check if alert condition is met
        alert_triggered = False
        if alert['type'] == 'above' and current_price >= alert['target']:
            alert_triggered = True
        elif alert['type'] == 'below' and current_price <= alert['target']:
            alert_triggered = True
        
        if alert_triggered:
            # Check if we already notified for this alert recently
            last_notified = alert.get('last_notified', 0)
            time_since_last = time.time() - last_notified
            
            if time_since_last > 3600:  # Only notify once per hour
                triggered_alerts.append({
                    'symbol': alert['symbol'],
                    'current_price': current_price,
                    'target': alert['target'],
                    'type': alert['type']
                })
                
                # Update last notified time
                alert['last_notified'] = time.time()
                
                # Send email if enabled
                if settings.get('notifications_enabled') and settings.get('email'):
                    subject = f"🚀 Stock Alert: {alert['symbol']}"
                    message = f"""
                    <p><strong>{alert['symbol']}</strong> has triggered your price alert!</p>
                    <p>Current Price: <strong>${current_price:.2f}</strong></p>
                    <p>Your Target: ${alert['target']:.2f} ({alert['type']})</p>
                    <p>Change: {stock_info['change_percent']:+.2f}%</p>
                    """
                    send_email_alert(settings['email'], subject, message)
    
    if triggered_alerts:
        save_alerts(alerts)
    
    return triggered_alerts

# Initialize session state
if 'alerts' not in st.session_state:
    st.session_state.alerts = load_alerts()

if 'settings' not in st.session_state:
    st.session_state.settings = load_settings()

# Header
st.title("📊 Stock Price Alert System PRO")
st.markdown("*Real-time monitoring with email notifications*")
st.markdown("---")

# Sidebar - Settings and Add Alert
with st.sidebar:
    # Settings Section
    st.header("⚙️ Settings")
    
    user_email = st.text_input(
        "Your Email", 
        value=st.session_state.settings.get('email', ''),
        placeholder="your.email@example.com"
    )
    
    notifications_enabled = st.checkbox(
        "Enable Email Notifications",
        value=st.session_state.settings.get('notifications_enabled', False)
    )
    
    if st.button("💾 Save Settings"):
        st.session_state.settings['email'] = user_email
        st.session_state.settings['notifications_enabled'] = notifications_enabled
        if save_settings(st.session_state.settings):
            st.success("✅ Settings saved!")
        else:
            st.error("❌ Error saving settings")
    
    # Test email button
    if notifications_enabled and user_email:
        if st.button("📧 Send Test Email"):
            with st.spinner("Sending test email..."):
                success, message = send_email_alert(
                    user_email,
                    "Test Alert from Stock Alert System",
                    "<p>This is a test email. Your notifications are working!</p>"
                )
                if success:
                    st.success("✅ Test email sent! Check your inbox.")
                else:
                    st.error(f"❌ {message}")
    
    st.markdown("---")
    
    # Add New Alert Section
    st.header("➕ Add New Alert")
    
    new_symbol = st.text_input("Stock Symbol", placeholder="e.g., AAPL", key="new_symbol").upper()
    
    if new_symbol:
        stock_info = get_stock_price(new_symbol)
        if stock_info:
            st.success(f"✅ Current: ${stock_info['price']:.2f}")
            
            new_target = st.number_input(
                "Target Price ($)", 
                min_value=0.01, 
                value=float(stock_info['price']), 
                step=0.01
            )
            new_type = st.selectbox("Alert Type", ["above", "below"])
            
            if st.button("Add Alert", type="primary"):
                new_alert = {
                    'symbol': new_symbol,
                    'target': new_target,
                    'type': new_type,
                    'enabled': True,
                    'created': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'last_notified': 0
                }
                st.session_state.alerts.append(new_alert)
                save_alerts(st.session_state.alerts)
                st.success(f"✅ Alert added!")
                time.sleep(1)
                st.rerun()
        else:
            st.error(f"❌ Invalid symbol: {new_symbol}")
    
    st.markdown("---")
    st.markdown("### Popular Stocks")
    st.markdown("**Tech**: AAPL, MSFT, GOOGL\n\n**Auto**: TSLA, F\n\n**Finance**: JPM, BAC")

# Main content
if not st.session_state.alerts:
    st.info("👋 No alerts yet! Add your first alert using the sidebar.")
else:
    # Check for triggered alerts
    triggered = check_and_send_alerts(st.session_state.alerts, st.session_state.settings)
    
    if triggered:
        st.success("🎯 **ALERTS TRIGGERED!**")
        for alert in triggered:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.warning(
                    f"**{alert['symbol']}** is ${alert['current_price']:.2f} - "
                    f"{alert['type'].upper()} target of ${alert['target']:.2f}!"
                )
            with col2:
                if st.session_state.settings.get('notifications_enabled'):
                    st.caption("📧 Email sent")
    
    # Display alerts table
    st.subheader(f"Your Alerts ({len(st.session_state.alerts)})")
    
    alert_data = []
    for idx, alert in enumerate(st.session_state.alerts):
        stock_info = get_stock_price(alert['symbol'])
        
        if stock_info:
            current_price = stock_info['price']
            change_percent = stock_info['change_percent']
            
            alert_status = "⏳ Waiting"
            if alert['type'] == 'above' and current_price >= alert['target']:
                alert_status = "🚀 TRIGGERED!"
            elif alert['type'] == 'below' and current_price <= alert['target']:
                alert_status = "📉 TRIGGERED!"
            
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
    
    df = pd.DataFrame(alert_data)
    df_display = df.drop('Index', axis=1)
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    # Manage alerts
    st.markdown("---")
    st.subheader("🗑️ Manage Alerts")
    
    cols = st.columns(4)
    for idx, alert in enumerate(st.session_state.alerts):
        col = cols[idx % 4]
        with col:
            if st.button(f"❌ {alert['symbol']}", key=f"del_{idx}"):
                st.session_state.alerts.pop(idx)
                save_alerts(st.session_state.alerts)
                st.rerun()

# Footer
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col2:
    if st.session_state.settings.get('notifications_enabled'):
        st.caption("📧 Email notifications: ON")
    else:
        st.caption("📧 Email notifications: OFF")