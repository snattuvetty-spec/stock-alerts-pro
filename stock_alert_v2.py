import requests
import time
import json
import os
from plyer import notification
from datetime import datetime

ALERTS_FILE = "my_alerts.json"

def get_stock_price(symbol):
    """Fetch stock price using Yahoo Finance API"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if 'chart' in data and 'result' in data['chart']:
            result = data['chart']['result'][0]
            current_price = result['meta']['regularMarketPrice']
            return current_price
        else:
            return None
            
    except Exception as e:
        print(f"  ⚠️ Error fetching {symbol}: {e}")
        return None

def send_notification(title, message):
    """Send a desktop notification"""
    notification.notify(
        title=title,
        message=message,
        app_name="Stock Alert",
        timeout=10
    )

def load_alerts():
    """Load alerts from JSON file"""
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, 'r') as f:
                alerts = json.load(f)
                print(f"✅ Loaded {len(alerts)} alert(s) from {ALERTS_FILE}")
                return alerts
        except Exception as e:
            print(f"⚠️ Error loading alerts: {e}")
            return []
    else:
        print(f"ℹ️ No saved alerts found. Creating default alerts...")
        return create_default_alerts()

def save_alerts(alerts):
    """Save alerts to JSON file"""
    try:
        with open(ALERTS_FILE, 'w') as f:
            json.dump(alerts, f, indent=2)
        print(f"✅ Alerts saved to {ALERTS_FILE}")
    except Exception as e:
        print(f"⚠️ Error saving alerts: {e}")

def create_default_alerts():
    """Create default alerts for first-time users"""
    default_alerts = [
        {'symbol': 'AAPL', 'target': 230.00, 'type': 'above', 'enabled': True},
        {'symbol': 'TSLA', 'target': 350.00, 'type': 'above', 'enabled': True},
        {'symbol': 'MSFT', 'target': 420.00, 'type': 'below', 'enabled': True},
        {'symbol': 'NVDA', 'target': 140.00, 'type': 'above', 'enabled': True}
    ]
    save_alerts(default_alerts)
    return default_alerts

def add_alert_interactive():
    """Add a new alert interactively"""
    print("\n" + "=" * 50)
    print("ADD NEW ALERT")
    print("=" * 50)
    
    symbol = input("Enter stock symbol (e.g., AAPL): ").upper().strip()
    
    # Test if symbol is valid
    price = get_stock_price(symbol)
    if price is None:
        print(f"❌ Could not fetch price for {symbol}. Invalid symbol?")
        return None
    
    print(f"Current price of {symbol}: ${price:.2f}")
    
    try:
        target = float(input("Enter target price: $"))
        alert_type = input("Alert when price goes (above/below): ").lower().strip()
        
        if alert_type not in ['above', 'below']:
            print("❌ Invalid type. Use 'above' or 'below'")
            return None
        
        new_alert = {
            'symbol': symbol,
            'target': target,
            'type': alert_type,
            'enabled': True
        }
        
        print(f"✅ Alert created: {symbol} - {alert_type} ${target:.2f}")
        return new_alert
        
    except ValueError:
        print("❌ Invalid price entered")
        return None

def show_menu():
    """Display interactive menu"""
    print("\n" + "=" * 50)
    print("STOCK ALERT MENU")
    print("=" * 50)
    print("1. Start monitoring")
    print("2. Add new alert")
    print("3. View all alerts")
    print("4. Delete alert")
    print("5. Exit")
    print("=" * 50)
    
    choice = input("\nEnter choice (1-5): ").strip()
    return choice

def view_alerts(alerts):
    """Display all alerts"""
    print("\n" + "=" * 50)
    print("YOUR ALERTS")
    print("=" * 50)
    
    if not alerts:
        print("No alerts configured.")
        return
    
    for i, alert in enumerate(alerts, 1):
        status = "✅ ON" if alert.get('enabled', True) else "❌ OFF"
        print(f"{i}. {alert['symbol']}: {alert['type']} ${alert['target']:.2f} - {status}")

def delete_alert(alerts):
    """Delete an alert"""
    view_alerts(alerts)
    
    if not alerts:
        return alerts
    
    try:
        choice = int(input("\nEnter alert number to delete (0 to cancel): "))
        if choice == 0:
            return alerts
        if 1 <= choice <= len(alerts):
            removed = alerts.pop(choice - 1)
            print(f"✅ Deleted alert: {removed['symbol']} {removed['type']} ${removed['target']:.2f}")
            save_alerts(alerts)
        else:
            print("❌ Invalid number")
    except ValueError:
        print("❌ Invalid input")
    
    return alerts

def check_alert(alert_config, current_price, alert_history):
    """Check if alert condition is met"""
    if not alert_config.get('enabled', True):
        return False
    
    symbol = alert_config['symbol']
    target_price = alert_config['target']
    alert_type = alert_config['type']
    
    if current_price is None:
        return False
    
    alert_key = f"{symbol}_{alert_type}_{target_price}"
    
    if alert_key in alert_history:
        time_since_last = time.time() - alert_history[alert_key]
        if time_since_last < 3600:
            return False
    
    triggered = False
    
    if alert_type == 'above' and current_price >= target_price:
        send_notification(
            title=f"🚀 {symbol} Price Alert!",
            message=f"Price is ${current_price:.2f} - ABOVE ${target_price:.2f}!"
        )
        triggered = True
        
    elif alert_type == 'below' and current_price <= target_price:
        send_notification(
            title=f"📉 {symbol} Price Alert!",
            message=f"Price is ${current_price:.2f} - BELOW ${target_price:.2f}!"
        )
        triggered = True
    
    if triggered:
        alert_history[alert_key] = time.time()
        print(f"  ✅ ALERT TRIGGERED: {symbol} ${current_price:.2f}")
    
    return triggered

def monitor_stocks(alerts, check_interval=60):
    """Monitor stock prices"""
    alert_history = {}
    
    print("\n" + "=" * 50)
    print("    📊 MONITORING STOCKS 📊")
    print("=" * 50)
    print(f"\nMonitoring {len(alerts)} alert(s)")
    print(f"Check interval: {check_interval} seconds")
    print("\nPress Ctrl+C to stop and return to menu\n")
    print("=" * 50 + "\n")
    
    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] Checking prices...")
            
            symbols = list(set([alert['symbol'] for alert in alerts if alert.get('enabled', True)]))
            
            prices = {}
            for symbol in symbols:
                price = get_stock_price(symbol)
                if price:
                    prices[symbol] = price
                    print(f"  {symbol}: ${price:.2f}")
                time.sleep(0.3)
            
            print()
            for alert in alerts:
                symbol = alert['symbol']
                if symbol in prices:
                    check_alert(alert, prices[symbol], alert_history)
            
            print(f"\n⏳ Next check in {check_interval} seconds...\n")
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print("\n\n✅ Monitoring stopped. Returning to menu...")

# MAIN PROGRAM
if __name__ == "__main__":
    print("=" * 50)
    print("    📊 US STOCK PRICE ALERT SYSTEM 📊")
    print("=" * 50)
    
    alerts = load_alerts()
    
    while True:
        choice = show_menu()
        
        if choice == '1':
            if alerts:
                monitor_stocks(alerts, check_interval=60)
            else:
                print("\n❌ No alerts configured. Add some alerts first!")
                
        elif choice == '2':
            new_alert = add_alert_interactive()
            if new_alert:
                alerts.append(new_alert)
                save_alerts(alerts)
                
        elif choice == '3':
            view_alerts(alerts)
            
        elif choice == '4':
            alerts = delete_alert(alerts)
            
        elif choice == '5':
            print("\n👋 Goodbye!")
            break
            
        else:
            print("\n❌ Invalid choice. Try again.")
