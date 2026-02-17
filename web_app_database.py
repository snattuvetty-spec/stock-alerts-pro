
import streamlit as st

# =============================================================
# ULTRA PRO V5 — TradingView Style Layout
# Horizontal mobile scrolling table
# =============================================================

st.set_page_config(page_title="Stock Alerts Pro", layout="wide")

# -----------------------------
# DEMO DATA (replace with DB)
# -----------------------------
def get_user_alerts(username):
    return [
        {"id":1,"symbol":"LAES","target":4.00,"type":"above"},
        {"id":2,"symbol":"QBTS","target":17.50,"type":"below"},
        {"id":3,"symbol":"BTQ","target":2.70,"type":"below"},
        {"id":4,"symbol":"UEC","target":15.50,"type":"above"},
    ]

def get_stock_price(symbol):
    prices = {"LAES":3.85,"QBTS":19.67,"BTQ":2.78,"UEC":15.52}
    return prices.get(symbol,0)

def delete_alert(id):
    pass

# =============================================================
# GLOBAL CSS — TRADINGVIEW MOBILE GRID
# =============================================================

st.markdown("""
<style>

.mobile-scroll{
    overflow-x:auto;
    width:100%;
}

.mobile-table{
    min-width:720px;
    border-collapse:collapse;
}

.mobile-row{
    display:grid;
    grid-template-columns:120px 120px 160px 80px 80px 80px;
    align-items:center;
    background:#f4f6f9;
    border-radius:10px;
    margin-bottom:10px;
    padding:10px;
}

.mobile-cell{
    font-size:14px;
}

@media (max-width:768px){
    section[data-testid="stSidebar"]{
        display:none !important;
    }
}

</style>
""", unsafe_allow_html=True)

# =============================================================
# SIMPLE LOGIN (FIELD READY)
# =============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:

    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.rerun()

    st.stop()

# =============================================================
# DASHBOARD
# =============================================================

username = st.session_state.username

st.title("📊 Dashboard")

alerts = get_user_alerts(username)

if not alerts:
    st.info("No alerts yet.")
    st.stop()

# Horizontal scroll wrapper
st.markdown('<div class="mobile-scroll">', unsafe_allow_html=True)

for a in alerts:

    price = get_stock_price(a["symbol"])

    # TradingView style grid row
    st.markdown(f"""
    <div class="mobile-row">
        <div class="mobile-cell"><b>{a['symbol']}</b></div>
        <div class="mobile-cell">${price:.2f}</div>
        <div class="mobile-cell">${a['target']:.2f} ({a['type']})</div>
        <div class="mobile-cell">📰</div>
        <div class="mobile-cell">✏️</div>
        <div class="mobile-cell">🗑</div>
    </div>
    """, unsafe_allow_html=True)

    c1,c2,c3 = st.columns([1,1,1])

    with c1:
        st.link_button(
            "📰 News",
            f"https://finance.yahoo.com/quote/{a['symbol']}/news"
        )

    with c2:
        if st.button("✏️ Edit", key=f"edit_{a['id']}"):
            st.session_state[f"editing_{a['id']}"]=True

    with c3:
        if st.button("🗑 Delete", key=f"del_{a['id']}"):
            delete_alert(a["id"])
            st.rerun()

    # Inline edit panel
    if st.session_state.get(f"editing_{a['id']}",False):

        new_target = st.number_input(
            "New Target",
            value=float(a["target"]),
            key=f"new_target_{a['id']}"
        )

        new_type = st.selectbox(
            "Alert Type",
            ["above","below"],
            index=0 if a["type"]=="above" else 1,
            key=f"new_type_{a['id']}"
        )

        sc1,sc2 = st.columns(2)

        with sc1:
            if st.button("💾 Save", key=f"save_{a['id']}"):
                st.session_state[f"editing_{a['id']}"]=False
                st.rerun()

        with sc2:
            if st.button("✖ Cancel", key=f"cancel_{a['id']}"):
                st.session_state[f"editing_{a['id']}"]=False
                st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

st.divider()

st.caption("© Natts Digital — Alerts Only. Not Financial Advice. Pls consult a financial advisor before making any investment decisions.")
