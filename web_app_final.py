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

ALERTS_FILE = "web_alerts_final.json"
SETTINGS_FILE = "user_settings_final.json"

# Page configuration
st.set_page_config(
    page_title="Stock Price Alerts Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_settings():
    """Load user settings"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {
                'email': '',
                'email_enabled': False,
                'telegram_enabled': False,
                'telegram_chat_id': '',
                'notification_method': 'both'  # 'email', 'telegram', or 'both'
            }
    return {
        'email': '',
        'email_enabled': False,
        'telegram_enabled': False,
        'telegram_chat_id': '',
        'notification_method': 'both'
    }

def save_settings(settings):
    """Save user settings"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except:
        return False

def send_telegram_message(message, chat_id=None):
    """Send message via Telegram"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not chat_id:
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            return False, "Telegram not configured. Check .env file or settings"
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            return True, "Telegram message sent"
        else:
            return False, f"Error: {response.text}"
            
    except Exception as e:
        return False, f"Error sending Telegram: {str(e)}"

def send_email_alert(recipient_email, subject, message):
    """Send email alert"""
    try:
        sender_email = os.getenv('EMAIL_SENDER')
        sender_password = os.getenv('EMAIL_PASSWORD')
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        
        if not sender_email or not sender_password:
            return False, "Email not configured. Check .env file"
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
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
        
        alert_triggered = False
        if alert['type'] == 'above' and current_price >= alert['target']:
            alert_triggered = True
        elif alert['type'] == 'below' and current_price <= alert['target']:
            alert_triggered = True
        
        if alert_triggered:
            last_notified = alert.get('last_notified', 0)
            time_since_last = time.time() - last_notified
            
            if time_since_last > 3600:
                triggered_alerts.append({
                    'symbol': alert['symbol'],
                    'current_price': current_price,
                    'target': alert['target'],
                    'type': alert['type'],
                    'change_percent': stock_info['change_percent']
                })
                
                alert['last_notified'] = time.time()
                
                notification_method = settings.get('notification_method', 'both')
                
                # Send Telegram
                if settings.get('telegram_enabled') and notification_method in ['telegram', 'both']:
                    telegram_msg = f"""
🚀 <b>Stock Alert: {alert['symbol']}</b>

💰 Current Price: <b>${current_price:.2f}</b>
🎯 Your Target: ${alert['target']:.2f} ({alert['type']})
📊 Change: {stock_info['change_percent']:+.2f}%

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                    chat_id = settings.get('telegram_chat_id') or os.getenv('TELEGRAM_CHAT_ID')
                    send_telegram_message(telegram_msg, chat_id)
                
                # Send Email
                if settings.get('email_enabled') and settings.get('email') and notification_method in ['email', 'both']:
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

if 'current_page' not in st.session_state:
    st.session_state.current_page = 'dashboard'

# Sidebar Navigation
with st.sidebar:
    st.title("📊 Stock Alerts Pro")
    st.markdown("---")
    
    if st.button("🏠 Dashboard", use_container_width=True, type="primary" if st.session_state.current_page == 'dashboard' else "secondary"):
        st.session_state.current_page = 'dashboard'
        st.rerun()
    
    if st.button("⚙️ Settings", use_container_width=True, type="primary" if st.session_state.current_page == 'settings' else "secondary"):
        st.session_state.current_page = 'settings'
        st.rerun()
    
    if st.button("➕ Add Alert", use_container_width=True, type="primary" if st.session_state.current_page == 'add_alert' else "secondary"):
        st.session_state.current_page = 'add_alert'
        st.rerun()
    
    st.markdown("---")
    st.caption(f"**{len(st.session_state.alerts)}** Active Alerts")
    
    # Status indicators
    if st.session_state.settings.get('telegram_enabled'):
        st.caption("📱 Telegram: ✅ ON")
    else:
        st.caption("📱 Telegram: ⭕ OFF")
    
    if st.session_state.settings.get('email_enabled'):
        st.caption("📧 Email: ✅ ON")
    else:
        st.caption("📧 Email: ⭕ OFF")

# SETTINGS PAGE
if st.session_state.current_page == 'settings':
    st.title("⚙️ Notification Settings")
    st.markdown("Configure how you want to receive alerts")
    st.markdown("---")
    
    # Notification Method Selection
    st.subheader("📮 Notification Method")
    notification_method = st.radio(
        "Choose how to receive alerts:",
        options=['both', 'email', 'telegram'],
        format_func=lambda x: {
            'both': '📧 + 📱 Email AND Telegram',
            'email': '📧 Email Only',
            'telegram': '📱 Telegram Only'
        }[x],
        index=['both', 'email', 'telegram'].index(st.session_state.settings.get('notification_method', 'both'))
    )
    
    st.markdown("---")
    
    # Telegram Settings
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("📱 Telegram Settings")
    with col2:
        telegram_enabled = st.toggle("Enable", value=st.session_state.settings.get('telegram_enabled', False), key="telegram_toggle")
    
    if notification_method in ['telegram', 'both']:
        telegram_chat_id = st.text_input(
            "Telegram Chat ID (Optional)",
            value=st.session_state.settings.get('telegram_chat_id', ''),
            help="Leave empty to use default from .env file",
            placeholder="7327563441"
        )
        
        st.info("ℹ️ Your Telegram bot is already configured in the .env file. You can optionally enter a different Chat ID here.")
        
        if telegram_enabled:
            if st.button("📱 Send Test Telegram", type="secondary"):
                with st.spinner("Sending test message..."):
                    chat_id = telegram_chat_id if telegram_chat_id else None
                    success, message = send_telegram_message(
                        "✅ <b>Test Alert</b>\n\nYour Telegram notifications are working perfectly!",
                        chat_id
                    )
                    if success:
                        st.success("✅ Test message sent! Check your Telegram.")
                    else:
                        st.error(f"❌ {message}")
    
    st.markdown("---")
    
    # Email Settings
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("📧 Email Settings")
    with col2:
        email_enabled = st.toggle("Enable", value=st.session_state.settings.get('email_enabled', False), key="email_toggle")
    
    if notification_method in ['email', 'both']:
        user_email = st.text_input(
            "Your Email Address",
            value=st.session_state.settings.get('email', ''),
            placeholder="your.email@example.com"
        )
        
        if email_enabled and user_email:
            if st.button("📧 Send Test Email", type="secondary"):
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
    
    # Save Button
    if st.button("💾 Save All Settings", type="primary", use_container_width=True):
        st.session_state.settings['notification_method'] = notification_method
        st.session_state.settings['telegram_enabled'] = telegram_enabled
        st.session_state.settings['telegram_chat_id'] = telegram_chat_id if notification_method in ['telegram', 'both'] else ''
        st.session_state.settings['email_enabled'] = email_enabled
        st.session_state.settings['email'] = user_email if notification_method in ['email', 'both'] else ''
        
        if save_settings(st.session_state.settings):
            st.success("✅ Settings saved successfully!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Error saving settings")

# ADD ALERT PAGE
elif st.session_state.current_page == 'add_alert':
    st.title("➕ Add New Alert")
    st.markdown("Create a new price alert for any stock")
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        new_symbol = st.text_input("Stock Symbol", placeholder="e.g., AAPL, TSLA, MSFT").upper()
    
    if new_symbol:
        stock_info = get_stock_price(new_symbol)
        if stock_info:
            with col2:
                st.metric("Current Price", f"${stock_info['price']:.2f}", f"{stock_info['change_percent']:+.2f}%")
            
            col1, col2 = st.columns(2)
            
            with col1:
                new_target = st.number_input(
                    "Target Price ($)", 
                    min_value=0.01, 
                    value=float(stock_info['price']), 
                    step=0.01
                )
            
            with col2:
                new_type = st.selectbox("Alert When Price Goes", ["above", "below"])
            
            st.markdown("---")
            
            if st.button("✅ Create Alert", type="primary", use_container_width=True):
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
                st.success(f"✅ Alert created for {new_symbol}!")
                time.sleep(1)
                st.session_state.current_page = 'dashboard'
                st.rerun()
        else:
            st.error(f"❌ Invalid stock symbol: {new_symbol}")
    
    st.markdown("---")
    st.subheader("💡 Popular Stocks")
    
    popular = {
        'Tech': ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'AMD'],
        'Auto': ['TSLA', 'F', 'GM'],
        'Finance': ['JPM', 'BAC', 'GS']
    }
    
    for category, stocks in popular.items():
        st.markdown(f"**{category}**: {', '.join(stocks)}")

