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

# ============================================================
# BUILD ALERT DATA WITH PRICES
# ============================================================

import streamlit.components.v1 as components

alert_list = []
for a in alerts:
    price = get_stock_price(a["symbol"])
    current = f"${price:.2f}" if price else "—"

    # Determine status
    status = "⏳ Waiting"
    status_color = "#888"
    if price:
        if a['type'] == 'above' and price >= a['target']:
            status = "🚀 TRIGGERED!"
            status_color = "#27ae60"
        elif a['type'] == 'below' and price <= a['target']:
            status = "📉 TRIGGERED!"
            status_color = "#e74c3c"

    news_url = f"https://finance.yahoo.com/quote/{a['symbol']}/news"

    alert_list.append({
        **a,
        'current': current,
        'status': status,
        'status_color': status_color,
        'news_url': news_url,
    })

# ============================================================
# HTML TABLE — renders identically on mobile and desktop
# ============================================================

rows_html = ""
for i, a in enumerate(alert_list):
    bg = "#ffffff" if i % 2 == 0 else "#f7f9fc"
    type_badge = "🔼 ABOVE" if a['type'] == 'above' else "🔽 BELOW"
    rows_html += f"""
    <tr style="background:{bg};">
        <td><strong>{a['symbol']}</strong></td>
        <td>{a['current']}</td>
        <td>${a['target']:.2f}</td>
        <td style="white-space:nowrap;">{type_badge}</td>
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
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{ font-family: Arial, sans-serif; }}
    .wrap {{
        width:100%;
        overflow-x:auto;
        -webkit-overflow-scrolling:touch;
    }}
    table {{
        min-width:650px;
        width:100%;
        border-collapse:collapse;
        font-size:13px;
    }}
    th {{
        background:#2E86AB;
        color:white;
        padding:10px 10px;
        text-align:left;
        white-space:nowrap;
        font-size:12px;
    }}
    td {{
        padding:10px 10px;
        border-bottom:1px solid #eee;
        vertical-align:middle;
    }}
</style>
<div class="wrap">
<table>
    <thead>
        <tr>
            <th>📈 Symbol</th>
            <th>💰 Price</th>
            <th>🎯 Target</th>
            <th>📊 Type</th>
            <th>🔔 Status</th>
            <th>📰 News</th>
            <th>⚙️ Actions</th>
        </tr>
    </thead>
    <tbody>{rows_html}</tbody>
</table>
</div>"""

table_height = 55 + (len(alert_list) * 58)
components.html(table_html, height=table_height, scrolling=False)

# ============================================================
# NATIVE STREAMLIT EDIT / DELETE BUTTONS
# (Table buttons are visual only — these do the real work)
# ============================================================

st.markdown("---")
for i, a in enumerate(alert_list):
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"**{a['symbol']}** — ${a['target']:.2f} {a['type'].upper()}")
    with col2:
        if st.button("✏️ Edit", key=f"edit_{i}", use_container_width=True):
            st.session_state[f"editing_{a['id']}"] = True
    with col3:
        if st.button("🗑️ Del", key=f"del_{i}", use_container_width=True):
            delete_alert(a["id"])
            st.rerun()

    # Inline edit form
    if st.session_state.get(f"editing_{a['id']}", False):
        st.markdown(f"**✏️ Editing {a['symbol']}**")
        ecol1, ecol2 = st.columns(2)
        with ecol1:
            new_target = st.number_input(
                "New Target Price", value=float(a["target"]),
                min_value=0.01, key=f"nt_{a['id']}"
            )
        with ecol2:
            new_type = st.selectbox(
                "Alert Type", ["above", "below"],
                index=0 if a["type"] == "above" else 1,
                key=f"ty_{a['id']}"
            )
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
⚠️ Price notifications only. Not financial advice. Consult a licensed financial advisor.
</div>
""", unsafe_allow_html=True)
