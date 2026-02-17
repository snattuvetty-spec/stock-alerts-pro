import streamlit as st
import requests
import os
import time
from datetime import datetime, timedelta
import bcrypt
from supabase import create_client, Client

# =====================================================
# CONFIG / SUPABASE
# =====================================================

def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except:
        return os.getenv(key, default)

url = get_secret("SUPABASE_URL")
admin_key = get_secret("SUPABASE_KEY")

supabase: Client = create_client(url, admin_key)

st.set_page_config(
    page_title="Stock Price Alerts Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =====================================================
# HELPERS
# =====================================================

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def get_stock_price(symbol):
    try:
        r = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5
        ).json()

        price = r["chart"]["result"][0]["meta"]["regularMarketPrice"]
        return price
    except:
        return None

# =====================================================
# DATABASE FUNCTIONS
# =====================================================

def authenticate_user(username, password):
    res = supabase.table("users").select("*").ilike("username", username).limit(1).execute()
    if not res.data:
        return False, None
    user = res.data[0]
    if verify_password(password, user["password_hash"]):
        return True, user
    return False, None

def get_user_alerts(username):
    res = supabase.table("alerts").select("*").eq("username", username).execute()
    return res.data

def save_alert(username, symbol, target, alert_type):
    supabase.table("alerts").insert({
        "username": username,
        "symbol": symbol,
        "target": target,
        "type": alert_type,
        "enabled": True
    }).execute()

def delete_alert(alert_id):
    supabase.table("alerts").delete().eq("id", alert_id).execute()

# =====================================================
# SESSION STATE
# =====================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# =====================================================
# LOGIN PAGE
# =====================================================

if not st.session_state.logged_in:

    st.title("📊 Stock Price Alerts Pro")

    with st.form("login_form"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            ok, u = authenticate_user(user, pwd)
            if ok:
                st.session_state.logged_in = True
                st.session_state.username = u["username"]
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Invalid credentials")

    st.stop()

# =====================================================
# MAIN APP
# =====================================================

username = st.session_state.username
user = st.session_state.user

if "current_page" not in st.session_state:
    st.session_state.current_page = "dashboard"

# =====================================================
# MOBILE NAV BAR
# =====================================================

st.markdown("""
<style>
@media (max-width:768px){
section[data-testid="stSidebar"]{display:none!important;}
.mobile-table{overflow-x:auto;}
.mobile-row{display:inline-flex;gap:16px;border-bottom:1px solid #eee;padding:10px 0;min-width:650px;}
.mobile-cell{min-width:120px;}
}
</style>
""", unsafe_allow_html=True)

col_user, col_home, col_add, col_logout = st.columns([2,1,1,1])

with col_user:
    st.markdown(f"👋 **{user['name'].split()[0]}**")

with col_home:
    if st.button("🏠", key="home"):
        st.session_state.current_page="dashboard"
        st.rerun()

with col_add:
    if st.button("➕", key="add"):
        st.session_state.current_page="add"
        st.rerun()

with col_logout:
    if st.button("🚪", key="logout"):
        st.session_state.logged_in=False
        st.rerun()

# =====================================================
# ADD ALERT PAGE
# =====================================================

if st.session_state.current_page=="add":

    st.title("➕ Add Alert")

    symbol = st.text_input("Symbol").upper()

    if symbol:
        price = get_stock_price(symbol)
        if price:
            st.metric("Current Price", f"${price:.2f}")

            target = st.number_input("Target Price", value=float(price))
            alert_type = st.selectbox("Alert When",["above","below"])

            if st.button("Create Alert"):
                save_alert(username,symbol,target,alert_type)
                st.success("Alert created")
                st.session_state.current_page="dashboard"
                st.rerun()
        else:
            st.error("Invalid symbol")

# =====================================================
# DASHBOARD
# =====================================================

else:

    st.title("📊 Dashboard")

    alerts = get_user_alerts(username)

    if not alerts:
        st.info("No alerts yet.")
        st.stop()

    # MOBILE SCROLL WRAPPER
    st.markdown('<div class="mobile-table">', unsafe_allow_html=True)

    for a in alerts:

        price = get_stock_price(a["symbol"])

        # ROW (MOBILE HORIZONTAL)
        st.markdown(f"""
        <div class="mobile-row">
            <div class="mobile-cell"><b>{a['symbol']}</b></div>
            <div class="mobile-cell">{f"${price:.2f}" if price else "N/A"}</div>
            <div class="mobile-cell">${a['target']:.2f} ({a['type']})</div>
        </div>
        """, unsafe_allow_html=True)

        # ACTION BUTTONS (REAL STREAMLIT)
        c1,c2,c3 = st.columns(3)

        with c1:
            st.link_button("📰 News",f"https://finance.yahoo.com/quote/{a['symbol']}/news",key=f"news_{a['id']}")

        with c2:
            if st.button("✏️ Edit",key=f"edit_{a['id']}"):
                st.session_state[f"editing_{a['id']}"]=True

        with c3:
            if st.button("🗑 Delete",key=f"del_{a['id']}"):
                delete_alert(a["id"])
                st.rerun()

        # INLINE EDIT PANEL
        if st.session_state.get(f"editing_{a['id']}",False):

            new_target = st.number_input(
                "New Target",
                value=float(a["target"]),
                key=f"new_target_{a['id']}"
            )

            new_type = st.selectbox(
                "Type",
                ["above","below"],
                index=0 if a["type"]=="above" else 1,
                key=f"new_type_{a['id']}"
            )

            s1,s2=st.columns(2)

            with s1:
                if st.button("💾 Save",key=f"save_{a['id']}"):
                    supabase.table("alerts").update({
                        "target":new_target,
                        "type":new_type
                    }).eq("id",a["id"]).execute()

                    st.session_state[f"editing_{a['id']}"]=False
                    st.rerun()

            with s2:
                if st.button("Cancel",key=f"cancel_{a['id']}"):
                    st.session_state[f"editing_{a['id']}"]=False
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.caption("© Natts Digital — Alerts Only. Not Financial Advice. Pls consult a financial advisor before making any investment decisions.")
