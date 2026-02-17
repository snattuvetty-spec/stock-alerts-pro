
# STOCK ALERTS PRO — ULTRA PRO VERSION
# Field‑ready deployment build

import streamlit as st
import requests
import os
import time
from datetime import datetime, timedelta
import bcrypt
from supabase import create_client, Client

st.set_page_config(page_title="Stock Price Alerts Pro", page_icon="📊", layout="wide")

def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except:
        return os.getenv(key, default)

url = get_secret("SUPABASE_URL")
admin_key = get_secret("SUPABASE_KEY")
supabase: Client = create_client(url, admin_key)

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_user(username, password):
    supabase.table("users").insert({
        "username": username,
        "password_hash": hash_password(password),
        "trial_ends": (datetime.now() + timedelta(days=21)).isoformat(),
        "premium": False
    }).execute()

def authenticate_user(username, password):
    result = supabase.table("users").select("*").ilike("username", username).limit(1).execute()
    if not result.data:
        return False, None
    user = result.data[0]
    if verify_password(password, user["password_hash"]):
        return True, user
    return False, None

def get_user_alerts(username):
    res = supabase.table("alerts").select("*").eq("username", username).execute()
    return res.data or []

def save_alert(username, symbol, target, typ):
    supabase.table("alerts").insert({
        "username": username,
        "symbol": symbol,
        "target": target,
        "type": typ,
        "enabled": True
    }).execute()

def delete_alert(alert_id):
    supabase.table("alerts").delete().eq("id", alert_id).execute()

def update_alert(alert_id, target, typ):
    supabase.table("alerts").update({"target": target, "type": typ}).eq("id", alert_id).execute()

def get_stock_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5).json()
        return r["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except:
        return None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:

    st.title("📊 Stock Price Alerts Pro")
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])

    with tab1:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

        if submit:
            ok, user = authenticate_user(u, p)
            if ok:
                st.session_state.logged_in = True
                st.session_state.username = user["username"]
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid login")

    with tab2:
        nu = st.text_input("New Username")
        np = st.text_input("New Password", type="password")
        if st.button("Create Account"):
            create_user(nu, np)
            st.success("Account created")

else:

    if "username" not in st.session_state:
        st.session_state.logged_in = False
        st.rerun()

    username = st.session_state.username

    st.markdown("""
    <style>
    .mobile-table{overflow-x:auto;}
    .mobile-row{display:flex;justify-content:space-between;background:#f5f7fb;padding:12px;border-radius:8px;margin-bottom:8px;min-width:600px;}
    </style>
    """, unsafe_allow_html=True)

    col_user, col_home, col_add, col_logout = st.columns([3,1,1,1])

    with col_user:
        st.markdown(f"👋 **{username}**")

    with col_home:
        if st.button("🏠"):
            st.session_state.page="dashboard"

    with col_add:
        if st.button("➕"):
            st.session_state.page="add"

    with col_logout:
        if st.button("🚪"):
            st.session_state.logged_in=False
            st.rerun()

    if "page" not in st.session_state:
        st.session_state.page="dashboard"

    if st.session_state.page=="add":

        st.title("➕ Add Alert")

        symbol=st.text_input("Symbol").upper()

        if symbol:
            price=get_stock_price(symbol)
            if price:
                st.metric("Current Price",f"${price:.2f}")
                target=st.number_input("Target",value=float(price))
                typ=st.selectbox("Type",["above","below"])

                if st.button("Create Alert"):
                    save_alert(username,symbol,target,typ)
                    st.session_state.page="dashboard"
                    st.rerun()

    else:

        st.title("📊 Dashboard")

        alerts=get_user_alerts(username)

        if not alerts:
            st.info("No alerts yet")
        else:
            for a in alerts:

                price=get_stock_price(a["symbol"])

                st.markdown(f"""
                <div class="mobile-table">
                    <div class="mobile-row">
                        <div><b>{a["symbol"]}</b></div>
                        <div>{price}</div>
                        <div>{a["target"]} ({a["type"]})</div>
                    </div>
                </div>
                """,unsafe_allow_html=True)

                c1,c2,c3=st.columns(3)

                with c1:
                    st.markdown(f'<a href="https://finance.yahoo.com/quote/{a["symbol"]}/news" target="_blank">📰 News</a>',unsafe_allow_html=True)

                with c2:
                    if st.button("✏️ Edit",key=f"edit_{a['id']}"):
                        st.session_state[f"editing_{a['id']}"]=True

                with c3:
                    if st.button("🗑 Delete",key=f"delete_{a['id']}"):
                        delete_alert(a["id"])
                        st.rerun()

                if st.session_state.get(f"editing_{a['id']}",False):

                    new_target=st.number_input("New Target",value=float(a["target"]),key=f"new_target_{a['id']}")
                    new_type=st.selectbox("Type",["above","below"],index=0 if a["type"]=="above" else 1,key=f"new_type_{a['id']}")

                    s1,s2=st.columns(2)

                    with s1:
                        if st.button("Save",key=f"save_{a['id']}"):
                            update_alert(a["id"],new_target,new_type)
                            st.session_state[f"editing_{a['id']}"]=False
                            st.rerun()

                    with s2:
                        if st.button("Cancel",key=f"cancel_{a['id']}"):
                            st.session_state[f"editing_{a['id']}"]=False
                            st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style='text-align:center;color:#999;font-size:12px;padding:20px 0;'>
    © Natts Digital — Alerts Only. Not Financial Advice.<br>
    Please consult a financial advisor before making any investment decisions.
    </div>
    """,unsafe_allow_html=True)
