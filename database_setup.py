from supabase import create_client, Client
import os
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

# Initialize Supabase client
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def setup_database():
    """Create database tables"""
    
    print("Setting up database tables...")
    
    # Note: Supabase tables are created via SQL in the Supabase dashboard
    # We'll create them through the dashboard SQL editor
    
    print("""
    
    ╔══════════════════════════════════════════════════════════════╗
    ║  DATABASE SETUP INSTRUCTIONS                                  ║
    ╚══════════════════════════════════════════════════════════════╝
    
    Go to your Supabase dashboard and run these SQL commands:
    
    1. Go to: https://scsgrssnaliirjmamwck.supabase.co
    2. Click on "SQL Editor" in the left sidebar
    3. Click "New Query"
    4. Copy and paste the SQL below:
    
    """)
    
    sql_commands = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email VARCHAR(255),
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    trial_ends TIMESTAMP,
    premium BOOLEAN DEFAULT FALSE,
    premium_price DECIMAL(10,2),
    premium_activated TIMESTAMP
);

-- Settings table
CREATE TABLE IF NOT EXISTS user_settings (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    email_enabled BOOLEAN DEFAULT FALSE,
    telegram_enabled BOOLEAN DEFAULT FALSE,
    telegram_chat_id VARCHAR(255),
    notification_method VARCHAR(50) DEFAULT 'both',
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    target DECIMAL(10,2) NOT NULL,
    type VARCHAR(10) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_notified TIMESTAMP,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

-- Daily metrics table (for historical tracking)
CREATE TABLE IF NOT EXISTS daily_metrics (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    total_users INTEGER DEFAULT 0,
    trial_users INTEGER DEFAULT 0,
    premium_users INTEGER DEFAULT 0,
    total_revenue DECIMAL(10,2) DEFAULT 0,
    alerts_sent INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Alert history table (tracks every alert sent)
CREATE TABLE IF NOT EXISTS alert_history (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    target DECIMAL(10,2) NOT NULL,
    type VARCHAR(10) NOT NULL,
    sent_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_alerts_username ON alerts(username);
CREATE INDEX IF NOT EXISTS idx_alert_history_date ON alert_history(sent_at);
CREATE INDEX IF NOT EXISTS idx_users_premium ON users(premium);
CREATE INDEX IF NOT EXISTS idx_users_trial ON users(trial_ends);
    """
    
    print(sql_commands)
    print("\n5. Click 'Run' to execute the SQL")
    print("\n6. Then run: python database_setup.py --migrate")
    print("   (This will migrate your existing JSON data)\n")

def migrate_json_data():
    """Migrate existing JSON data to database"""
    
    print("\n📦 Migrating existing JSON data to database...\n")
    
    # Migrate users
    if os.path.exists('users_database.json'):
        with open('users_database.json', 'r') as f:
            users_data = json.load(f)
        
        for username, user_info in users_data.items():
            try:
                # Insert user
                result = supabase.table('users').insert({
                    'username': username,
                    'password_hash': user_info['password'],
                    'email': user_info.get('email', ''),
                    'name': user_info.get('name', ''),
                    'created_at': user_info.get('created', datetime.now().isoformat()),
                    'trial_ends': (datetime.fromisoformat(user_info.get('created', datetime.now().isoformat())) + 
                                 timedelta(days=7)).isoformat(),
                    'premium': False
                }).execute()
                
                print(f"✅ Migrated user: {username}")
                
            except Exception as e:
                print(f"⚠️  User {username} already exists or error: {e}")
    
    # Migrate alerts and settings
    alerts_dir = 'user_alerts'
    if os.path.exists(alerts_dir):
        for username_dir in os.listdir(alerts_dir):
            user_path = os.path.join(alerts_dir, username_dir)
            
            # Migrate alerts
            alerts_file = os.path.join(user_path, 'alerts.json')
            if os.path.exists(alerts_file):
                with open(alerts_file, 'r') as f:
                    alerts = json.load(f)
                
                for alert in alerts:
                    try:
                        supabase.table('alerts').insert({
                            'username': username_dir,
                            'symbol': alert['symbol'],
                            'target': alert['target'],
                            'type': alert['type'],
                            'enabled': alert.get('enabled', True),
                            'created_at': alert.get('created', datetime.now().isoformat())
                        }).execute()
                    except Exception as e:
                        print(f"⚠️  Alert exists: {username_dir}/{alert['symbol']}")
            
            # Migrate settings
            settings_file = os.path.join(user_path, 'settings.json')
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                
                try:
                    supabase.table('user_settings').insert({
                        'username': username_dir,
                        'email': settings.get('email', ''),
                        'email_enabled': settings.get('email_enabled', False),
                        'telegram_enabled': settings.get('telegram_enabled', False),
                        'telegram_chat_id': settings.get('telegram_chat_id', ''),
                        'notification_method': settings.get('notification_method', 'both')
                    }).execute()
                    
                    print(f"✅ Migrated settings for: {username_dir}")
                except Exception as e:
                    print(f"⚠️  Settings exist: {username_dir}")
    
    print("\n✅ Migration complete!\n")

if __name__ == "__main__":
    import sys
    from datetime import timedelta
    
    if len(sys.argv) > 1 and sys.argv[1] == '--migrate':
        migrate_json_data()
    else:
        setup_database()