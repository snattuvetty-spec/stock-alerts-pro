import streamlit as st
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

load_dotenv()

# Initialize Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Page config
st.set_page_config(
    page_title="Admin Dashboard",
    page_icon="🔐",
    layout="wide"
)

# Authentication
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.title("🔐 Admin Dashboard Login")

    with st.form("admin_login"):
        admin_user = st.text_input("Username")
        admin_pass = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", type="primary")

    if submit:
        correct_user = os.getenv("ADMIN_USERNAME", "admin")
        correct_pass = os.getenv("ADMIN_PASSWORD", "admin123")

        if admin_user == correct_user and admin_pass == correct_pass:
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

    st.stop()

# Admin is logged in
st.title("📊 Stock Alerts Pro - Admin Dashboard")
st.markdown("---")

# Logout button
if st.button("🚪 Logout", key="logout"):
    st.session_state.admin_logged_in = False
    st.rerun()

# ============================================================
# DATA FUNCTIONS
# ============================================================

def get_all_users():
    result = supabase.table('users').select('*').execute()
    return result.data

def get_trial_users():
    result = supabase.table('users').select('*').eq('premium', False).execute()
    trial_users = []
    for user in result.data:
        trial_ends = datetime.fromisoformat(user['trial_ends'])
        if trial_ends > datetime.now():
            trial_users.append(user)
    return trial_users

def get_premium_users():
    result = supabase.table('users').select('*').eq('premium', True).execute()
    return result.data

def get_total_revenue():
    premium_users = get_premium_users()
    total = sum([user.get('premium_price', 0) or 0 for user in premium_users])
    return total

def get_alerts_sent_today():
    today = datetime.now().date().isoformat()
    result = supabase.table('alert_history').select('*').gte('sent_at', today).execute()
    return len(result.data)

def get_historical_data(days=30):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    result = supabase.table('daily_metrics').select('*').gte('date', start_date.isoformat()).order('date').execute()
    return result.data

def calculate_conversion_rate():
    all_users = get_all_users()
    premium_users = get_premium_users()
    if len(all_users) == 0:
        return 0
    return (len(premium_users) / len(all_users)) * 100

def update_daily_metrics():
    today = datetime.now().date().isoformat()
    total_users = len(get_all_users())
    trial_users = len(get_trial_users())
    premium_users = len(get_premium_users())
    total_revenue = get_total_revenue()
    alerts_sent = get_alerts_sent_today()

    try:
        supabase.table('daily_metrics').update({
            'total_users': total_users,
            'trial_users': trial_users,
            'premium_users': premium_users,
            'total_revenue': total_revenue,
            'alerts_sent': alerts_sent
        }).eq('date', today).execute()
    except:
        supabase.table('daily_metrics').insert({
            'date': today,
            'total_users': total_users,
            'trial_users': trial_users,
            'premium_users': premium_users,
            'total_revenue': total_revenue,
            'alerts_sent': alerts_sent
        }).execute()

# ============================================================
# UPDATE METRICS
# ============================================================
update_daily_metrics()

# ============================================================
# KEY METRICS
# ============================================================
st.header("📈 Key Metrics (Real-time)")

all_users = get_all_users()
trial_users = get_trial_users()
premium_users = get_premium_users()
total_revenue = get_total_revenue()
alerts_today = get_alerts_sent_today()
conversion = calculate_conversion_rate()
mrr = sum([user.get('premium_price', 0) or 0 for user in premium_users])

metrics_data = {
    'Metric': [
        '👥 Total Users',
        '🎁 Trial Users (Active)',
        '⭐ Premium Users',
        '💰 Total Revenue',
        '🔔 Alerts Sent Today',
        '📊 Conversion Rate',
        '💵 MRR (Monthly)'
    ],
    'Value': [
        len(all_users),
        len(trial_users),
        len(premium_users),
        f"${total_revenue:,.2f}",
        alerts_today,
        f"{conversion:.1f}%",
        f"${mrr:,.2f}"
    ]
}

df_metrics = pd.DataFrame(metrics_data)
st.dataframe(
    df_metrics,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Metric": st.column_config.TextColumn("Metric", width="medium"),
        "Value": st.column_config.TextColumn("Value", width="medium")
    }
)

st.markdown("---")

