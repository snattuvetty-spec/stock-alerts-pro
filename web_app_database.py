# ============================================================
# ULTRA PRO STOCK ALERTS APP (DESKTOP + MOBILE FRIENDLY)
# Clean Streamlit-native layout (NO HTML TABLE BREAKS)
# ============================================================

import streamlit as st
from supabase import create_client, Client
import os

# ============================================================
# SUPABASE CONNECTION
# ============================================================

def get_secret(key, default=None):
    """Get secret from Streamlit Cloud secrets or environment variables."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.getenv(key, default)

# Initialize Supabase
url = get_secret("SUPABASE_URL")
key = get_secret("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# ============================================================
# REAL BACKEND FUNCTIONS
# ============================================================

def get_user_alerts(username):
    """Fetch alerts from Supabase"""
    result = supabase.table('alerts').select('*').eq('username', username).execute()
    return result.data

def delete_alert(alert_id):
    """Delete alert from Supabase"""
    try:
        supabase.table('alerts').delete().eq('id', alert_id).execute()
        return True
    except:
        return False

def get_stock_price(symbol):
    """Fetch real-time stock price using yfinance"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        data = ticker.history(period='1d')
        if not data.empty:
            return float(data['Close'].iloc[-1])
        return None
    except:
        return None

def update_alert(alert_id, target, alert_type):
    """Update alert in Supabase"""
    try:
        supabase.table('alerts').update({
            'target': target,
            'type': alert_type
        }).eq('id', alert_id).execute()
        return True
    except:
        return False

def authenticate_user(username, password):
    """Simple authentication - replace with your real auth"""
    try:
        import bcrypt
        result = supabase.table('users').select('*').execute()
        for user in result.data:
            if user['username'].lower() == username.lower():
                if bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
                    return True, user
        return False, None
    except:
        return False, None

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(page_title="Stock Alerts Pro", layout="wide")

