import streamlit as st
import requests
import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import pandas as pd
import bcrypt
from supabase import create_client, Client

# Load secrets - works on both local (.env) and Streamlit Cloud (st.secrets)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.getenv(key, default)

# Initialize Supabase (Split Access Model)
url = get_secret("SUPABASE_URL")

# 🔒 Admin key (secret)
admin_key = get_secret("SUPABASE_KEY")

# 🔓 Public key (publishable)
public_key = get_secret("SUPABASE_PUBLIC_KEY")

# Admin client - full access
supabase_admin: Client = create_client(url, admin_key)

# Public client - limited access
supabase_public: Client = create_client(url, public_key)
supabase = supabase_admin

# Page config
st.set_page_config(
    page_title="Stock Price Alerts Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Auto-refresh every 2 minutes
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

current_time = time.time()
if current_time - st.session_state.last_refresh > 120:
    st.session_state.last_refresh = current_time
    st.rerun()

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_user(username, password, email, name):
    try:
        trial_ends = (datetime.now() + timedelta(days=21)).isoformat()
        supabase.table('users').insert({
            'username': username,
            'password_hash': hash_password(password),
            'email': email,
            'name': name,
            'trial_ends': trial_ends,
            'premium': False
        }).execute()
        supabase.table('user_settings').insert({
            'username': username,
            'email': '',
            'email_enabled': False,
            'telegram_enabled': False,
            'notification_method': 'both'
        }).execute()
        return True, "User created successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"

def authenticate_user(username, password):
    try:
        # Case-insensitive username search
        result = supabase_admin.table('users').select('*').execute()
        for user in result.data:
            if user['username'].lower() == username.lower():
                if verify_password(password, user['password_hash']):
                    return True, user
        return False, None
    except:
        return False, None

def get_user_alerts(username):
    result = supabase_admin.table('alerts').select('*').eq('username', username).execute()
    return result.data

def save_alert(username, alert_data):
    try:
        supabase.table('alerts').insert({
            'username': username,
            'symbol': alert_data['symbol'],
            'target': alert_data['target'],
            'type': alert_data['type'],
            'enabled': True
        }).execute()
        return True
    except:
        return False

def delete_alert(alert_id):
    try:
        supabase.table('alerts').delete().eq('id', alert_id).execute()
        return True
    except:
        return False

def get_user_settings(username):
    result = supabase_public.table('user_settings').select('*').eq('username', username).execute()
    if result.data:
        return result.data[0]
    return None

def update_user_settings(username, settings):
    try:
        supabase.table('user_settings').update(settings).eq('username', username).execute()
        return True
    except:
        return False

def get_account_status(user):
    trial_ends = datetime.fromisoformat(user['trial_ends'])
    now = datetime.now()

    if user['premium']:
        return {
            'status': 'premium',
            'message': '✨ Premium Account',
            'price_paid': user.get('premium_price', 'N/A')
        }

    if now < trial_ends:
        days_remaining = (trial_ends - now).days
        return {
            'status': 'trial',
            'message': f'🎁 Free Trial ({days_remaining} days left)',
            'upgrade_price': 2
        }

    days_since_expired = (now - trial_ends).days

    if days_since_expired <= 30:
        return {
            'status': 'expired_early',
            'message': f'⏰ Special Offer! ({30 - days_since_expired} days left)',
            'upgrade_price': 2
        }
    else:
        return {
            'status': 'expired_late',
            'message': '🔒 Trial Expired',
            'upgrade_price': 4
        }

def upgrade_to_premium(username, price):
    try:
        supabase.table('users').update({
            'premium': True,
            'premium_price': price,
            'premium_activated': datetime.now().isoformat()
        }).eq('username', username).execute()
        return True
    except:
        return False

def send_telegram_message(message, chat_id=None):
    try:
        bot_token = get_secret('TELEGRAM_BOT_TOKEN')
        if not chat_id:
            chat_id = get_secret('TELEGRAM_CHAT_ID')
        if not bot_token or not chat_id:
            return False, "Telegram not configured"
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200, "Sent"
    except Exception as e:
        return False, str(e)

def send_email_alert(recipient_email, subject, message):
    try:
        sender_email = get_secret('EMAIL_SENDER')
        sender_password = get_secret('EMAIL_PASSWORD')
        smtp_server = get_secret('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(get_secret('SMTP_PORT', 587))
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
                'change_percent': change_percent
            }
        return None
    except:
        return None

def check_and_send_alerts(alerts, settings, username):
    triggered = []
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
            last_notified = alert.get('last_notified')
            if last_notified:
                last_time = datetime.fromisoformat(last_notified)
                if (datetime.now() - last_time).seconds < 3600:
                    continue
            triggered.append({
                'symbol': alert['symbol'],
                'current_price': current_price,
                'target': alert['target'],
                'type': alert['type'],
                'change_percent': stock_info['change_percent']
            })
            supabase.table('alerts').update({
                'last_notified': datetime.now().isoformat()
            }).eq('id', alert['id']).execute()
            supabase.table('alert_history').insert({
                'username': username,
                'symbol': alert['symbol'],
                'price': current_price,
                'target': alert['target'],
                'type': alert['type']
            }).execute()
            method = settings.get('notification_method', 'both')
            if settings.get('telegram_enabled') and method in ['telegram', 'both']:
                msg = f"""🚀 <b>Stock Alert: {alert['symbol']}</b>

💰 Current Price: <b>${current_price:.2f}</b>
🎯 Your Target: ${alert['target']:.2f} ({alert['type']})
📊 Change: {stock_info['change_percent']:+.2f}%

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                chat_id = settings.get('telegram_chat_id') or None
                send_telegram_message(msg, chat_id)
            if settings.get('email_enabled') and settings.get('email') and method in ['email', 'both']:
                subject = f"🚀 Stock Alert: {alert['symbol']}"
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
    return triggered


# ============================================================
# SESSION STATE INIT
# ============================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Mobile-friendly CSS
st.markdown("""
<style>
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 2rem !important;
        }
        .stButton button {
            min-height: 44px !important;
        }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# NOT LOGGED IN - Show Login/Signup