# ============================================================
# HISTORICAL TRENDS
# ============================================================
st.header("📊 Historical Trends")
historical = get_historical_data(30)

tab1, tab2, tab3 = st.tabs(["📈 Users", "💰 Revenue", "🔔 Alerts"])

with tab1:
    st.subheader("User Growth Over Time")
    if historical:
        df = pd.DataFrame(historical)
        df['date'] = pd.to_datetime(df['date'])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['date'], y=df['total_users'], name='Total Users', line=dict(color='blue', width=2)))
        fig.add_trace(go.Scatter(x=df['date'], y=df['trial_users'], name='Trial Users', line=dict(color='orange', width=2)))
        fig.add_trace(go.Scatter(x=df['date'], y=df['premium_users'], name='Premium Users', line=dict(color='green', width=2)))
        fig.update_layout(title="User Growth", xaxis_title="Date", yaxis_title="Number of Users", hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No historical data yet. Data will appear after a few days.")

with tab2:
    st.subheader("Revenue Over Time")
    if historical:
        df = pd.DataFrame(historical)
        df['date'] = pd.to_datetime(df['date'])
        fig = px.line(df, x='date', y='total_revenue', title='Total Revenue')
        fig.update_traces(line_color='green', line_width=3)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Revenue Breakdown")
        col1, col2 = st.columns(2)
        with col1:
            users_2dollar = len([u for u in premium_users if u.get('premium_price') == 2])
            users_4dollar = len([u for u in premium_users if u.get('premium_price') == 4])
            fig = go.Figure(data=[go.Pie(
                labels=['$2/month', '$4/month'],
                values=[users_2dollar, users_4dollar],
                hole=.3
            )])
            fig.update_layout(title="Premium Users by Price")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            revenue_2 = users_2dollar * 2
            revenue_4 = users_4dollar * 4
            st.metric("Revenue from $2 tier", f"${revenue_2:.2f}")
            st.metric("Revenue from $4 tier", f"${revenue_4:.2f}")
    else:
        st.info("No historical data yet.")

with tab3:
    st.subheader("Alerts Sent Over Time")
    if historical:
        df = pd.DataFrame(historical)
        df['date'] = pd.to_datetime(df['date'])
        fig = px.bar(df, x='date', y='alerts_sent', title='Daily Alerts Sent')
        fig.update_traces(marker_color='lightblue')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No historical data yet.")

st.markdown("---")

# ============================================================
# USER DETAILS
# ============================================================
st.header("👥 User Details")

if all_users:
    user_data = []
    for user in all_users:
        trial_ends = datetime.fromisoformat(user['trial_ends'])
        days_left = (trial_ends - datetime.now()).days
        status = "Premium" if user['premium'] else f"Trial ({days_left} days)"
        user_data.append({
            'Username': user['username'],
            'Name': user['name'],
            'Email': user['email'],
            'Status': status,
            'Joined': datetime.fromisoformat(user['created_at']).strftime('%Y-%m-%d'),
            'Premium Price': f"${user.get('premium_price', 0) or 0:.2f}" if user['premium'] else '-'
        })
    df_users = pd.DataFrame(user_data)
    st.dataframe(df_users, use_container_width=True, hide_index=True)

st.markdown("---")

# ============================================================
# RECENT ALERTS
# ============================================================
st.header("🔔 Recent Alerts Sent")

result = supabase.table('alert_history').select('*').order('sent_at', desc=True).limit(20).execute()
recent_alerts = result.data

if recent_alerts:
    alert_data = []
    for alert in recent_alerts:
        alert_data.append({
            'Time': datetime.fromisoformat(alert['sent_at']).strftime('%Y-%m-%d %H:%M:%S'),
            'User': alert['username'],
            'Symbol': alert['symbol'],
            'Price': f"${alert['price']:.2f}",
            'Target': f"${alert['target']:.2f}",
            'Type': alert['type'].upper()
        })
    df_alerts = pd.DataFrame(alert_data)
    st.dataframe(df_alerts, use_container_width=True, hide_index=True)
else:
    st.info("No alerts sent yet")

st.markdown("---")
st.caption("Dashboard updates in real-time. Refresh page for latest data.")

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div style='text-align: center; color: #999; font-size: 11px; padding: 10px;'>
Copyright 2026 Natts Digital. All rights reserved. | Admin Panel
</div>
""", unsafe_allow_html=True)
