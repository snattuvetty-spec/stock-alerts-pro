import requests
import time
from plyer import notification
from datetime import datetime

# Mapping of common names to CoinCap IDs
CRYPTO_MAP = {
    'bitcoin': 'bitcoin',
    'ethereum': 'ethereum',
    'solana': 'solana',
    'cardano': 'cardano',
    'dogecoin': 'dogecoin',
    'ripple': 'ripple',
    'polkadot': 'polkadot',
    'litecoin': 'litecoin',
    'chainlink': 'chainlink',
    'polygon': 'polygon-pos'
}

def get_crypto_price_coincap(crypto_id):
    """Fetch crypto price from CoinCap API (better rate limits)"""
    try:
        # Map to CoinCap ID if needed
        coincap_id = CRYPTO_MAP.get(crypto_id, crypto_id)
        
        url = f"https://api.coincap.io/v2/assets/{coincap_id}"
        response = requests.get(url)
        data = response.json()
        
        if 'data' in data and 'priceUsd' in data['data']:
            price = float(data['data']['priceUsd'])
            return price
        else:
            print(f"  ⚠️ Could not find price for {crypto_id}")
            return None
            
    except Exception as e:
        print(f"  ⚠️ Error fetching {crypto_id}: {e}")
        return None

def send_notification(title, message):
    """Send a desktop notification"""
    notification.notify(
        title=title,
        message=message,
        app_name="Price Alert",
        timeout=10
    )

def check_alert(alert_config, current_price, alert_history):
    """Check a single alert configuration"""
    crypto_id = alert_config['crypto']
    target_price = alert_config['target']
    alert_type = alert_config['type']
    
    if current_price is None:
        return False
    
    # Create unique key for this alert
    alert_key = f"{crypto_id}_{alert_type}_{target_price}"
    
    # Check if we already sent this alert recently (avoid spam)
    if alert_key in alert_history:
        time_since_last = time.time() - alert_history[alert_key]
        if time_since_last < 3600:  # Don't repeat same alert within 1 hour
            return False
    
    triggered = False
    
    if alert_type == 'above' and current_price >= target_price:
        send_notification(
            title=f"🚀 {crypto_id.upper()} Price Alert!",
            message=f"Price is ${current_price:,.2f} - ABOVE ${target_price:,.2f}!"
        )
        triggered = True
        
    elif alert_type == 'below' and current_price <= target_price:
        send_notification(
            title=f"📉 {crypto_id.upper()} Price Alert!",
            message=f"Price is ${current_price:,.2f} - BELOW ${target_price:,.2f}!"
        )
        triggered = True
    
    if triggered:
        alert_history[alert_key] = time.time()
        print(f"  ✅ ALERT TRIGGERED: {crypto_id.upper()} ${current_price:,.2f}")
    
    return triggered

def monitor_prices(alerts, check_interval=60):
    """Monitor multiple price alerts"""
    alert_history = {}
    
    print("=== Multi-Crypto Price Alert System ===")
    print(f"Monitoring {len(alerts)} alert(s)\n")
    
    for alert in alerts:
        print(f"  • {alert['crypto'].upper()}: Alert when price goes {alert['type']} ${alert['target']:,.2f}")
    
    print(f"\nChecking every {check_interval} seconds...")
    print("Using CoinCap API (better free limits)\n")
    
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Checking prices...")
        
        # Get list of unique cryptos to check
        crypto_list = list(set([alert['crypto'] for alert in alerts]))
        
        # Fetch prices one by one (with small delay to be nice to the API)
        prices = {}
        for crypto in crypto_list:
            price = get_crypto_price_coincap(crypto)
            if price:
                prices[crypto] = price
                print(f"  {crypto.upper()}: ${price:,.2f}")
            time.sleep(0.5)  # Small delay between requests
        
        # Check all alerts
        print()
        for alert in alerts:
            crypto = alert['crypto']
            if crypto in prices:
                check_alert(alert, prices[crypto], alert_history)
        
        print(f"\n⏳ Next check in {check_interval} seconds...\n")
        time.sleep(check_interval)

# CONFIGURE YOUR ALERTS HERE
if __name__ == "__main__":
    
    # List of alerts you want to monitor
    my_alerts = [
        {
            'crypto': 'bitcoin',
            'target': 71000,
            'type': 'above'  # Alert when Bitcoin goes above $71,000
        },
        {
            'crypto': 'ethereum',
            'target': 2100,
            'type': 'above'  # Alert when Ethereum goes above $2,100
        },
        {
            'crypto': 'bitcoin',
            'target': 69000,
            'type': 'below'  # Alert when Bitcoin drops below $69,000
        },
        {
            'crypto': 'solana',
            'target': 150,
            'type': 'above'  # Alert when Solana goes above $150
        }
    ]
    
    # Start monitoring (checks every 60 seconds)
    monitor_prices(my_alerts, check_interval=60)