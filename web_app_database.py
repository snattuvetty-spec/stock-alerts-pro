import streamlit as st
import requests
import os
import time
from datetime import datetime
from supabase import create_client, Client

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(page_title="Stock Alerts Pro", layout="wide")

# ============================================================
# SUPABASE
# ============================================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================================
# HELPERS
# ============================================================

def get_user_alerts(username):
    res = supabase.table("alerts").select("*").eq("username", username).execute()
    return res.data or []

def delete_alert(alert_id):
    supabase.table("alerts").delete().eq("id", alert_id).execute()

def update_alert(alert_id, target, typ):
    supabase.table("alerts").update(
        {"target": target, "type": typ}
    ).eq("id", alert_id).execute()

def get_stock_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        r = requests.get(url, timeout=5).json()
        return r["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except:
        return None

# ============================================================
# SESSION INIT
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "editing" not in st.session_state:
    st.session_state.editing = {}

# ============================================================
# LOGIN MOCK (KEEP YOUR ORIGINAL LOGIN IF YOU WANT)
# ============================================================

if not st.session_state.logged_in:

    st.title("🔐 Login")

    u = st.text_input("Username")
    if st.button("Login"):
        st.session_state.logged_in = True
        st.session_state.username = u   # ⭐ CRITICAL FIX
        st.rerun()

    st.stop()

# ============================================================
# SESSION SAFETY (⭐ THIS FIXES DISAPPEARING ALERTS)
# ============================================================

if "username" not in st.session_state:
    st.error("Session lost — please login again.")
    st.stop()

username = st.session_state["username"]

# ============================================================
# MOBILE CSS
# ============================================================

st.markdown("""
<style>
.mobile-table { overflow-x:auto; }
.mobile-row {
    display:flex;
    justify-content:space-between;
    background:#f8f9fc;
    padding:12px;
    margin-bottom:8px;
    border-radius:8px;
}
.mobile-cell { min-width:90px; font-size:14px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# TOP NAV
# ============================================================

col_user, col_home, col_add, col_set, col_logout = st.columns([2,1,1,1,1])

with col_user:
    st.markdown(f"👋 **{username}**")

with col_logout:
    if st.button("🚪"):
        st.session_state.logged_in = False
        st.rerun()

# ============================================================
# DASHBOARD
# ============================================================

st.title("📊 Dashboard")

alerts = get_user_alerts(username)

if not alerts:
    st.info("No alerts yet.")
    st.stop()

# Detect mobile
is_mobile = st.session_state.get("mobile", False)
# (Streamlit cannot truly detect device — layout still responsive)

# ============================================================
# DESKTOP TABLE
# ============================================================

if not is_mobile:

    header = st.columns([2,2,2,1,1,1])
    header[0].markdown("**Symbol**")
    header[1].markdown("**Price**")
    header[2].markdown("**Target**")
    header[3].markdown("**News**")
    header[4].markdown("**Edit**")
    header[5].markdown("**Delete**")

    st.divider()

    for a in alerts:

        price = get_stock_price(a["symbol"])

        c1,c2,c3,c4,c5,c6 = st.columns([2,2,2,1,1,1])

        c1.write(a["symbol"])
        c2.write(f"${price:.2f}" if price else "-")
        c3.write(f"${a['target']:.2f} ({a['type']})")

        # NEWS
        with c4:
            st.markdown(
                f'<a href="https://finance.yahoo.com/quote/{a["symbol"]}/news" target="_blank">📰</a>',
                unsafe_allow_html=True
            )

        # EDIT BUTTON
        with c5:
            if st.button("✏️", key=f"edit_{a['id']}"):
                st.session_state.editing[a["id"]] = True

        # DELETE BUTTON
        with c6:
            if st.button("🗑", key=f"del_{a['id']}"):
                delete_alert(a["id"])
                st.rerun()

        # INLINE EDIT PANEL
        if st.session_state.editing.get(a["id"], False):

            st.markdown("---")

            new_target = st.number_input(
                "Target",
                value=float(a["target"]),
                key=f"target_{a['id']}"
            )

            new_type = st.selectbox(
                "Type",
                ["above","below"],
                index=0 if a["type"]=="above" else 1,
                key=f"type_{a['id']}"
            )

            s1,s2 = st.columns(2)

            with s1:
                if st.button("Save", key=f"save_{a['id']}"):
                    update_alert(a["id"], new_target, new_type)
                    st.session_state.editing[a["id"]] = False
                    st.rerun()

            with s2:
                if st.button("Cancel", key=f"cancel_{a['id']}"):
                    st.session_state.editing[a["id"]] = False
                    st.rerun()

            st.markdown("---")

# ============================================================
# MOBILE HORIZONTAL TABLE
# ============================================================

else:

    st.markdown('<div class="mobile-table">', unsafe_allow_html=True)

    for a in alerts:

        price = get_stock_price(a["symbol"])

        st.markdown(f"""
        <div class="mobile-row">
            <div class="mobile-cell"><b>{a['symbol']}</b></div>
            <div class="mobile-cell">{f"${price:.2f}" if price else "-"}</div>
            <div class="mobile-cell">${a['target']:.2f} ({a['type']})</div>
        </div>
        """, unsafe_allow_html=True)

        c1,c2,c3 = st.columns(3)

        with c1:
            st.markdown(
                f'<a href="https://finance.yahoo.com/quote/{a["symbol"]}/news" target="_blank">📰 News</a>',
                unsafe_allow_html=True
            )

        with c2:
            if st.button("✏️ Edit", key=f"editm_{a['id']}"):
                st.session_state.editing[a["id"]] = True

        with c3:
            if st.button("🗑 Delete", key=f"delm_{a['id']}"):
                delete_alert(a["id"])
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)



# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.caption("© Natts Digital — Alerts Only. Not Financial Advice. Pls consult a financial advisor before making any investment decisions.")
