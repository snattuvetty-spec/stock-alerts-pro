import requests
import time
from plyer import notification
from datetime import datetime

def get_stock_price(symbol):
    """
    Fetch stock price using Yahoo Finance API (free, no key needed)
    symbol: Stock ticker like 'AAPL', 'TSLA', 'MSFT'
    """
    try:
        # Using a reliable free endpoint
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # Extract current price
        if 'chart' in data and 'result' in data['chart']:
            result = data['chart']['result'][0]
            current_price = result['meta']['regularMarketPrice']
            return current_price
        else:
            print(f"  ⚠️ Could not find price for {symbol}")
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

def check_alert(alert_config, current_price, alert_history):
    """Check if alert condition is met"""
    symbol = alert_config['symbol']
    target_price = alert_config['target']
    alert_type = alert_config['type']
    
    if current_price is None:
        return False
    
    # Create unique key for this alert
    alert_key = f"{symbol}_{alert_type}_{target_price}"
    
    # Check if we already sent this alert recently (avoid spam)
    if alert_key in alert_history:
        time_since_last = time.time() - alert_history[alert_key]
        if time_since_last < 3600:  # Don't repeat within 1 hour
            return False
    
    triggered = False
    
    if alert_type == 'above' and current_price >= target_price:
        send_notification(
            title=f"🚀 {symbol} Price Alert!",
            message=f"Price is ${current_price:.2f} - ABOVE your target of ${target_price:.2f}!"
        )
        triggered = True
        
    elif alert_type == 'below' and current_price <= target_price:
        send_notification(
            title=f"📉 {symbol} Price Alert!",
            message=f"Price is ${current_price:.2f} - BELOW your target of ${target_price:.2f}!"
        )
        triggered = True
    
    if triggered:
        alert_history[alert_key] = time.time()
        print(f"  ✅ ALERT TRIGGERED: {symbol} ${current_price:.2f}")
    
    return triggered

def monitor_stocks(alerts, check_interval=60):
    """Monitor multiple stock price alerts"""
    alert_history = {}
    
    print("=" * 50)
    print("    📊 US STOCK PRICE ALERT SYSTEM 📊")
    print("=" * 50)
    print(f"\nMonitoring {len(alerts)} alert(s):\n")
    
    for alert in alerts:
        print(f"  • {alert['symbol']}: Alert when price goes {alert['type']} ${alert['target']:.2f}")
    
    print(f"\nChecking every {check_interval} seconds...")
    print("Market hours: 9:30 AM - 4:00 PM ET (Mon-Fri)")
    print("\n" + "=" * 50 + "\n")
    
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Checking prices...")
        
        # Get list of unique stock symbols
        symbols = list(set([alert['symbol'] for alert in alerts]))
        
        # Fetch prices
        prices = {}
        for symbol in symbols:
            price = get_stock_price(symbol)
            if price:
                prices[symbol] = price
                print(f"  {symbol}: ${price:.2f}")
            time.sleep(0.3)  # Small delay between requests
        
        # Check all alerts
        print()
        for alert in alerts:
            symbol = alert['symbol']
            if symbol in prices:
                check_alert(alert, prices[symbol], alert_history)
        
        print(f"\n⏳ Next check in {check_interval} seconds...\n")
        time.sleep(check_interval)

# CONFIGURE YOUR STOCK ALERTS HERE
if __name__ == "__main__":
    
    # List of stock alerts you want to monitor
    # Popular stock symbols: AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, NFLX
    
    my_alerts = [
        {
            'symbol': 'AAPL',      # Apple
            'target': 230.00,
            'type': 'above'
        },
        {
            'symbol': 'TSLA',      # Tesla
            'target': 350.00,
            'type': 'above'
        },
        {
            'symbol': 'MSFT',      # Microsoft
            'target': 420.00,
            'type': 'below'
        },
        {
            'symbol': 'NVDA',      # NVIDIA
            'target': 140.00,
            'type': 'above'
        }
    ]
    
    # Start monitoring
    monitor_stocks(my_alerts, check_interval=60)