# ============================================================
if not st.session_state.logged_in:
    st.title("📊 Stock Price Alerts Pro")
    st.markdown("### Welcome! Please login or create an account")

    with st.expander("⚠️ Important Disclaimer - Please Read"):
        st.markdown("""
        **DISCLAIMER - Natts Digital**

        Stock Alerts Pro is a **price notification service only**.

        - ❌ We do NOT provide financial advice
        - ❌ We do NOT recommend buying or selling any securities
        - ❌ We are NOT an Australian Financial Services (AFS) licensee
        - ✅ We ONLY notify you when stocks reach your chosen price points

        All investment decisions are made solely by you.
        Past price movements do not guarantee future performance.
        Always consult a licensed financial advisor before making any investment decisions.

        **Natts Digital is a technology company, not a financial services provider.**
        """)

    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])

    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            login_username = st.text_input("Username", key="login_user", autocomplete="username")
            login_password = st.text_input("Password", type="password", key="login_pass", autocomplete="current-password")
            submit = st.form_submit_button("🔐 Login", type="primary", use_container_width=True)

        if submit:
            success, user = authenticate_user(login_username, login_password)
            if success:
                st.session_state.logged_in = True
                st.session_state.username = user['username']
                st.session_state.user = user
                st.rerun()
            else:
                st.error("❌ Invalid credentials")

    with tab2:
        st.subheader("Create Account")
        new_name = st.text_input("Full Name", key="signup_name")
        new_email = st.text_input("Email", key="signup_email")
        new_username = st.text_input("Username", key="signup_user")
        new_password = st.text_input("Password", type="password", key="signup_pass")
        new_password_confirm = st.text_input("Confirm Password", type="password", key="signup_pass_confirm")

        if st.button("Create Account", type="primary", use_container_width=True):
            if not all([new_name, new_email, new_username, new_password]):
                st.error("❌ Please fill all fields")
            elif new_password != new_password_confirm:
                st.error("❌ Passwords don't match")
            elif len(new_password) < 6:
                st.error("❌ Password must be 6+ characters")
            else:
                success, message = create_user(new_username, new_password, new_email, new_name)
                if success:
                    st.success("✅ Account created! Please login.")
                else:
                    st.error(f"❌ {message}")