# CRITICAL MOBILE CSS - Forces horizontal scroll
st.markdown("""
<style>
/* Force horizontal scroll on mobile */
@media (max-width: 768px) {
    .element-container:has(.scroll-wrapper) {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
    }
    .scroll-wrapper {
        min-width: 800px;
        display: block;
    }
    /* Ensure buttons don't wrap */
    .stButton button {
        white-space: nowrap;
        min-width: 70px;
    }
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# SIMPLE LOGIN
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", type="primary")
    
    if submit:
        success, user = authenticate_user(username, password)
        if success:
            st.session_state.logged_in = True
            st.session_state.username = user['username']
            st.session_state.user = user
            st.rerun()
        else:
            st.error("❌ Invalid credentials")
    
    st.stop()

# ============================================================
# TOP NAV (MOBILE + DESKTOP)
# ============================================================

username = st.session_state.username

if 'current_page' not in st.session_state:
    st.session_state.current_page = 'dashboard'

nav1, nav2, nav3, nav4 = st.columns([5, 1.2, 1.2, 1.2])

with nav1:
    st.markdown(f"👋 **{username}**")

with nav2:
    if st.button("🏠 Dash", use_container_width=True):
        st.session_state.current_page = 'dashboard'
        st.rerun()

with nav3:
    if st.button("➕ Add", use_container_width=True):
        st.session_state.current_page = 'add_alert'
        st.rerun()

with nav4:
    if st.button("🚪 Exit", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# ============================================================
# ADD ALERT PAGE
# ============================================================

if st.session_state.current_page == 'add_alert':
    st.title("➕ Add New Alert")

    if st.button("← Back to Dashboard"):
        st.session_state.current_page = 'dashboard'
        st.rerun()

    with st.form("add_alert_form"):
        symbol = st.text_input("Stock Symbol (e.g. AAPL, TSLA, BTQ)").upper().strip()
        target = st.number_input("Target Price ($)", min_value=0.01, value=10.00)
        alert_type = st.selectbox("Alert When Price Goes", ["above", "below"])
        add_submit = st.form_submit_button("✅ Create Alert", type="primary", use_container_width=True)

    if add_submit:
        if not symbol:
            st.error("❌ Please enter a stock symbol")
        else:
            # Check current price
            price = get_stock_price(symbol)
            if price:
                st.metric(f"{symbol} Current Price", f"${price:.2f}")
            else:
                st.warning("⚠️ Could not verify symbol — alert will still be created")

            try:
                supabase.table('alerts').insert({
                    'username': username,
                    'symbol': symbol,
                    'target': target,
                    'type': alert_type,
                    'enabled': True
                }).execute()
                st.success(f"✅ Alert created! Notify when {symbol} goes {alert_type} ${target:.2f}")
                import time
                time.sleep(1)
                st.session_state.current_page = 'dashboard'
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to create alert: {str(e)}")

    st.stop()

# ============================================================
# DASHBOARD
# ============================================================

st.title("📊 Dashboard")

alerts = get_user_alerts(username)

if not alerts:
    st.info("No alerts yet. Click ➕ Add to create your first alert!")
    st.stop()

import streamlit.components.v1 as components

# ============================================================
# BUILD ALERT DATA
# ============================================================
alert_list = []
for a in alerts:
    price = get_stock_price(a["symbol"])
    current = f"${price:.2f}" if price else "—"
    status = "⏳ Waiting"
    status_color = "#888"
    if price:
        if a["type"] == "above" and price >= a["target"]:
            status = "🚀 TRIGGERED!"
            status_color = "#27ae60"
        elif a["type"] == "below" and price <= a["target"]:
            status = "📉 TRIGGERED!"
            status_color = "#e74c3c"
    news_url = f"https://finance.yahoo.com/quote/{a['symbol']}/news"
    alert_list.append({**a, "current": current, "status": status,
                       "status_color": status_color, "news_url": news_url})

# ============================================================
# PURE NATIVE STREAMLIT TABLE
# Force horizontal layout with CSS override on mobile
# ============================================================

st.markdown("""
<style>
/* Force ALL columns to stay horizontal - never stack */
[data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    min-width: 60px !important;
    flex-shrink: 0 !important;
}
/* Hide the header separator */
.header-row {
    background: #2E86AB;
    color: white;
    padding: 8px;
    border-radius: 4px 4px 0 0;
    margin-bottom: 2px;
}
</style>
""", unsafe_allow_html=True)

# Table header
h = st.columns([2, 1.5, 1.5, 1.5, 2, 0.8, 0.8, 0.8])
headers = ["📈 Symbol", "💰 Price", "🎯 Target", "📊 Type", "🔔 Status", "📰", "✏️", "🗑️"]
for col, header in zip(h, headers):
    col.markdown(f"**{header}**")
st.divider()

# Table rows - all native Streamlit buttons
for i, a in enumerate(alert_list):
    cols = st.columns([2, 1.5, 1.5, 1.5, 2, 0.8, 0.8, 0.8])

    cols[0].markdown(f"**{a['symbol']}**")
    cols[1].markdown(a['current'])
    cols[2].markdown(f"${a['target']:.2f}")
    cols[3].markdown("🔼" if a['type'] == 'above' else "🔽")
    cols[4].markdown(f"<span style='color:{a['status_color']}'>{a['status']}</span>",
                     unsafe_allow_html=True)
    cols[5].link_button("📰", a['news_url'])

    if cols[6].button("✏️", key=f"edit_{i}", use_container_width=True):
        # Toggle edit - close others first
        for other in alert_list:
            if other['id'] != a['id']:
                st.session_state[f"editing_{other['id']}"] = False
        st.session_state[f"editing_{a['id']}"] = not st.session_state.get(f"editing_{a['id']}", False)
        st.rerun()

    if cols[7].button("🗑️", key=f"del_{i}", use_container_width=True):
        st.session_state[f"confirm_del_{a['id']}"] = True
        st.rerun()

    # Delete confirmation
    if st.session_state.get(f"confirm_del_{a['id']}", False):
        st.warning(f"⚠️ Delete **{a['symbol']}** alert?")
        dc1, dc2 = st.columns(2)
        if dc1.button("✅ Yes, Delete", key=f"yes_del_{a['id']}", type="primary", use_container_width=True):
            delete_alert(a['id'])
            st.session_state[f"confirm_del_{a['id']}"] = False
            st.rerun()
        if dc2.button("❌ Cancel", key=f"no_del_{a['id']}", use_container_width=True):
            st.session_state[f"confirm_del_{a['id']}"] = False
            st.rerun()

    # Inline edit form
    if st.session_state.get(f"editing_{a['id']}", False):
        with st.container():
            st.markdown(f"**✏️ Editing {a['symbol']}**")
            ecol1, ecol2 = st.columns(2)
            with ecol1:
                new_target = st.number_input("New Target Price",
                    value=float(a["target"]), min_value=0.01, key=f"nt_{a['id']}")
            with ecol2:
                new_type = st.selectbox("Alert Type", ["above", "below"],
                    index=0 if a["type"] == "above" else 1, key=f"ty_{a['id']}")
            cA, cB = st.columns(2)
            with cA:
                if st.button("💾 Save", key=f"save_{a['id']}", type="primary", use_container_width=True):
                    if update_alert(a["id"], new_target, new_type):
                        st.session_state[f"editing_{a['id']}"] = False
                        st.success("✅ Updated!")
                        st.rerun()
                    else:
                        st.error("❌ Update failed")
            with cB:
                if st.button("✖ Cancel", key=f"cancel_{a['id']}", use_container_width=True):
                    st.session_state[f"editing_{a['id']}"] = False
                    st.rerun()
        st.markdown("---")

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div style="text-align:center;color:gray;font-size:12px;margin-top:30px;">
© 2026 Natts Digital — Stock Alerts Pro<br>
⚠️ Price notifications only. Not financial advice.
</div>
""", unsafe_allow_html=True)
