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

nav1, nav2, nav3 = st.columns([6,1,1])

with nav1:
    st.markdown(f"👋 **{username}**")

with nav2:
    if st.button("➕ Add"):
        st.session_state.current_page = 'add_alert'
        st.rerun()

with nav3:
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

# ============================================================
# DASHBOARD
# ============================================================

st.title("📊 Dashboard")

alerts = get_user_alerts(username)

if not alerts:
    st.info("No alerts yet. Click ➕ Add to create your first alert!")
    st.stop()

# ============================================================
# TABLE HEADER - Scrolls with content on mobile
# ============================================================

st.markdown('<div class="scroll-wrapper">', unsafe_allow_html=True)

# Header row
hcol1, hcol2, hcol3, hcol4, hcol5, hcol6 = st.columns([2.2, 1.2, 2.2, 1.2, 1.2, 1.2])
with hcol1:
    st.markdown("**📈 Symbol**")
with hcol2:
    st.markdown("**💰 Price**")
with hcol3:
    st.markdown("**🎯 Target**")
with hcol4:
    st.markdown("**📰 News**")
with hcol5:
    st.markdown("**✏️ Edit**")
with hcol6:
    st.markdown("**🗑️ Delete**")

st.divider()

# ============================================================
# ALERT ROWS - Each alert in one horizontal row
# ============================================================

for a in alerts:
    price = get_stock_price(a["symbol"])
    
    col1, col2, col3, col4, col5, col6 = st.columns([2.2, 1.2, 2.2, 1.2, 1.2, 1.2])
    
    with col1:
        st.markdown(f"**{a['symbol']}**")
    
    with col2:
        if price:
            st.markdown(f"${price:.2f}")
        else:
            st.markdown("—")
    
    with col3:
        st.markdown(f"${a['target']:.2f} ({a['type'].upper()})")
    
    with col4:
        st.link_button(
            "📰",
            f"https://finance.yahoo.com/quote/{a['symbol']}/news",
            use_container_width=True
        )
    
    with col5:
        if st.button("✏️", key=f"edit_{a['id']}", use_container_width=True):
            st.session_state[f"editing_{a['id']}"] = True
    
    with col6:
        if st.button("🗑️", key=f"del_{a['id']}", use_container_width=True):
            if delete_alert(a["id"]):
                st.rerun()
            else:
                st.error("Failed to delete")
    
    # INLINE EDIT PANEL (appears below the row when edit is clicked)
    if st.session_state.get(f"editing_{a['id']}", False):
        st.markdown(f"**✏️ Editing {a['symbol']}**")
        
        ecol1, ecol2 = st.columns(2)
        
        with ecol1:
            new_target = st.number_input(
                "New Target Price",
                value=float(a["target"]),
                min_value=0.01,
                key=f"nt_{a['id']}"
            )
        
        with ecol2:
            new_type = st.selectbox(
                "Alert Type",
                ["above", "below"],
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
    
    st.divider()

st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# FOOTER
# ============================================================

st.markdown("""
<div style="text-align:center;color:gray;font-size:12px;margin-top:30px;">
© 2026 Natts Digital — Stock Alerts Pro<br>
⚠️ Price notifications only. Not financial advice. Consult a licensed financial advisor.
</div>
""", unsafe_allow_html=True)