# DASHBOARD PAGE
else:
    st.title("📊 Stock Price Alerts Dashboard")
    st.markdown("*Real-time monitoring with smart notifications*")
    st.markdown("---")
    
    if not st.session_state.alerts:
        st.info("👋 No alerts yet! Click **➕ Add Alert** in the sidebar to get started.")
    else:
        # Check for triggered alerts
        triggered = check_and_send_alerts(st.session_state.alerts, st.session_state.settings)
        
        if triggered:
            st.success("🎯 **ALERTS TRIGGERED!**")
            for alert in triggered:
                notification_sent = []
                method = st.session_state.settings.get('notification_method', 'both')
                
                if st.session_state.settings.get('telegram_enabled') and method in ['telegram', 'both']:
                    notification_sent.append("📱 Telegram")
                if st.session_state.settings.get('email_enabled') and method in ['email', 'both']:
                    notification_sent.append("📧 Email")
                
                st.warning(
                    f"**{alert['symbol']}** is ${alert['current_price']:.2f} - "
                    f"{alert['type'].upper()} target of ${alert['target']:.2f}! "
                    f"({', '.join(notification_sent)} sent)"
                )
        
        # Display alerts table
        st.subheader(f"Active Alerts ({len(st.session_state.alerts)})")
        
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
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
