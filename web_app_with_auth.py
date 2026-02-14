import streamlit as st
import requests
import json
import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
import pickle
from pathlib import Path
import bcrypt

# Custom CSS for better mobile experience
st.markdown("""
<style>
    /* Make sidebar toggle more visible on mobile */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            background-color: #f0f2f6;
        }
        
        /* Highlight sidebar toggle button */
        button[kind="header"] {
            background-color: #ff4b4b !important;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
    }
    
    /* Better button spacing on mobile */
    @media (max-width: 768px) {
        .stButton button {
            width: 100%;
            margin: 5px 0;
        }
    }
</style>
""", unsafe_allow_html=True)

# Load environment variables
load_dotenv()

# File paths
USERS_FILE = "users_database.json"
ALERTS_DIR = "user_alerts"

# Ensure directories exist
os.makedirs(ALERTS_DIR, exist_ok=True)

# Page configuration
st.set_page_config(
    page_title="Stock Price Alerts Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def hash_password(password):
    """Hash a password"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    """Verify a password against a hash"""
    return bcrypt.checkpw(password.encode(), hashed.encode())

def load_users():
    """Load users database"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users):
    """Save users database"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def create_user(username, password, email, name):
    """Create a new user"""
    users = load_users()
    
    # Make username case-insensitive
    username_lower = username.lower()
    
    # Check if username already exists (case-insensitive)
    for existing_user in users.keys():
        if existing_user.lower() == username_lower:
            return False, "Username already exists"
    
    # Store with original case but check case-insensitive
    users[username] = {
        'password': hash_password(password),
        'email': email,
        'name': name,
        'created': datetime.now().isoformat()
    }
    
    save_users(users)
    return True, "User created successfully"






def authenticate_user(username, password):
    """Authenticate a user"""
    users = load_users()
    
    # Make username case-insensitive
    username_lower = username.lower()
    
    # Find user (case-insensitive search)
    for stored_username, user_data in users.items():
        if stored_username.lower() == username_lower:
            return verify_password(password, user_data['password'])
    
    return False






def get_user_file_path(username, filename):
    """Get file path for user-specific data"""
    user_dir = os.path.join(ALERTS_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, filename)

def load_user_alerts(username):
    """Load alerts for specific user"""
    filepath = get_user_file_path(username, "alerts.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_user_alerts(username, alerts):
    """Save alerts for specific user"""
    filepath = get_user_file_path(username, "alerts.json")
    try:
        with open(filepath, 'w') as f:
            json.dump(alerts, f, indent=2)
        return True
    except:
        return False

def load_user_settings(username):
    """Load settings for specific user"""
    filepath = get_user_file_path(username, "settings.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            pass
    
    # Default settings with trial info
    return {
        'email': '',
        'email_enabled': False,
        'telegram_enabled': False,
        'telegram_chat_id': '',
        'notification_method': 'both',
        'account_created': datetime.now().isoformat(),
        'trial_ends': (datetime.now() + timedelta(days=7)).isoformat(),
        'premium': False,
        'premium_price': None,
        'premium_activated': None
    }

def save_user_settings(username, settings):
    """Save settings for specific user"""
    filepath = get_user_file_path(username, "settings.json")
    try:
        with open(filepath, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except:
        return False

def get_account_status(settings):
    """Determine account status and pricing"""
    account_created = datetime.fromisoformat(settings['account_created'])
    trial_ends = datetime.fromisoformat(settings['trial_ends'])
    now = datetime.now()
    
    if settings.get('premium'):
        return {
            'status': 'premium',
            'message': '✨ Premium Account',
            'price_paid': settings.get('premium_price', 'N/A'),
            'days_remaining': None
        }
    
    # Check if trial is active
    if now < trial_ends:
        days_remaining = (trial_ends - now).days
        return {
            'status': 'trial',
            'message': f'🎁 Free Trial ({days_remaining} days left)',
            'days_remaining': days_remaining,
            'upgrade_price': 2
        }
    
    # Trial ended
    days_since_trial_ended = (now - trial_ends).days
    
    if days_since_trial_ended <= 10:
        return {
            'status': 'expired_early',
            'message': f'⏰ Trial Expired - Special Offer! ({10 - days_since_trial_ended} days left)',
            'days_since_expired': days_since_trial_ended,
            'upgrade_price': 2
        }
    else:
        return {
            'status': 'expired_late',
            'message': '🔒 Trial Expired - Upgrade Required',
            'upgrade_price': 4
        }

def upgrade_to_premium(username, settings, price):
    """Upgrade user to premium"""
    settings['premium'] = True
    settings['premium_price'] = price
    settings['premium_activated'] = datetime.now().isoformat()
    save_user_settings(username, settings)
    return True

def send_telegram_message(message, chat_id=None):
    """Send message via Telegram"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not chat_id:
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            return False, "Telegram not configured"
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
        response = requests.post(url, data=data, timeout=10)
        
        return response.status_code == 200, "Sent"
    except Exception as e:
        return False, str(e)

def send_email_alert(recipient_email, subject, message):
    """Send email alert"""
    try:
        sender_email = os.getenv('EMAIL_SENDER')
        sender_password = os.getenv('EMAIL_PASSWORD')
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        
        if not sender_email or not sender_password:
            return False, "Email not configured"
        
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
            </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        return True, "Email sent"
    except Exception as e:
        return False, str(e)

def get_stock_price(symbol):
    """Fetch stock price"""
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
    except:
        return None

def check_and_send_alerts(alerts, settings):
    """Check alerts and send notifications"""
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
            if time.time() - last_notified > 3600:
                triggered_alerts.append({
                    'symbol': alert['symbol'],
                    'current_price': current_price,
                    'target': alert['target'],
                    'type': alert['type'],
                    'change_percent': stock_info['change_percent']
                })
                
                alert['last_notified'] = time.time()
                
                method = settings.get('notification_method', 'both')
                
                if settings.get('telegram_enabled') and method in ['telegram', 'both']:
                    telegram_msg = f"""🚀 <b>Stock Alert: {alert['symbol']}</b>

💰 Current Price: <b>${current_price:.2f}</b>
🎯 Your Target: ${alert['target']:.2f} ({alert['type']})
📊 Change: {stock_info['change_percent']:+.2f}%

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                    chat_id = settings.get('telegram_chat_id') or None
                    send_telegram_message(telegram_msg, chat_id)
                
                if settings.get('email_enabled') and settings.get('email') and method in ['email', 'both']:
                    subject = f"🚀 Stock Alert: {alert['symbol']}"
                    
                    # Determine color based on change
                    change_color = 'green' if stock_info['change_percent'] >= 0 else 'red'
                    
                    email_message = f"""
                    <p><strong>🚀 Stock Alert: {alert['symbol']}</strong></p>
                    <hr>
                    <p><strong>💰 Current Price:</strong> <span style="font-size: 18px; color: #2E86AB;">${current_price:.2f}</span></p>
                    <p><strong>🎯 Your Target:</strong> ${alert['target']:.2f} ({alert['type']})</p>
                    <p><strong>📊 Change:</strong> <span style="color: {change_color};">{stock_info['change_percent']:+.2f}%</span></p>
                    <hr>
                    <p style="color: #666; font-size: 12px;">⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    """
                    
                    send_email_alert(settings['email'], subject, email_message)





    
    return triggered_alerts

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'show_signup' not in st.session_state:
    st.session_state.show_signup = False

# Login/Signup UI
if not st.session_state.logged_in:
    st.title("📊 Stock Price Alerts Pro")
    st.markdown("### Welcome! Please login or create an account")
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
    
    with tab1:
        st.subheader("Login to Your Account")
        login_username = st.text_input("Username", key="login_user")
        login_password = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Login", type="primary", use_container_width=True):
            users = load_users()
            
            # Find the actual stored username (case-insensitive)
            actual_username = None
            for stored_user in users.keys():
                if stored_user.lower() == login_username.lower():
                    actual_username = stored_user
                    break
            
            if actual_username and authenticate_user(login_username, login_password):
                st.session_state.logged_in = True
                st.session_state.username = actual_username
                st.session_state.name = users[actual_username]['name']
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
    
    with tab2:
        st.subheader("Create New Account")
        new_name = st.text_input("Full Name", key="signup_name")
        new_email = st.text_input("Email", key="signup_email")
        new_username = st.text_input("Username", key="signup_user")
        new_password = st.text_input("Password", type="password", key="signup_pass")
        new_password_confirm = st.text_input("Confirm Password", type="password", key="signup_pass_confirm")
        
        if st.button("Create Account", type="primary", use_container_width=True):
            if not new_name or not new_email or not new_username or not new_password:
                st.error("❌ Please fill all fields")
            elif new_password != new_password_confirm:
                st.error("❌ Passwords don't match")
            elif len(new_password) < 6:
                st.error("❌ Password must be at least 6 characters")
            else:
                success, message = create_user(new_username, new_password, new_email, new_name)
                if success:
                    st.success("✅ Account created! Please login.")
                else:
                    st.error(f"❌ {message}")

else:
    # User is logged in
    username = st.session_state.username
    name = st.session_state.name
    
    # Initialize session state variables
    if 'current_page' not in st.session_state or st.session_state.current_page is None:
        st.session_state.current_page = 'dashboard'
    
    if 'user_alerts' not in st.session_state:
        st.session_state.user_alerts = load_user_alerts(username)
    
    if 'user_settings' not in st.session_state:
        st.session_state.user_settings = load_user_settings(username)
    
    if 'show_mobile_hint' not in st.session_state:
        st.session_state.show_mobile_hint = True
    
    # Get account status
    account_status = get_account_status(st.session_state.user_settings)
    
    # Sidebar
    with st.sidebar:
        
        
        st.title(f"👋 {name}")
        
        # Account Status
        st.info(account_status['message'])
        
        if not st.session_state.user_settings.get('premium'):
            st.warning(f"💰 Upgrade: ${account_status['upgrade_price']}/month")
            if st.button("⭐ Upgrade to Premium", use_container_width=True, type="primary"):
                st.session_state.current_page = 'upgrade'
                st.rerun()
        
        st.markdown("---")
        
        # Navigation
        if st.button("🏠 Dashboard", use_container_width=True):
            st.session_state.current_page = 'dashboard'
            st.rerun()
        
        if st.button("⚙️ Settings", use_container_width=True):
            st.session_state.current_page = 'settings'
            st.rerun()
        
        if st.button("➕ Add Alert", use_container_width=True):
            st.session_state.current_page = 'add_alert'
            st.rerun()
        
        st.markdown("---")
        
        # Stats
        alert_count = len(st.session_state.user_alerts)
        alert_limit = 10
        
        st.caption(f"📊 Alerts: {alert_count}/{alert_limit if not st.session_state.user_settings.get('premium') else '∞'}")
        
        if st.session_state.user_settings.get('telegram_enabled'):
            st.caption("📱 Telegram: ✅")
        else:
            st.caption("📱 Telegram: ⭕")
        
        if st.session_state.user_settings.get('email_enabled'):
            st.caption("📧 Email: ✅")
        else:
            st.caption("📧 Email: ⭕")
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.name = None
            st.rerun()
    
    # UPGRADE PAGE
    if st.session_state.current_page == 'upgrade':
        st.title("⭐ Upgrade to Premium")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### Why Upgrade?")
            st.markdown("""
            **Premium Features:**
            - ✅ Unlimited stock alerts
            - ✅ Priority notifications (faster)
            - ✅ Email + Telegram notifications
            - ✅ Price history charts (coming soon)
            - ✅ Multiple watchlists (coming soon)
            - ✅ Export to CSV (coming soon)
            - ✅ Priority support
            """)
        
        with col2:
            st.markdown("### Your Price")
            price = account_status['upgrade_price']
            
            if price == 2:
                st.success(f"### ${price}/month")
                st.caption("🎉 Special early upgrade price!")
            else:
                st.info(f"### ${price}/month")
            
            st.markdown("---")
            
            st.warning("⚠️ This is a demo. Payment not implemented yet.")
            
            if st.button("✅ Activate Premium (Demo)", type="primary", use_container_width=True):
                upgrade_to_premium(username, st.session_state.user_settings, price)
                st.success("🎉 Premium activated!")
                time.sleep(2)
                st.session_state.current_page = 'dashboard'
                st.rerun()
    
    # SETTINGS PAGE
    elif st.session_state.current_page == 'settings':
        st.title("⚙️ Settings")
        
        # Notification Method
        st.subheader("📮 Notification Method")
        method = st.radio(
            "How to receive alerts:",
            ['both', 'email', 'telegram'],
            format_func=lambda x: {'both': '📧+📱 Both', 'email': '📧 Email Only', 'telegram': '📱 Telegram Only'}[x],
            index=['both', 'email', 'telegram'].index(st.session_state.user_settings.get('notification_method', 'both'))
        )
        
        st.markdown("---")
        
        # Telegram
        st.subheader("📱 Telegram")
        telegram_enabled = st.toggle("Enable Telegram", value=st.session_state.user_settings.get('telegram_enabled', False))
        
        # Help section for getting Chat ID
        with st.expander("ℹ️ How to get your Telegram Chat ID"):
            st.markdown("""
            **Step 1: Create Your Bot Connection**
            1. Open Telegram on your phone
            2. Search for: `@MyStockAlerts_bot`
            3. Click **START** and send any message (like "hello")
            
            **Step 2: Get Your Chat ID**
            
            **Option A - Easy Way:**
            1. Search for: `@userinfobot` in Telegram
            2. Start a chat and send any message
            3. The bot will reply with your **Chat ID** (a number like `7327563441`)
            4. Copy that number and paste it below ⬇️
            
            **Option B - Manual Way:**
            1. Send a message to our bot: `@MyStockAlerts_bot`
            2. Open this link in your browser: `https://api.telegram.org/bot8386931280:AAHacghVM73rKOCmKKaDTX-OEiX15DJ_OQE/getUpdates`
            3. Look for `"chat":{"id":123456789`
            4. Copy that number
            
            ---
            
            **🎁 Pro Tip:** Leave this empty to use the default bot settings (works for most users!)
            """)
        
        telegram_chat_id = st.text_input(
            "Telegram Chat ID (Optional)", 
            value=st.session_state.user_settings.get('telegram_chat_id', ''),
            placeholder="Leave empty for default bot, or enter your Chat ID",
            help="Get your Chat ID from @userinfobot on Telegram"
        )
        
        if telegram_enabled:
            if st.button("📱 Send Test Telegram"):
                success, _ = send_telegram_message("✅ Test from Stock Alerts!", telegram_chat_id or None)
                if success:
                    st.success("✅ Message sent! Check your Telegram.")
                else:
                    st.error("❌ Failed to send. Make sure you've started a chat with the bot first.")
        





        # Email
        st.subheader("📧 Email")
        email_enabled = st.toggle("Enable Email", value=st.session_state.user_settings.get('email_enabled', False))
        user_email = st.text_input("Email", value=st.session_state.user_settings.get('email', ''))
        
        if email_enabled and user_email:
            if st.button("Test Email"):
                success, _ = send_email_alert(user_email, "Test", "<p>Test email!</p>")
                if success:
                    st.success("✅ Sent!")
                else:
                    st.error("❌ Failed")
        
        st.markdown("---")
        
        if st.button("💾 Save Settings", type="primary"):
            st.session_state.user_settings['notification_method'] = method
            st.session_state.user_settings['telegram_enabled'] = telegram_enabled
            st.session_state.user_settings['telegram_chat_id'] = telegram_chat_id
            st.session_state.user_settings['email_enabled'] = email_enabled
            st.session_state.user_settings['email'] = user_email
            save_user_settings(username, st.session_state.user_settings)
            st.success("✅ Saved!")
    
    # ADD ALERT PAGE
    elif st.session_state.current_page == 'add_alert':
        st.title("➕ Add Alert")
        
        # Check limit
        alert_limit = 10
        current_count = len(st.session_state.user_alerts)
        
        if current_count >= alert_limit and not st.session_state.user_settings.get('premium'):
            st.error(f"🔒 Alert limit reached ({alert_limit} alerts)")
            st.info("Upgrade to Premium for unlimited alerts!")
            if st.button("⭐ Upgrade Now"):
                st.session_state.current_page = 'upgrade'
                st.rerun()
        else:
            st.info(f"Alerts: {current_count}/{alert_limit if not st.session_state.user_settings.get('premium') else '∞'}")
            
            symbol = st.text_input("Stock Symbol", placeholder="AAPL").upper()
            
            if symbol:
                stock_info = get_stock_price(symbol)
                if stock_info:
                    st.metric("Current Price", f"${stock_info['price']:.2f}", f"{stock_info['change_percent']:+.2f}%")
                    
                    target = st.number_input("Target Price", min_value=0.01, value=float(stock_info['price']))
                    alert_type = st.selectbox("Alert When", ["above", "below"])
                    
                    if st.button("Create Alert", type="primary"):
                        new_alert = {
                            'symbol': symbol,
                            'target': target,
                            'type': alert_type,
                            'enabled': True,
                            'created': datetime.now().isoformat(),
                            'last_notified': 0
                        }
                        st.session_state.user_alerts.append(new_alert)
                        save_user_alerts(username, st.session_state.user_alerts)
                        st.success(f"✅ Alert created for {symbol}!")
                        time.sleep(1)
                        st.session_state.current_page = 'dashboard'
                        st.rerun()
                else:
                    st.error("Invalid symbol")
    
    # DASHBOARD
    else:
        st.title("📊 Dashboard")
        
        if not st.session_state.user_alerts:
            st.info("No alerts yet! Click **➕ Add Alert** to get started.")
        else:
            # Check alerts
            triggered = check_and_send_alerts(st.session_state.user_alerts, st.session_state.user_settings)
            
            if triggered:
                st.success("🎯 ALERTS TRIGGERED!")
                for alert in triggered:
                    st.warning(f"**{alert['symbol']}**: ${alert['current_price']:.2f}")
            
            # Display table
            alert_data = []
            for idx, alert in enumerate(st.session_state.user_alerts):
                stock_info = get_stock_price(alert['symbol'])
                if stock_info:
                    status = "⏳ Waiting"
                    if alert['type'] == 'above' and stock_info['price'] >= alert['target']:
                        status = "🚀 TRIGGERED!"
                    elif alert['type'] == 'below' and stock_info['price'] <= alert['target']:
                        status = "📉 TRIGGERED!"
                    
                    alert_data.append({
                        'Symbol': alert['symbol'],
                        'Current': f"${stock_info['price']:.2f}",
                        'Target': f"${alert['target']:.2f}",
                        'Type': alert['type'].upper(),
                        'Status': status
                    })
            
            df = pd.DataFrame(alert_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Delete buttons
            st.markdown("---")
            st.subheader("Manage Alerts")
            cols = st.columns(4)
            for idx, alert in enumerate(st.session_state.user_alerts):
                col = cols[idx % 4]
                with col:
                    if st.button(f"❌ {alert['symbol']}", key=f"del_{idx}"):
                        st.session_state.user_alerts.pop(idx)
                        save_user_alerts(username, st.session_state.user_alerts)
                        st.rerun()