# ============================================================
# LOGGED IN - Main App
# ============================================================
else:
    # Safety checks
    if 'username' not in st.session_state or st.session_state.username is None:
        st.session_state.logged_in = False
        st.rerun()

    if 'user' not in st.session_state or st.session_state.user is None:
        st.session_state.logged_in = False
        st.rerun()

    username = st.session_state.username
    user = st.session_state.user

    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'

    account_status = get_account_status(user)

    # ============================================================
    # NAVIGATION - Dropdown on mobile, Sidebar on desktop
    # ============================================================
    alerts_count = get_user_alerts(username)
    alert_limit = 10

    # Mobile top nav using selectbox (always works, no JS needed)
    st.markdown("""
    <style>
    .mobile-only { display: none; }
    .desktop-only { display: block; }
    @media (max-width: 768px) {
        .mobile-only { display: block; }
        section[data-testid="stSidebar"] { display: none !important; }
    }
    </style>
    """, unsafe_allow_html=True)

    # Mobile top bar - pure HTML so it stays horizontal always
    page = st.session_state.get('current_page', 'dashboard')

    def nav_style(p):
        if page == p:
            return "background:#2E86AB;color:white;border:none;border-radius:8px;padding:8px 0;width:100%;font-size:22px;cursor:pointer;"
        return "background:#f0f2f6;color:#555;border:none;border-radius:8px;padding:8px 0;width:100%;font-size:22px;cursor:pointer;"

    st.markdown(f"""
    <style>
    .mobile-topnav {{
        display: none;
    }}
    @media (max-width: 768px) {{
        .mobile-topnav {{
            display: grid;
            grid-template-columns: 2fr 1fr 1fr 1fr 1fr;
            gap: 6px;
            padding: 8px 4px 12px 4px;
            background: white;
            border-bottom: 1px solid #eee;
            margin-bottom: 10px;
            align-items: center;
        }}
        .mobile-topnav .username {{
            font-weight: bold;
            font-size: 14px;
            color: #333;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .mobile-topnav .nav-btn {{
            background: #f0f2f6;
            border: none;
            border-radius: 8px;
            padding: 10px 4px;
            font-size: 20px;
            text-align: center;
            cursor: pointer;
            text-decoration: none;
            display: block;
        }}
        .mobile-topnav .nav-btn.active {{
            background: #2E86AB;
        }}
        section[data-testid="stSidebar"] {{
            display: none !important;
        }}
    }}
    </style>

    <div class="mobile-topnav">
        <div class="username">👋 {user['name'].split()[0]}</div>
        <a class="nav-btn {'active' if page == 'dashboard' else ''}"
           href="?page=dashboard">🏠</a>
        <a class="nav-btn {'active' if page == 'add_alert' else ''}"
           href="?page=add_alert">➕</a>
        <a class="nav-btn {'active' if page == 'settings' else ''}"
           href="?page=settings">⚙️</a>
        <a class="nav-btn" href="?page=logout">🚪</a>
    </div>
    """, unsafe_allow_html=True)

    # Handle URL params from mobile nav
    params = st.query_params
    if 'page' in params:
        nav = params['page']
        st.query_params.clear()
        if nav == 'logout':
            st.session_state.logged_in = False
        else:
            st.session_state.current_page = nav
        st.rerun()

    # Sidebar for desktop
    with st.sidebar:
        st.title(f"👋 {user['name']}")
        st.info(account_status['message'])

        if not user['premium']:
            st.warning(f"💰 Upgrade: ${account_status['upgrade_price']}/month")
            if st.button("⭐ Upgrade", use_container_width=True, type="primary"):
                st.session_state.current_page = 'upgrade'
                st.rerun()

        st.markdown("---")

        if st.button("🏠 Dashboard", use_container_width=True):
            st.session_state.current_page = 'dashboard'
            st.rerun()

        if st.button("➕ Add Alert", use_container_width=True):
            st.session_state.current_page = 'add_alert'
            st.rerun()

        if st.button("⚙️ Settings", use_container_width=True):
            st.session_state.current_page = 'settings'
            st.rerun()

        st.markdown("---")
        st.caption(f"📊 Alerts: {len(alerts_count)}/{alert_limit if not user['premium'] else '∞'}")
        st.markdown("---")

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # ---- UPGRADE PAGE ----
    if st.session_state.current_page == 'upgrade':
        st.title("⭐ Upgrade to Premium")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("### Premium Features")
            st.markdown("""
            - ✅ Unlimited alerts
            - ✅ Priority notifications
            - ✅ Email + Telegram
            - ✅ Price charts (coming soon)
            - ✅ Multiple watchlists (coming soon)
            """)
        with col2:
            price = account_status['upgrade_price']
            st.success(f"### ${price}/month")
            st.warning("⚠️ Demo - Payment not implemented")
            if st.button("✅ Activate Premium (Demo)", type="primary"):
                upgrade_to_premium(username, price)
                st.success("🎉 Premium activated!")
                time.sleep(2)
                st.rerun()

    # ---- SETTINGS PAGE ----
    elif st.session_state.current_page == 'settings':
        st.title("⚙️ Settings")
        settings = get_user_settings(username)
        method = st.radio(
            "Notification Method:",
            ['both', 'email', 'telegram'],
            format_func=lambda x: {'both': '📧+📱 Both', 'email': '📧 Email', 'telegram': '📱 Telegram'}[x],
            index=['both', 'email', 'telegram'].index(settings.get('notification_method', 'both'))
        )
        st.markdown("---")
        st.subheader("📱 Telegram")
        telegram_enabled = st.toggle("Enable", value=settings.get('telegram_enabled', False))
        with st.expander("ℹ️ How to get Chat ID"):
            st.markdown("""
            1. Search for `@userinfobot` on Telegram
            2. Send any message
            3. Bot replies with your Chat ID
            4. Paste it below (optional)
            """)
        telegram_chat_id = st.text_input("Chat ID (optional)", value=settings.get('telegram_chat_id', ''))
        if telegram_enabled:
            if st.button("Test Telegram"):
                success, _ = send_telegram_message("✅ Test!", telegram_chat_id or None)
                if success:
                    st.success("✅ Sent!")
                else:
                    st.error("❌ Failed")
        st.markdown("---")
        st.subheader("📧 Email")
        email_enabled = st.toggle("Enable Email", value=settings.get('email_enabled', False))
        if email_enabled:
            user_email = st.text_input("Your Email", value=settings.get('email', ''))
            if user_email and st.button("Test Email"):
                success, _ = send_email_alert(user_email, "Test", "<p>Test!</p>")
                if success:
                    st.success("✅ Sent!")
                else:
                    st.error("❌ Failed")
        else:
            user_email = ""
        st.markdown("---")
        if st.button("💾 Save", type="primary"):
            update_user_settings(username, {
                'notification_method': method,
                'telegram_enabled': telegram_enabled,
                'telegram_chat_id': telegram_chat_id,
                'email_enabled': email_enabled,
                'email': user_email
            })
            st.success("✅ Saved!")

    # ---- ADD ALERT PAGE ----
    elif st.session_state.current_page == 'add_alert':
        st.title("➕ Add Alert")
        alerts = get_user_alerts(username)
        alert_limit = 10
        if len(alerts) >= alert_limit and not user['premium']:
            st.error(f"🔒 Limit reached ({alert_limit})")
            if st.button("⭐ Upgrade"):
                st.session_state.current_page = 'upgrade'
                st.rerun()
        else:
            symbol = st.text_input("Symbol", placeholder="AAPL").upper()
            if symbol:
                stock_info = get_stock_price(symbol)
                if stock_info:
                    st.metric("Current", f"${stock_info['price']:.2f}", f"{stock_info['change_percent']:+.2f}%")
                    target = st.number_input("Target Price", min_value=0.01, value=float(stock_info['price']))
                    alert_type = st.selectbox("Alert When", ["above", "below"])
                    if st.button("Create", type="primary"):
                        if save_alert(username, {
                            'symbol': symbol,
                            'target': target,
                            'type': alert_type
                        }):
                            st.success("✅ Created!")
                            time.sleep(1)
                            st.session_state.current_page = 'dashboard'
                            st.rerun()
                else:
                    st.error("Invalid symbol")

    # ---- DASHBOARD ----
    else:
        st.title("📊 Dashboard")
        st.caption("⏱️ Auto-refreshes every 2 minutes")

        alerts = get_user_alerts(username)

        if not alerts:
            st.info("No alerts set yet! Tap ➕ Add Alert to get started.")
        else:
            settings = get_user_settings(username)
            triggered = check_and_send_alerts(alerts, settings, username)

            if triggered:
                st.success("🎯 ALERTS TRIGGERED!")
                for alert in triggered:
                    st.warning(f"**{alert['symbol']}**: ${alert['current_price']:.2f}")

            # Build alert data list
            alert_list = []

            for idx, alert in enumerate(alerts):
                stock_info = get_stock_price(alert['symbol'])
                if not stock_info:
                    continue

                current_price = stock_info['price']
                change_pct = stock_info['change_percent']
                change_color = "#27ae60" if change_pct >= 0 else "#e74c3c"
                change_arrow = "▲" if change_pct >= 0 else "▼"

                status = "⏳ Waiting"
                status_color = "#888888"
                if alert['type'] == 'above' and current_price >= alert['target']:
                    status = "🚀 TRIGGERED!"
                    status_color = "#27ae60"
                elif alert['type'] == 'below' and current_price <= alert['target']:
                    status = "📉 TRIGGERED!"
                    status_color = "#e74c3c"

                type_badge = "🔼 ABOVE" if alert['type'] == 'above' else "🔽 BELOW"
                news_url = f"https://finance.yahoo.com/quote/{alert['symbol']}/news"

                alert_list.append({
                    **alert,
                    'current_price': current_price,
                    'change_pct': change_pct,
                    'change_color': change_color,
                    'change_arrow': change_arrow,
                    'status': status,
                    'status_color': status_color,
                    'type_badge': type_badge,
                    'news_url': news_url,
                })

            # ---- HTML Table - horizontally scrollable on mobile ----
            import streamlit.components.v1 as components

            rows_html = ""
            for idx, a in enumerate(alert_list):
                row_bg = "#ffffff" if idx % 2 == 0 else "#f7f9fc"
                rows_html += f"""
                <tr style="background:{row_bg};">
                    <td><strong>{a['symbol']}</strong></td>
                    <td><strong>${a['current_price']:.2f}</strong><br>
                        <span style="color:{a['change_color']};font-size:11px;">
                            {a['change_arrow']}{abs(a['change_pct']):.2f}%
                        </span>
                    </td>
                    <td>${a['target']:.2f}</td>
                    <td style="white-space:nowrap;">{a['type_badge']}</td>
                    <td style="color:{a['status_color']};font-weight:bold;white-space:nowrap;">{a['status']}</td>
                    <td style="text-align:center;">
                        <a href="{a['news_url']}" target="_blank"
                           style="text-decoration:none;font-size:18px;">&#128240;</a>
                    </td>
                    <td style="white-space:nowrap;">
                        <button onclick="window.parent.postMessage({{action:'edit',id:'{a['id']}'}}, '*')"
                            style="background:#2E86AB;color:white;border:none;border-radius:4px;
                                   padding:6px 12px;cursor:pointer;font-size:13px;margin-right:4px;">
                            &#9999; Edit
                        </button>
                        <button onclick="window.parent.postMessage({{action:'delete',id:'{a['id']}'}}, '*')"
                            style="background:#e74c3c;color:white;border:none;border-radius:4px;
                                   padding:6px 12px;cursor:pointer;font-size:13px;">
                            &#128465; Del
                        </button>
                    </td>
                </tr>"""

            table_html = f"""
            <style>
                * {{ box-sizing: border-box; }}
                body {{ margin:0; padding:0; font-family: Arial, sans-serif; }}
                .table-wrap {{
                    width:100%;
                    overflow-x:auto;
                    -webkit-overflow-scrolling:touch;
                }}
                table {{
                    min-width:600px;
                    width:100%;
                    border-collapse:collapse;
                    font-size:13px;
                }}
                th {{
                    background:#2E86AB;
                    color:white;
                    padding:10px 12px;
                    text-align:left;
                    font-size:12px;
                    white-space:nowrap;
                }}
                td {{
                    padding:10px 12px;
                    border-bottom:1px solid #eee;
                    vertical-align:middle;
                }}
            </style>
            <div class="table-wrap">
            <table>
                <thead><tr>
                    <th>Symbol</th>
                    <th>Price</th>
                    <th>Target</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>News</th>
                    <th>Actions</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
            </div>"""

            # Generous height - 55px per row + 60px header, ensures all rows visible on mobile
            table_height = 60 + (len(alert_list) * 65)
            components.html(table_html, height=table_height, scrolling=False)

            # ---- Edit Forms (shown when edit is triggered) ----
            for idx, a in enumerate(alert_list):
                if st.session_state.get(f'editing_{a["id"]}', False):
                    st.markdown(
                        f"<div style='background:#f0f7fb; padding:14px; "
                        f"border-left:4px solid #2E86AB; border-radius:6px; margin:8px 0;'>",
                        unsafe_allow_html=True
                    )
                    st.markdown(f"**✏️ Editing: {a['symbol']}** — ${a['target']:.2f} {a['type'].upper()}")
                    ecol1, ecol2 = st.columns(2)
                    with ecol1:
                        new_target = st.number_input(
                            "New Target Price", min_value=0.01,
                            value=float(a['target']),
                            key=f"new_target_{a['id']}"
                        )
                    with ecol2:
                        new_type = st.selectbox(
                            "Alert When", ["above", "below"],
                            index=0 if a['type'] == 'above' else 1,
                            key=f"new_type_{a['id']}"
                        )
                    sc, cc = st.columns(2)
                    with sc:
                        if st.button("💾 Save", key=f"save_{a['id']}", type="primary", use_container_width=True):
                            supabase.table('alerts').update({
                                'target': new_target, 'type': new_type
                            }).eq('id', a['id']).execute()
                            st.session_state[f'editing_{a["id"]}'] = False
                            st.success("✅ Updated!")
                            st.rerun()
                    with cc:
                        if st.button("✖ Cancel", key=f"cancel_{a['id']}", use_container_width=True):
                            st.session_state[f'editing_{a["id"]}'] = False
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# FOOTER - Shows on ALL pages
# ============================================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #aaa; font-size: 11px; padding: 10px 0 20px 0; line-height: 2;'>
⚠️ Stock Alerts Pro provides price notifications only. This is NOT financial advice.<br>
Natts Digital is not an AFS licensee. Always consult a licensed financial advisor before making investment decisions.<br><br>
<a href='#' style='color: #aaa; text-decoration: none;'>Terms & Disclaimer</a> &nbsp;|&nbsp;
<a href='#' style='color: #aaa; text-decoration: none;'>Privacy Policy</a> &nbsp;|&nbsp;
© 2026 Natts Digital. All rights reserved.
</div>
""", unsafe_allow_html=True)
