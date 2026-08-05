import time
import threading
import ccxt
from http.server import HTTPServer, BaseHTTPRequestHandler

# 1. Render Port Requirement Dummy Server
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running 24/7!")

def run_dummy_server():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHTTPRequestHandler)
    server.serve_forever()

# Background Thread me Dummy Server start karein
threading.Thread(target=run_dummy_server, daemon=True).start()

# ==============================================================
# API CREDENTIALS & CONFIGURATION
# ==============================================================
API_KEY = 'b450a76a2cf0724b0e2dddd69cd7675a'
SECRET_KEY = 'c8e6ef153aefea2dda2b36c0b3fad153'  # <--- Apni real Secret Key yahan paste karein

exchange = ccxt.delta({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
})

TIMEFRAME = '5m'

INITIAL_SL_PCT = 0.008     # Initial SL: 0.8%
TRAILING_STEP_PCT = 0.003  # Har 0.3% movement par SL trail hoga
TARGET_TP_PCT = 0.010      # Target: 1.0%

CONFIG = {
    'BTC/USDT': {'quantity': 0.045},
    'SOL/USDT': {'quantity': 10.0}
}

active_positions = {}

def check_sma(ohlcv):
    closes = [c[4] for c in ohlcv]
    sma_fast, sma_slow = sum(closes[-10:]) / 10, sum(closes[-30:]) / 30
    return 'BUY' if sma_fast > sma_slow else ('SELL' if sma_fast < sma_slow else None)

def check_rsi(ohlcv):
    closes = [c[4] for c in ohlcv]
    gains = [max(closes[-i] - closes[-i-1], 0) for i in range(1, 15)]
    losses = [max(-(closes[-i] - closes[-i-1]), 0) for i in range(1, 15)]
    avg_gain, avg_loss = sum(gains) / 14, sum(losses) / 14
    if avg_loss == 0: return None
    rsi = 100 - (100 / (1 + (avg_gain / avg_loss)))
    return 'BUY' if rsi < 38 else ('SELL' if rsi > 62 else None)

def check_breakout(ohlcv):
    highs, lows = [c[2] for c in ohlcv[-11:-1]], [c[3] for c in ohlcv[-11:-1]]
    curr = ohlcv[-1][4]
    return 'BUY' if curr > max(highs) else ('SELL' if curr < min(lows) else None)

def check_momentum(ohlcv):
    change = ((ohlcv[-1][4] - ohlcv[-6][4]) / ohlcv[-6][4]) * 100
    return 'BUY' if change > 0.3 else ('SELL' if change < -0.3 else None)

def run_quick_bot():
    for symbol, settings in CONFIG.items():
        try:
            qty = settings['quantity']
            ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=50)
            curr_price = ohlcv[-1][4]

            if symbol in active_positions:
                pos = active_positions[symbol]
                
                if pos['side'] == 'BUY':
                    if curr_price > pos['highest_price'] * (1 + TRAILING_STEP_PCT):
                        pos['highest_price'] = curr_price
                        pos['sl'] = curr_price * (1 - INITIAL_SL_PCT)
                        print(f"[{symbol}] Trailing SL Updated -> {pos['sl']:.2f}", flush=True)

                    if curr_price <= pos['sl']:
                        print(f"[{symbol}] SL Hit! Exit Position.", flush=True)
                        exchange.create_market_sell_order(symbol, qty)
                        del active_positions[symbol]
                    elif curr_price >= pos['tp']:
                        print(f"[{symbol}] Quick 1% Target Hit! Profit Booked.", flush=True)
                        exchange.create_market_sell_order(symbol, qty)
                        del active_positions[symbol]

            else:
                signals = [check_sma(ohlcv), check_rsi(ohlcv), check_breakout(ohlcv), check_momentum(ohlcv)]
                buy_votes, sell_votes = signals.count('BUY'), signals.count('SELL')

                if buy_votes >= 1 and sell_votes == 0:
                    sl = curr_price * (1 - INITIAL_SL_PCT)
                    tp = curr_price * (1 + TARGET_TP_PCT)
                    print(f">>> BUY ENTRY: {symbol} | Price: {curr_price} | TP (1%): {tp:.2f} | SL: {sl:.2f} <<<", flush=True)
                    exchange.create_market_buy_order(symbol, qty)
                    active_positions[symbol] = {'side': 'BUY', 'entry': curr_price, 'sl': sl, 'tp': tp, 'highest_price': curr_price}
                else:
                    print(f"[{symbol}] Checking Market... Price: {curr_price} | Votes (BUY: {buy_votes})", flush=True)

        except Exception as e:
            print(f"Error on {symbol}: {e}", flush=True)

if __name__ == '__main__':
    print("Quick-Target 1% Profit Bot Active...", flush=True)
    while True:
        run_quick_bot()
        time.sleep(60)
