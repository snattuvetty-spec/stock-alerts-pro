
import streamlit as st
from supabase import create_client, Client
import requests

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(page_title="Stock Alerts Pro", layout="wide")

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================================
# SIMPLE LOGIN
# ============================================================
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

# ============================================================
# HELPERS
# ============================================================
def get_user_alerts(username):
    try:
        res = supabase.table("alerts").select("*").eq("username", username).execute()
        return res.data or []
    except:
        return []

def delete_alert(alert_id):
    try:
        supabase.table("alerts").delete().eq("id", alert_id).execute()
    except:
        pass

def get_stock_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        r = requests.get(url, timeout=5)
        data = r.json()
        return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except:
        return None

# ============================================================
# HEADER
# ============================================================
st.markdown(f"👋 **{st.session_state.username}**")

top1, top2, top3 = st.columns([1,1,1])
with top1:
    st.button("🏠", key="home_btn")
with top2:
    st.button("➕", key="add_btn")
with top3:
    if st.button("🚪"):
        st.session_state.logged_in = False
        st.rerun()

st.title("📊 Dashboard")

alerts = get_user_alerts(st.session_state.username)

if not alerts:
    st.info("No alerts yet.")
    st.stop()

# ============================================================
# ULTRA PRO V4 TABLE (HORIZONTAL MOBILE SCROLL)
# ============================================================

st.markdown("""
<style>
.table-wrap {
    width:100%;
    overflow-x:auto;
    -webkit-overflow-scrolling:touch;
}
.alert-table {
    min-width:700px;
    width:100%;
    border-collapse:collapse;
}
.alert-table th {
    background:#2E86AB;
    color:white;
    padding:10px;
    text-align:left;
}
.alert-table td {
    padding:12px;
    border-bottom:1px solid #eee;
}
</style>
""", unsafe_allow_html=True)

rows_html = ""

for a in alerts:

    price = get_stock_price(a["symbol"])
    price_txt = f"${price:.2f}" if price else "N/A"

    rows_html += f"""
    <tr>
        <td><b>{a['symbol']}</b></td>
        <td>{price_txt}</td>
        <td>${a['target']:.2f} ({a['type']})</td>
        <td><a href="https://finance.yahoo.com/quote/{a['symbol']}/news" target="_blank">📰 News</a></td>
        <td>EDIT_{a['id']}</td>
        <td>DEL_{a['id']}</td>
    </tr>
    """

table_html = f"""
<div class="table-wrap">
<table class="alert-table">
<thead>
<tr>
<th>Symbol</th>
<th>Price</th>
<th>Target</th>
<th>News</th>
<th>Edit</th>
<th>Delete</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</div>
"""

import streamlit.components.v1 as components
components.html(table_html, height=80 + len(alerts)*60, scrolling=True)

# ============================================================
# ACTION BUTTONS
# ============================================================

st.divider()

for a in alerts:

    c1, c2, c3 = st.columns([2,1,1])

    with c1:
        st.write(f"**{a['symbol']}**")

    with c2:
        if st.button("✏️ Edit", key=f"edit_{a['id']}"):
            st.session_state[f"editing_{a['id']}"] = True

    with c3:
        if st.button("🗑 Delete", key=f"del_{a['id']}"):
            delete_alert(a["id"])
            st.rerun()

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

        if st.button("💾 Save", key=f"save_{a['id']}"):
            supabase.table("alerts").update({
                "target": new_target,
                "type": new_type
            }).eq("id", a["id"]).execute()

            st.session_state[f"editing_{a['id']}"] = False
            st.rerun()

    st.divider()

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div style='text-align:center;color:#999;font-size:12px;padding:20px'>
© Natts Digital — Alerts Only. Not Financial Advice.<br>
Pls consult a financial advisor before making any investment decisions.
</div>
""", unsafe_allow_html=True)
