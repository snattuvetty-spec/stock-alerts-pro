# 🚀 Deployment Guide - Stock Alerts Pro

## Step 1: Install Git (if not already installed)
Download from: https://git-scm.com/download/win

---

## Step 2: Create GitHub Account
Go to: https://github.com and sign up (free)

---

## Step 3: Create a New GitHub Repository
1. Click the **+** button → **New repository**
2. Name it: `stock-alerts-pro`
3. Set to **Private** (keeps your code safe)
4. Click **Create repository**

---

## Step 4: Upload Your Files to GitHub
Open Command Prompt in your project folder:
```
C:\Users\snatt\Documents\MY_APP_PROJECTS_NEW\PriceAlertApp\
```

Run these commands one by one:
```bash
git init
git add .
git commit -m "Initial deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/stock-alerts-pro.git
git push -u origin main
```

> Replace YOUR_USERNAME with your GitHub username

---

## Step 5: Deploy to Streamlit Cloud
1. Go to: https://share.streamlit.io
2. Sign in with your GitHub account
3. Click **New app**
4. Fill in:
   - **Repository**: YOUR_USERNAME/stock-alerts-pro
   - **Branch**: main
   - **Main file path**: web_app_database.py
5. Click **Advanced settings** → **Secrets** (see Step 6 first!)
6. Click **Deploy**

---

## Step 6: Add Your Secrets in Streamlit Cloud
In the **Secrets** box, paste this (fill in your actual values):

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-supabase-anon-key"

EMAIL_SENDER = "your-gmail@gmail.com"
EMAIL_PASSWORD = "your-gmail-app-password"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = "587"

TELEGRAM_BOT_TOKEN = "your-telegram-bot-token"
TELEGRAM_CHAT_ID = "your-telegram-chat-id"
```

> Find these values in your local .env file

---

## Step 7: Deploy Admin Dashboard (Optional)
Repeat Step 5 with:
- **Main file path**: admin_dashboard.py
- Add these extra secrets:
```toml
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "your-secure-admin-password"
```

---

## Your App URLs Will Be:
- **Main app**: https://YOUR_USERNAME-stock-alerts-pro-web-app-database-XXXXX.streamlit.app
- **Admin**: https://YOUR_USERNAME-stock-alerts-pro-admin-dashboard-XXXXX.streamlit.app

---

## Files Checklist
Make sure these files are in your project folder before pushing to GitHub:
- [x] web_app_database.py
- [x] admin_dashboard.py  
- [x] requirements.txt
- [x] .streamlit/config.toml
- [x] .gitignore
- [ ] .env  ← DO NOT push this! It's in .gitignore ✅

---

## Troubleshooting
**App crashes on startup?**
→ Check that all secrets are added in Streamlit Cloud settings

**Module not found error?**
→ Check requirements.txt has all packages listed

**Supabase connection fails?**
→ Double-check SUPABASE_URL and SUPABASE_KEY in secrets

---
*Natts Digital - Stock Alerts Pro*
