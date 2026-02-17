import streamlit as st
import requests
import os
import bcrypt
from supabase import create_client, Client

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Stock Alerts Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# SECRETS
# ============================================================

def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except:
        return os.getenv(key, default)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================================
# HELPERS
# ============================================================

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def get_stock_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except:
        return None

def authenticate_user(username, password):
    try:
        result = (
            supabase
            .table("users")
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
    except:
        return False, None

def get_user_alerts(username):
    result = supabase.table("alerts").select("*").eq("username", username).execute()
    return result.data or []

def save_alert(username, symbol, target, atype):
    supabase.table("alerts").insert({
        "username": username,
        "symbol": symbol,
        "target": target,
        "type": atype,
        "enabled": True
    }).execute()

def delete_alert(alert_id):
    supabase.table("alerts").delete().eq("id", alert_id).execute()

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

    st.title("📊 Stock Alerts Pro")

    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")

    if st.button("🔐 Login", use_container_width=True):
        ok, user = authenticate_user(username_input, password_input)
        if ok:
            st.session_state.logged_in = True
            st.session_state.username = user["username"]
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Invalid login")

    st.stop()

# ============================================================
# USER CONTEXT
# ============================================================

username = st.session_state.username
user = st.session_state.user

# ============================================================
# MOBILE TOP NAV
# ============================================================

st.markdown("""
<style>
@media (max-width:768px){
section[data-testid="stSidebar"]{display:none!important;}
}
</style>
""", unsafe_allow_html=True)

col_user, col_home, col_add, col_logout = st.columns([3,1,1,1])

with col_user:
    st.markdown(f"👋 **{user['name'].split()[0]}**")

with col_home:
    if st.button("🏠", key="m_home"):
        st.session_state.current_page = "dashboard"
        st.rerun()

with col_add:
    if st.button("➕", key="m_add"):
        st.session_state.current_page = "add_alert"
        st.rerun()

with col_logout:
    if st.button("🚪", key="m_logout"):
        st.session_state.logged_in = False
        st.rerun()

# ============================================================
# SIDEBAR DESKTOP
# ============================================================

with st.sidebar:
    st.title(user["name"])

    if st.button("Dashboard", use_container_width=True):
        st.session_state.current_page = "dashboard"
        st.rerun()

    if st.button("Add Alert", use_container_width=True):
        st.session_state.current_page = "add_alert"
        st.rerun()

    if st.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# ============================================================
# ADD ALERT PAGE
# ============================================================

if st.session_state.current_page == "add_alert":

    st.title("➕ Add Alert")

    symbol = st.text_input("Symbol").upper()

    if symbol:
        price = get_stock_price(symbol)
        if price:
            st.metric("Current Price", f"${price:.2f}")
            target = st.number_input("Target Price", min_value=0.01, value=float(price))
            atype = st.selectbox("Alert When", ["above", "below"])

            if st.button("Create Alert", type="primary"):
                save_alert(username, symbol, target, atype)
                st.success("Alert Created")
                st.session_state.current_page = "dashboard"
                st.rerun()
        else:
            st.error("Invalid symbol")

# ============================================================
# DASHBOARD (DESKTOP FIXED + EDIT FIX)
# ============================================================

else:

    st.title("📊 Dashboard")

    alerts = get_user_alerts(username)

    if not alerts:
        st.info("No alerts yet.")
    else:

        # ===== HEADER =====
        h1,h2,h3,h4,h5,h6 = st.columns([3,2,2,1,1,1])
        h1.markdown("**Symbol**")
        h2.markdown("**Price**")
        h3.markdown("**Target**")
        h4.markdown("**News**")
        h5.markdown("**Edit**")
        h6.markdown("**Delete**")

        st.divider()

        # ===== ALERT ROWS =====
        for a in alerts:

            price = get_stock_price(a["symbol"])

            c1,c2,c3,c4,c5,c6 = st.columns([3,2,2,1,1,1])

            with c1:
                st.write(a["symbol"])

            with c2:
                st.write(f"${price:.2f}" if price else "N/A")

            with c3:
                st.write(f"${a['target']:.2f} ({a['type']})")

            with c4:
                st.link_button("📰", f"https://finance.yahoo.com/quote/{a['symbol']}/news")

            with c5:
                if st.button("✏️", key=f"edit_{a['id']}"):
                    st.session_state[f"editing_{a['id']}"] = True

            with c6:
                if st.button("🗑", key=f"delete_{a['id']}"):
                    delete_alert(a["id"])
                    st.rerun()

            # =========================
            # INLINE EDIT PANEL (FIXED)
            # =========================
            if st.session_state.get(f"editing_{a['id']}", False):

                st.markdown("---")
                st.write(f"Editing **{a['symbol']}**")

                new_target = st.number_input(
                    "New Target Price",
                    min_value=0.01,
                    value=float(a["target"]),
                    key=f"new_target_{a['id']}"
                )

                new_type = st.selectbox(
                    "Alert When",
                    ["above", "below"],
                    index=0 if a["type"]=="above" else 1,
                    key=f"new_type_{a['id']}"
                )

                save_col, cancel_col = st.columns(2)

                with save_col:
                    if st.button("💾 Save", key=f"save_{a['id']}"):
                        supabase.table("alerts").update({
                            "target": new_target,
                            "type": new_type
                        }).eq("id", a["id"]).execute()

                        st.session_state[f"editing_{a['id']}"] = False
                        st.success("Updated!")
                        st.rerun()

                with cancel_col:
                    if st.button("✖ Cancel", key=f"cancel_{a['id']}"):
                        st.session_state[f"editing_{a['id']}"] = False
                        st.rerun()

                st.markdown("---")

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.caption("© Natts Digital — Alerts Only. Not Financial Advice. Pls consult a financial advisor before making any investment decisions.")
