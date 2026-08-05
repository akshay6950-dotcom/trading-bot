import time
import threading
import ccxt
from http.server import HTTPServer, BaseHTTPRequestHandler

# 1. Keep-Alive Web Server
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"High Win-Rate Scalping Bot (1 Trade Per Coin Limit Active)!")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_dummy_server():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# ==============================================================
# API CREDENTIALS & CONFIGURATION
# ==============================================================
API_KEY = 'b450a76a2cf0724b0e2dddd69cd7675a'
SECRET_KEY = 'c8e6ef153aefea2dda2b36c0b3fad153'

exchange = ccxt.delta({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
})

TIMEFRAME = '3m'           # 3-Minute chart for quick scalping
INITIAL_SL_PCT = 0.005     # Strict SL: 0.5% (Max Capital Safety)
TARGET_TP_PCT = 0.008      # Quick TP: 0.8% (High Win Rate)

CONFIG = {
    'BTC/USDT': {'quantity': 0.045},
    'SOL/USDT': {'quantity': 10.0}
}

# Stores active trades (Max 1 position per coin)
active_positions = {}

def get_ticker_price_and_candles(symbol):
    ticker = exchange.fetch_ticker(symbol)
    curr_price = ticker['last']
    ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=30)
    if not ohlcv or len(ohlcv) < 20:
        return curr_price, None
    return curr_price, ohlcv

# COMBINED HIGH-ACCURACY SCALPING STRATEGY
def analyze_scalp_signal(ohlcv):
    closes = [c[4] for c in ohlcv]
    
    # 1. EMA Trend Check (EMA 9 vs EMA 21)
    ema9 = sum(closes[-9:]) / 9
    ema21 = sum(closes[-21:]) / 21
    
    # 2. RSI Check (14 Period)
    gains = [max(closes[-i] - closes[-i-1], 0) for i in range(1, 15)]
    losses = [max(-(closes[-i] - closes[-i-1]), 0) for i in range(1, 15)]
    avg_gain, avg_loss = sum(gains) / 14, sum(losses) / 14
    if avg_loss == 0: return None
    rsi = 100 - (100 / (1 + (avg_gain / avg_loss)))

    # Entry Logic (Trend + Momentum)
    if ema9 > ema21 and rsi > 45 and rsi < 65:
        return 'BUY'
    elif ema9 < ema21 and rsi < 55 and rsi > 35:
        return 'SELL'
    
    return None

def run_quick_bot():
    for symbol, settings in CONFIG.items():
        try:
            qty = settings['quantity']
            curr_price, ohlcv = get_ticker_price_and_candles(symbol)

            # AGAR POSITION ALREADY OPEN HAI (STRICT LIMIT: MAXIMUM 1 TRADE PER COIN)
            if symbol in active_positions:
                pos = active_positions[symbol]
                
                # LONG POSITION MANAGEMENT
                if pos['side'] == 'BUY':
                    if curr_price <= pos['sl']:
                        print(f"[{symbol}] SL Hit! Exit Long.", flush=True)
                        exchange.create_market_sell_order(symbol, qty)
                        del active_positions[symbol]
                    elif curr_price >= pos['tp']:
                        print(f"[{symbol}] Target Hit! Long Profit Booked.", flush=True)
                        exchange.create_market_sell_order(symbol, qty)
                        del active_positions[symbol]

                # SHORT POSITION MANAGEMENT
                elif pos['side'] == 'SELL':
                    if curr_price >= pos['sl']:
                        print(f"[{symbol}] SL Hit! Exit Short.", flush=True)
                        exchange.create_market_buy_order(symbol, qty)
                        del active_positions[symbol]
                    elif curr_price <= pos['tp']:
                        print(f"[{symbol}] Target Hit! Short Profit Booked.", flush=True)
                        exchange.create_market_buy_order(symbol, qty)
                        del active_positions[symbol]

            # AGAR COIN ME KOI ACTIVE TRADE NAHI HAI TABHI NAYA TRADE LEGA
            else:
                if ohlcv is None:
                    print(f"[{symbol}] Price: {curr_price} | Scanning market...", flush=True)
                    continue

                signal = analyze_scalp_signal(ohlcv)

                # BUY ENTRY (LONG)
                if signal == 'BUY':
                    sl = curr_price * (1 - INITIAL_SL_PCT)
                    tp = curr_price * (1 + TARGET_TP_PCT)
                    print(f">>> BUY ENTRY (LONG): {symbol} | Price: {curr_price} | TP: {tp:.2f} | SL: {sl:.2f} <<<", flush=True)
                    exchange.create_market_buy_order(symbol, qty)
                    active_positions[symbol] = {'side': 'BUY', 'entry': curr_price, 'sl': sl, 'tp': tp}

                # SELL ENTRY (SHORT)
                elif signal == 'SELL':
                    sl = curr_price * (1 + INITIAL_SL_PCT)
                    tp = curr_price * (1 - TARGET_TP_PCT)
                    print(f">>> SELL ENTRY (SHORT): {symbol} | Price: {curr_price} | TP: {tp:.2f} | SL: {sl:.2f} <<<", flush=True)
                    exchange.create_market_sell_order(symbol, qty)
                    active_positions[symbol] = {'side': 'SELL', 'entry': curr_price, 'sl': sl, 'tp': tp}

                else:
                    print(f"[{symbol}] Scanning Market... Price: {curr_price} (No active trade)", flush=True)

        except Exception as e:
            print(f"Error on {symbol}: {e}", flush=True)

if __name__ == '__main__':
    print("Scalping Engine Active (Max 1 Trade Per Coin Limit Enabled)...", flush=True)
    while True:
        run_quick_bot()
        time.sleep(30)
