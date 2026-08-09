import time
import requests
import math
import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

# ==========================================
# BACKGROUND WEB SERVER (TO KEEP RENDER ALIVE)
# ==========================================
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    
    # Hide web server logs from console to keep it clean
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get('PORT', 10000))
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleHandler)
    httpd.serve_forever()

# ==========================================
# CONFIGURATION & PARAMETERS
# ==========================================
SYMBOLS = [
    'BTC-USDT',
    'ETH-USDT',
    'SOL-USDT',
    'XAU-USDT',  # Gold
    'PAXG-USDT'  # Gold Alternative
]

POSITION_SIZES = {
    'BTC-USDT': 0.035,
    'ETH-USDT': 50.0,
    'SOL-USDT': 10.0,
    'XAU-USDT': 0.5,
    'PAXG-USDT': 0.5
}

LEVERAGE = 5  # Fixed 5x Margin
CHECK_INTERVAL = 15  # Scan every 15 seconds

price_history = {symbol: [] for symbol in SYMBOLS}
active_trades = {symbol: False for symbol in SYMBOLS}

# ==========================================
# TECHNICAL INDICATORS (PURE PYTHON)
# ==========================================
def calculate_ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = (price * k) + (ema * (1 - k))
    return ema

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change >= 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
            
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger_bands(prices, period=20):
    if len(prices) < period:
        return None, None
    sub_prices = prices[-period:]
    sma = sum(sub_prices) / period
    variance = sum((x - sma) ** 2 for x in sub_prices) / period
    std = math.sqrt(variance)
    return sma + (2 * std), sma - (2 * std)

# ==========================================
# FETCH PRICE & EXECUTE
# ==========================================
def fetch_ticker_price(symbol):
    try:
        clean_symbol = symbol.replace('-', '')
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={clean_symbol}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return float(response.json()['price'])
        
        if 'SOL' in symbol:
            res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd", timeout=5).json()
            return float(res['solana']['usd'])
        return None
    except Exception:
        return None

def execute_trade(symbol, side, price, reason):
    qty = POSITION_SIZES.get(symbol, 0.01)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 SIGNAL TRIGGERED ({reason}) | {symbol} | Side: {side} | Qty: {qty} | Margin: {LEVERAGE}x | Price: {price}")
    active_trades[symbol] = True

# ==========================================
# MULTI-STRATEGY ENGINE
# ==========================================
def analyze_market_and_trade(symbol, current_price):
    history = price_history[symbol]
    history.append(current_price)
    
    if len(history) > 50:
        history.pop(0)

    if len(history) < 5:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{symbol}] Price: {current_price} | Building Indicator Data ({len(history)}/5)...")
        return

    ema_fast = calculate_ema(history, 3)
    ema_slow = calculate_ema(history, 5)
    rsi = calculate_rsi(history, 7)
    upper_bb, lower_bb = calculate_bollinger_bands(history, 10)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] [{symbol}] Price: {current_price} | RSI: {round(rsi,1)} | Fast EMA: {round(ema_fast,1) if ema_fast else 'N/A'}")

    # Strategy Triggers
    if rsi < 35:
        execute_trade(symbol, 'BUY', current_price, 'RSI Oversold Breakout')
        return
    elif rsi > 65:
        execute_trade(symbol, 'SELL', current_price, 'RSI Overbought Breakout')
        return

    if ema_fast and ema_slow:
        if ema_fast > ema_slow and history[-2] <= ema_slow:
            execute_trade(symbol, 'BUY', current_price, 'EMA Golden Cross')
            return
        elif ema_fast < ema_slow and history[-2] >= ema_slow:
            execute_trade(symbol, 'SELL', current_price, 'EMA Death Cross')
            return

    if upper_bb and lower_bb:
        if current_price < lower_bb:
            execute_trade(symbol, 'BUY', current_price, 'Bollinger Lower Band Rebound')
            return
        elif current_price > upper_bb:
            execute_trade(symbol, 'SELL', current_price, 'Bollinger Upper Band Rejection')
            return

# ==========================================
# MAIN LOOP
# ==========================================
def main():
    # 1. Start the web server in the background so Render approves the deploy
    threading.Thread(target=run_server, daemon=True).start()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Web server started. Render will now accept the deployment.")
    
    # 2. Start the actual bot logic
    print(f"[{datetime.now().strftime('%H:%M:%S')}] High-Frequency Engine Active (5x Leverage)...")
    
    while True:
        for symbol in SYMBOLS:
            price = fetch_ticker_price(symbol)
            if price is not None:
                analyze_market_and_trade(symbol, price)
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [{symbol}] Price: Retrying stream...")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
