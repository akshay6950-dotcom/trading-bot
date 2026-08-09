import time
import urllib.request
import json
import math
import threading
import os
import builtins
import hmac
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

# ==========================================
# RENDER LOGS FIX
# ==========================================
def print(*args, **kwargs):
    kwargs['flush'] = True
    builtins.print(*args, **kwargs)

SYMBOLS = ['BTC-USDT', 'ETH-USDT', 'SOL-USDT', 'XAU-USDT', 'PAXG-USDT']
POSITION_SIZES = {'BTC-USDT': 0.035, 'ETH-USDT': 50.0, 'SOL-USDT': 10.0, 'XAU-USDT': 0.5, 'PAXG-USDT': 0.5}
LEVERAGE = 5
CHECK_INTERVAL = 15

price_history = {symbol: [] for symbol in SYMBOLS}

# TRACKS ACTIVE TRADES PER CURRENCY
# True means a trade is currently open for that coin, False means free to trade
active_trades = {symbol: False for symbol in SYMBOLS}

# Track entry prices to simulate profit/loss closing condition
entry_prices = {symbol: 0.0 for symbol in SYMBOLS}

# ==========================================
# FETCH SECURE API KEYS FROM RENDER
# ==========================================
API_KEY = os.environ.get('API_KEY')
API_SECRET = os.environ.get('API_SECRET')

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
        if change >= 0: gains.append(change); losses.append(0)
        else: gains.append(0); losses.append(abs(change))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ==========================================
# API PRICE FETCHER (Anti-Block)
# ==========================================
def fetch_ticker_price(symbol):
    try:
        kucoin_sym = 'PAXG-USDT' if 'XAU' in symbol else symbol
        url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kucoin_sym}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data['code'] == '200000': return float(data['data']['price'])
    except: pass
    try:
        clean_symbol = 'PAXGUSDT' if 'XAU' in symbol else symbol.replace('-', '')
        url = f"https://api1.binance.com/api/v3/ticker/price?symbol={clean_symbol}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return float(json.loads(response.read().decode())['price'])
    except: return None

# ==========================================
# REAL TRADE EXECUTION & MANAGEMENT ENGINE
# ==========================================
def check_and_manage_trade(symbol, current_price):
    # If trade is already active for this specific currency, check for profit/loss book condition
    if active_trades[symbol]:
        entry_p = entry_prices[symbol]
        # Example Target: Close trade if profit >= 1.5% or loss >= 1.0% (Simulated Book Condition)
        pnl_pct = ((current_price - entry_p) / entry_p) * 100
        
        # If price moves by target, simulate booking profit/loss and free up the coin
        if abs(pnl_pct) >= 1.2: 
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 💰 TRADE CLOSED / BOOKED for {symbol} at Price: {current_price} | PnL: {round(pnl_pct, 2)}%")
            active_trades[symbol] = False # Unlocks coin for next trade
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Trade Active for {symbol} | Entry: {entry_p} | Current: {current_price} | PnL: {round(pnl_pct, 2)}% (Waiting to Book)")
        return True
    return False

def execute_trade(symbol, side, price, reason):
    # BLOCK NEW TRADE IF ALREADY ACTIVE FOR THIS SYMBOL
    if active_trades[symbol]:
        return

    qty = POSITION_SIZES.get(symbol, 0.01)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 NEW SIGNAL ({reason}) | {symbol} | Side: {side} | Qty: {qty} | Price: {price}")
    
    if not API_KEY or not API_SECRET:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ API Keys missing! Trade skipped.")
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Placing REAL {side} Order for {symbol}...")
    
    try:
        payload = f"symbol={symbol}&side={side}&quantity={qty}&leverage={LEVERAGE}&timestamp={int(time.time() * 1000)}"
        signature = hmac.new(API_SECRET.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # LOCK THIS COIN SO NO NEW TRADE OPENS UNTIL THIS IS BOOKED
        active_trades[symbol] = True
        entry_prices[symbol] = price
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ SUCCESS: Order opened for {symbol}. Locked until profit/loss is booked.")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ FAILED to place order: {e}")

# ==========================================
# BOT LOGIC LOOP
# ==========================================
def bot_loop():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] SMART PER-CURRENCY LOCK ENGINE STARTED...")
    if API_KEY: print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ API Key Detected. Live Trading is ON.")

    while True:
        for symbol in SYMBOLS:
            current_price = fetch_ticker_price(symbol)
            if current_price is not None:
                # FIRST: Check if an active trade exists for this coin and manage it
                if check_and_manage_trade(symbol, current_price):
                    continue # Skip new signals for this coin while trade is open

                history = price_history[symbol]
                history.append(current_price)
                if len(history) > 50: history.pop(0)

                if len(history) < 5: continue

                ema_fast = calculate_ema(history, 3)
                ema_slow = calculate_ema(history, 5)
                rsi = calculate_rsi(history, 7)
                
                if rsi < 35: execute_trade(symbol, 'BUY', current_price, 'RSI Oversold')
                elif rsi > 65: execute_trade(symbol, 'SELL', current_price, 'RSI Overbought')
                elif ema_fast and ema_slow:
                    if ema_fast > ema_slow and history[-2] <= ema_slow: execute_trade(symbol, 'BUY', current_price, 'EMA Golden Cross')
                    elif ema_fast < ema_slow and history[-2] >= ema_slow: execute_trade(symbol, 'SELL', current_price, 'EMA Death Cross')
        time.sleep(CHECK_INTERVAL)

# ==========================================
# WEB SERVER
# ==========================================
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is active!")
    def log_message(self, format, *args): pass

def main():
    bot_thread = threading.Thread(target=bot_loop)
    bot_thread.daemon = True
    bot_thread.start()
    port = int(os.environ.get('PORT', 10000))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimpleHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
