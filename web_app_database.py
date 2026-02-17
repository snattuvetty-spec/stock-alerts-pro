
# ============================================================
# ULTRA PRO STOCK ALERTS APP (DESKTOP + MOBILE FRIENDLY)
# Clean Streamlit-native layout (NO HTML TABLE BREAKS)
# ============================================================

import streamlit as st

# ============================================================
# MOCK FUNCTIONS (KEEP YOUR ORIGINAL BACKEND FUNCTIONS HERE)
# Replace these with your real Supabase / API functions
# ============================================================

def get_user_alerts(username):
    # Example structure — replace with real DB call
    return st.session_state.get("demo_alerts",[
        {"id":1,"symbol":"LAES","target":4.00,"type":"above"},
        {"id":2,"symbol":"QBTS","target":17.50,"type":"below"},
        {"id":3,"symbol":"BTQ","target":2.70,"type":"below"},
        {"id":4,"symbol":"UEC","target":15.50,"type":"above"},
    ])

def delete_alert(alert_id):
    alerts = get_user_alerts("demo")
    st.session_state.demo_alerts = [a for a in alerts if a["id"] != alert_id]

def get_stock_price(symbol):
    # Replace with real price fetch
    demo_prices = {
        "LAES":3.85,
        "QBTS":19.67,
        "BTQ":2.78,
        "UEC":15.52
    }
    return demo_prices.get(symbol,None)

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(page_title="Stock Alerts Pro", layout="wide")

# ============================================================
# SIMPLE LOGIN (FIELD READY — NO AUTO LOGIN MAGIC)
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:

    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Replace with real auth
        if username:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.rerun()

    st.stop()

# ============================================================
# TOP NAV (MOBILE + DESKTOP)
# ============================================================

username = st.session_state.username

nav1, nav2, nav3 = st.columns([6,1,1])

with nav1:
    st.markdown(f"👋 **{username}**")

with nav2:
    if st.button("➕"):
        st.info("Add alert page coming next 🙂")

with nav3:
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

# ============================================================
# ULTRA PRO DASHBOARD LOOP
# Works PERFECT on Desktop + Mobile
# ============================================================

for a in alerts:

    price = get_stock_price(a["symbol"])

    # ===== ULTRA PRO RESPONSIVE ROW =====
    col1, col2, col3, col4, col5, col6 = st.columns(
        [2.2, 1.2, 2.2, 1.2, 1.2, 1.2]
    )

    with col1:
        st.markdown(f"**{a['symbol']}**")

    with col2:
        st.markdown(f"${price:.2f}" if price else "N/A")

    with col3:
        st.markdown(f"${a['target']:.2f} ({a['type']})")

    with col4:
        st.link_button(
            "📰",
            f"https://finance.yahoo.com/quote/{a['symbol']}/news"
        )

    with col5:
        if st.button("✏️", key=f"edit_{a['id']}"):
            st.session_state[f"editing_{a['id']}"] = True

    with col6:
        if st.button("🗑", key=f"del_{a['id']}"):
            delete_alert(a["id"])
            st.rerun()

    # ===== INLINE EDIT PANEL =====
    if st.session_state.get(f"editing_{a['id']}", False):

        new_target = st.number_input(
            "Target",
            value=float(a["target"]),
            key=f"nt_{a['id']}"
        )

        new_type = st.selectbox(
            "Type",
            ["above","below"],
            index=0 if a["type"]=="above" else 1,
            key=f"ty_{a['id']}"
        )

        cA, cB = st.columns(2)

        with cA:
            if st.button("💾 Save", key=f"save_{a['id']}"):
                supabase.table("alerts").update({
                    "target": new_target,
                    "type": new_type
                }).eq("id", a["id"]).execute()

                st.session_state[f"editing_{a['id']}"] = False
                st.rerun()

        with cB:
            if st.button("Cancel", key=f"cancel_{a['id']}"):
                st.session_state[f"editing_{a['id']}"] = False
                st.rerun()

    st.divider()


# ============================================================
# FOOTER
# ============================================================

st.markdown(
"""
<div style="text-align:center;color:gray;font-size:12px;">
© Natts Digital — Alerts Only. Not Financial Advice.<br>
Pls consult a financial advisor before making any investment decisions.
</div>
""",
unsafe_allow_html=True
)
