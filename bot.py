import time
import urllib.request
import json
import math
import threading
import os
import builtins
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

# ==========================================
# RENDER LOGS FIX
# ==========================================
def print(*args, **kwargs):
    kwargs['flush'] = True
    builtins.print(*args, **kwargs)

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
# ANTI-BLOCK API FETCHER (KuCoin + Binance Alt)
# ==========================================
def fetch_ticker_price(symbol):
    # 1. KuCoin API (Primary - Super friendly with Cloud servers)
    try:
        kucoin_sym = 'PAXG-USDT' if 'XAU' in symbol else symbol
        url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kucoin_sym}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data['code'] == '200000':
                return float(data['data']['price'])
    except Exception:
        pass

    # 2. Binance Alternative API (Secondary Fallback)
    try:
        clean_symbol = 'PAXGUSDT' if 'XAU' in symbol else symbol.replace('-', '')
        url = f"https://api1.binance.com/api/v3/ticker/price?symbol={clean_symbol}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return float(json.loads(response.read().decode())['price'])
    except Exception:
        return None

def execute_trade(symbol, side, price, reason):
    qty = POSITION_SIZES.get(symbol, 0.01)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 SIGNAL TRIGGERED ({reason}) | {symbol} | Side: {side} | Qty: {qty} | Margin: {LEVERAGE}x | Price: {price}")
    active_trades[symbol] = True

# ==========================================
# BOT LOGIC LOOP
# ==========================================
def bot_loop():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bot Engine Started (ETH, GOLD, SOL, BTC) with Anti-Block APIs...")
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
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [{symbol}] API Blocked / Retrying in next cycle...")
        time.sleep(CHECK_INTERVAL)

# ==========================================
# WEB SERVER
# ==========================================
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is active and bypassing blocks!")
    def log_message(self, format, *args): pass

def main():
    bot_thread = threading.Thread(target=bot_loop)
    bot_thread.daemon = True
    bot_thread.start()

    port = int(os.environ.get('PORT', 10000))
    server_address = ('0.0.0.0', port)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Web Server binding to port {port}...")
    httpd = HTTPServer(server_address, SimpleHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
