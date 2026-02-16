# ============================================================
# ULTRA PRO STOCK ALERTS APP
# ============================================================

import streamlit as st
import requests
import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import bcrypt
from supabase import create_client, Client

# ============================================================
# SECRETS LOADER
# ============================================================

def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except:
        return os.getenv(key, default)

# ============================================================
# SUPABASE
# ============================================================

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Stock Price Alerts Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# AUTO REFRESH
# ============================================================

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 120:
    st.session_state.last_refresh = time.time()
    st.rerun()

# ============================================================
# SECURITY HELPERS
# ============================================================

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def authenticate_user(username, password):
    result = (
        supabase.table("users")
        .select("*")
        .ilike("username", username)
        .limit(1)
        .execute()
    )

    if not result.data:
        return False, None

    user = result.data[0]

    if verify_password(password, user["password_hash"]):
        return True, user

    return False, None


def get_user_alerts(username):
    res = supabase.table("alerts").select("*").eq("username", username).execute()
    return res.data or []


def save_alert(username, data):
    supabase.table("alerts").insert({
        "username": username,
        "symbol": data["symbol"],
        "target": data["target"],
        "type": data["type"],
        "enabled": True
    }).execute()


def delete_alert(alert_id):
    supabase.table("alerts").delete().eq("id", alert_id).execute()


def update_alert(alert_id, target, alert_type):
    supabase.table("alerts").update({
        "target": target,
        "type": alert_type
    }).eq("id", alert_id).execute()

# ============================================================
# STOCK PRICE
# ============================================================

def get_stock_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        r = requests.get(url, timeout=5).json()

        result = r["chart"]["result"][0]["meta"]
        price = result["regularMarketPrice"]
        prev = result.get("chartPreviousClose", price)
        change_pct = ((price - prev) / prev) * 100 if prev else 0

        return price, change_pct
    except:
        return None, None

# ============================================================
# SESSION INIT
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "current_page" not in st.session_state:
    st.session_state.current_page = "dashboard"

# ============================================================
# LOGIN PAGE
# ============================================================

if not st.session_state.logged_in:

    st.title("📊 Stock Price Alerts Pro")

    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

    if submit:
        ok, user = authenticate_user(u, p)
        if ok:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.session_state.username = user["username"]
            st.rerun()
        else:
            st.error("Invalid login")

    st.stop()

# ============================================================
# USER SESSION
# ============================================================

user = st.session_state.user
username = st.session_state.username

# ============================================================
# MOBILE TOP NAV (SAFE)
# ============================================================

st.markdown("""
<style>
@media(max-width:768px){
    section[data-testid="stSidebar"]{display:none !important;}
}
</style>
""", unsafe_allow_html=True)

c1,c2,c3,c4,c5 = st.columns([2,1,1,1,1])

with c1:
    st.markdown(f"👋 **{user['name'].split()[0]}**")

with c2:
    if st.button("🏠", key="home"):
        st.session_state.current_page="dashboard"
        st.rerun()

with c3:
    if st.button("➕", key="add"):
        st.session_state.current_page="add"
        st.rerun()

with c4:
    if st.button("⚙️", key="settings"):
        st.session_state.current_page="settings"
        st.rerun()

with c5:
    if st.button("🚪", key="logout"):
        st.session_state.logged_in=False
        st.rerun()

# ============================================================
# SIDEBAR DESKTOP
# ============================================================

with st.sidebar:
    st.title(user["name"])

    if st.button("Dashboard"):
        st.session_state.current_page="dashboard"
        st.rerun()

    if st.button("Add Alert"):
        st.session_state.current_page="add"
        st.rerun()

    if st.button("Logout"):
        st.session_state.logged_in=False
        st.rerun()

# ============================================================
# ADD ALERT PAGE
# ============================================================

if st.session_state.current_page=="add":

    st.title("➕ Add Alert")

    symbol = st.text_input("Symbol").upper()

    if symbol:
        price,change = get_stock_price(symbol)

        if price:
            st.metric("Current Price", f"${price:.2f}", f"{change:+.2f}%")

            target = st.number_input("Target", value=float(price))
            alert_type = st.selectbox("Type",["above","below"])

            if st.button("Create Alert"):
                save_alert(username,{
                    "symbol":symbol,
                    "target":target,
                    "type":alert_type
                })
                st.success("Created!")
                st.session_state.current_page="dashboard"
                st.rerun()

    st.stop()

# ============================================================
# DASHBOARD
# ============================================================

st.title("📊 Dashboard")

alerts = get_user_alerts(username)

if not alerts:
    st.info("No alerts yet.")
    st.stop()

# -------- ALERT TABLE --------

for a in alerts:

    price,change = get_stock_price(a["symbol"])

    with st.container():
        col1,col2,col3,col4,col5 = st.columns([3,2,2,1,1])

        with col1:
            st.write(f"**{a['symbol']}**")

        with col2:
            st.write(f"${price:.2f}" if price else "-")

        with col3:
            st.write(f"${a['target']:.2f} ({a['type']})")

        with col4:
            if st.button("✏️", key=f"edit_{a['id']}"):
                st.session_state[f"editing_{a['id']}"]=True

        with col5:
            if st.button("🗑", key=f"del_{a['id']}"):
                delete_alert(a["id"])
                st.rerun()

    # -------- INLINE EDIT --------
    if st.session_state.get(f"editing_{a['id']}", False):

        new_target = st.number_input(
            "New Target",
            value=float(a["target"]),
            key=f"target_{a['id']}"
        )

        new_type = st.selectbox(
            "Type",
            ["above","below"],
            index=0 if a["type"]=="above" else 1,
            key=f"type_{a['id']}"
        )

        c1,c2 = st.columns(2)

        with c1:
            if st.button("Save", key=f"save_{a['id']}"):
                update_alert(a["id"], new_target, new_type)
                st.session_state[f"editing_{a['id']}"]=False
                st.rerun()

        with c2:
            if st.button("Cancel", key=f"cancel_{a['id']}"):
                st.session_state[f"editing_{a['id']}"]=False
                st.rerun()

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.caption("© Natts Digital - Alerts Only. Not Financial Advice.")

