import requests
import time
from plyer import notification

def get_crypto_price(symbol):
    """Fetch current crypto price from CoinGecko API"""
    try:
        # CoinGecko free API - no key needed
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
        response = requests.get(url)
        data = response.json()
        price = data[symbol]['usd']
        return price
    except Exception as e:
        print(f"Error fetching price: {e}")
        return None

def send_notification(title, message):
    """Send a desktop notification"""
    notification.notify(
        title=title,
        message=message,
        app_name="Price Alert",
        timeout=10  # Notification stays for 10 seconds
    )

def check_price_alert(crypto_id, target_price, alert_type):
    """
    Check if price meets criteria and send alert
    crypto_id: e.g., 'bitcoin', 'ethereum'
    target_price: your target price in USD
    alert_type: 'above' or 'below'
    """
    current_price = get_crypto_price(crypto_id)
    
    if current_price is None:
        print("Could not fetch price. Will try again...")
        return
    
    print(f"{crypto_id.upper()} current price: ${current_price:,.2f}")
    
    # Check if alert condition is met
    if alert_type == 'above' and current_price >= target_price:
        send_notification(
            title=f"🚀 {crypto_id.upper()} Price Alert!",
            message=f"Price is ${current_price:,.2f} - ABOVE your target of ${target_price:,.2f}!"
        )
        print("✅ Alert sent!")
        
    elif alert_type == 'below' and current_price <= target_price:
        send_notification(
            title=f"📉 {crypto_id.upper()} Price Alert!",
            message=f"Price is ${current_price:,.2f} - BELOW your target of ${target_price:,.2f}!"
        )
        print("✅ Alert sent!")
    else:
        print("No alert triggered.")

# MAIN PROGRAM STARTS HERE
if __name__ == "__main__":
    print("=== Crypto Price Alert App ===")
    print("Starting price monitoring...\n")
    
    # Example: Alert when Bitcoin goes above $100,000
    crypto_to_watch = "bitcoin"
    target_price = 69100
    alert_type = "below"  # Change to "below" if you want alerts when price drops
    
    # Check price every 60 seconds
    while True:
        check_price_alert(crypto_to_watch, target_price, alert_type)
        print("Waiting 60 seconds before next check...\n")
        time.sleep(60)  # Wait 60 seconds
