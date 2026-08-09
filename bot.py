import time
import requests
import math
import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

# ==========================================
# CONFIGURATION & PARAMETERS
# ==========================================
SYMBOLS = ['BTC-USDT', 'ETH-USDT', 'SOL-USDT', 'XAU-USDT', 'PAXG-USDT']
POSITION_SIZES = {'BTC-USDT': 0.035, 'ETH-USDT': 50.0, 'SOL-USDT': 10.0, 'XAU-USDT': 0.5, 'PAXG-USDT': 0.5}
LEVERAGE = 5
CHECK_INTERVAL = 15

price_history = {symbol: [] for symbol in SYMBOLS}
active_trades = {symbol: False for symbol in SYMBOLS}

# ==========================================
# TECHNICAL INDICATORS
# ==========================================
def calculate_ema(prices, period):
    if len(prices) < period: return None
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]: ema = (price * k) + (ema * (1 - k))
    return ema

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    gains, losses = [], []
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
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger_bands(prices, period=20):
    if len(prices) < period: return None, None
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
        if response.status_code == 200: return float(response.json()['price'])
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
# BOT LOGIC LOOP (RUNS IN BACKGROUND)
# ==========================================
def bot_loop():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] High-Frequency Bot Engine Started (ETH, GOLD, SOL, BTC)...")
    while True:
        for symbol in SYMBOLS:
            current_price = fetch_ticker_price(symbol)
            if current_price is not None:
                history = price_history[symbol]
                history.append(current_price)
                if len(history) > 50: history.pop(0)

                if len(history) < 5:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [{symbol}] Price: {current_price} | Gathering Data ({len(history)}/5)...")
                    continue

                ema_fast = calculate_ema(history, 3)
                ema_slow = calculate_ema(history, 5)
                rsi = calculate_rsi(history, 7)
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [{symbol}] Price: {current_price} | RSI: {round(rsi,1)}")

                if rsi < 35: execute_trade(symbol, 'BUY', current_price, 'RSI Oversold')
                elif rsi > 65: execute_trade(symbol, 'SELL', current_price, 'RSI Overbought')
                elif ema_fast and ema_slow:
                    if ema_fast > ema_slow and history[-2] <= ema_slow: execute_trade(symbol, 'BUY', current_price, 'EMA Golden Cross')
                    elif ema_fast < ema_slow and history[-2] >= ema_slow: execute_trade(symbol, 'SELL', current_price, 'EMA Death Cross')
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [{symbol}] API Error, Retrying...")
        time.sleep(CHECK_INTERVAL)

# ==========================================
# WEB SERVER (RUNS IN MAIN THREAD FOR RENDER)
# ==========================================
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    def log_message(self, format, *args): pass

def main():
    bot_thread = threading.Thread(target=bot_loop)
    bot_thread.daemon = True
    bot_thread.start()

    port = int(os.environ.get('PORT', 10000))
    server_address = ('0.0.0.0', port)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Web Server binding to port {port} for Render...")
    httpd = HTTPServer(server_address, SimpleHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
