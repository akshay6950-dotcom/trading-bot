import time
import logging
import threading
import os
from flask import Flask
import ccxt
import pandas as pd
import pandas_ta as ta

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - INFO - %(message)s')

# Active trades tracker for both coins
active_trades = {
    'SOLUSDT': None,
    'BTCUSDT': None
}

# Fixed Quantities
QUANTITIES = {
    'SOLUSDT': 25.0,     
    'BTCUSDT': 0.035     
}

# --- API KEYS ---
API_KEY = 'b450a76a2cf0724b0e2dddd69cd7675a' 
API_SECRET = 'c8e6ef153aefea2dda2b36c0b3fad153'

# Connect to Exchange 
try:
    exchange = ccxt.delta({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True,
    })
    logging.info("Exchange API Connected Successfully!")
except Exception as e:
    logging.error(f"Exchange connection error: {e}")

def fetch_market_data(symbol):
    """Fetches LIVE data and calculates indicators for specific symbol."""
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=250)
        if not bars or len(bars) == 0:
            logging.error(f"Exchange ne {symbol} ke liye koi data nahi bheja!")
            return None

        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Calculate Indicators
        df.ta.ema(length=50, append=True)
        df.ta.ema(length=200, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.rsi(length=14, append=True)
        df['vol_ma'] = df['volume'].rolling(window=20).mean()

        latest = df.iloc[-1]
        
        data = {
            'price': float(latest['close']),
            'ema_50': float(latest['EMA_50']),
            'ema_200': float(latest['EMA_200']),
            'macd': float(latest['MACD_12_26_9']),
            'signal': float(latest['MACDs_12_26_9']),
            'rsi': float(latest['RSI_14']),
            'vol': float(latest['volume']),
            'vol_ma': float(latest['vol_ma'])
        }
        return data
    except Exception as e:
        logging.error(f"Data fetch error for {symbol}: {e}")
        return None

def check_strategies(symbol, data):
    price, ema_50, ema_200 = data['price'], data['ema_50'], data['ema_200']
    macd, signal, rsi = data['macd'], data['signal'], data['rsi']
    vol, vol_ma = data['vol'], data['vol_ma']

    if symbol == 'SOLUSDT':
        # --- SOL Ki Purani 3 Strategies (UNCHANGED) ---
        strat_1 = (price > ema_50) and (ema_50 > ema_200) and (macd > signal) and (45 <= rsi <= 70)
        strat_2 = (rsi < 40) and (macd > signal) and (price > ema_200)
        strat_3 = (macd > signal) and (50 <= rsi <= 75) and (price > ema_50)

        if strat_1: return "SOL Strat 1 (Trend & Momentum)"
        elif strat_2: return "SOL Strat 2 (RSI Dip Recovery)"
        elif strat_3: return "SOL Strat 3 (Quick Scalp Momentum)"
    
    elif symbol == 'BTCUSDT':
        # --- BTC Ki 3 Nayi Strategies (For MORE TRADES) ---
        
        # 1. Volume Breakout (Purani wali)
        btc_strat_1 = (price > ema_50) and (macd > signal) and (50 < rsi < 68) and (vol > vol_ma * 1.2)
        
        # 2. Trend & Momentum (Market flow pakadne ke liye)
        btc_strat_2 = (price > ema_50) and (ema_50 > ema_200) and (macd > signal) and (45 <= rsi <= 70)
        
        # 3. Dip Recovery (Jab market thoda gir kar wapas uthe)
        btc_strat_3 = (rsi < 40) and (macd > signal) and (price > ema_200)

        if btc_strat_1: return "BTC Strat 1 (Volume Breakout)"
        elif btc_strat_2: return "BTC Strat 2 (Trend & Momentum)"
        elif btc_strat_3: return "BTC Strat 3 (RSI Dip Recovery)"
    
    return None

def manage_active_trade(symbol, current_price):
    global active_trades
    trade = active_trades[symbol]
    if not trade: return

    target = trade['target']
    
    # Trailing Stop Loss Logic (Same as SOL)
    if current_price > trade['highest_price']:
        trade['highest_price'] = current_price
        new_tsl = current_price * 0.985  # 1.5% Trailing Stop Loss
        if new_tsl > trade['sl']:
            trade['sl'] = new_tsl
            logging.info(f"[{symbol}] TSL updated to: {trade['sl']:.2f}")

    # Stop Loss / Trailing Stop Loss Hit
    if current_price <= trade['sl']:
        logging.info(f"[{symbol}] SL/TSL Hit! Closing trade on exchange...")
        try:
            exchange.create_market_order(symbol, 'sell', trade['quantity'])
            logging.info(f"[{symbol}] Real Exit Order Executed Successfully!")
        except Exception as e:
            logging.error(f"[{symbol}] Exit order error: {e}")
        active_trades[symbol] = None  
        
    # Target Hit
    elif current_price >= target:
        logging.info(f"[{symbol}] Target Hit! Closing trade on exchange...")
        try:
            exchange.create_market_order(symbol, 'sell', trade['quantity'])
            logging.info(f"[{symbol}] Real Target Order Executed Successfully!")
        except Exception as e:
            logging.error(f"[{symbol}] Exit order error: {e}")
        active_trades[symbol] = None  

def run_trading_bot():
    global active_trades
    logging.info("Real-Execution DUAL Bot (SOL + 3 BTC Strats) Started...")
    
    symbols = ['SOLUSDT', 'BTCUSDT']

    while True:
        try:
            for symbol in symbols:
                data = fetch_market_data(symbol)
                if not data: continue
                    
                price, rsi = data['price'], data['rsi']
                logging.info(f"SCAN {symbol} - Price: {price:.2f} | RSI: {rsi:.2f} | Active Trade: {active_trades[symbol] is not None}")

                if active_trades[symbol] is not None:
                    manage_active_trade(symbol, price)
                else:
                    matched_strategy = check_strategies(symbol, data)
                    
                    if matched_strategy:
                        qty = QUANTITIES[symbol]
                        logging.info(f"SIGNAL MATCHED via {matched_strategy}! Placing REAL Buy Order...")
                        
                        try:
                            order = exchange.create_market_order(symbol, 'buy', qty)
                            logging.info(f"REAL ORDER PLACED SUCCESSFULLY: {order}")
                            
                            active_trades[symbol] = {
                                'strategy': matched_strategy,
                                'entry_price': price,
                                'quantity': qty,
                                'sl': price * 0.985,      # 1.5% Stop Loss
                                'target': price * 1.03,   # 3% Target
                                'highest_price': price
                            }
                        except Exception as order_error:
                            logging.error(f"Real Order Execution Failed for {symbol}: {order_error}")

            time.sleep(30) # Scan delay
        except Exception as e:
            logging.error(f"Bot loop error: {e}")
            time.sleep(10)

app = Flask(__name__)
@app.route('/')
def keep_alive():
    return "Real Execution DUAL Bot (With Upgraded BTC Strats) is Live!"

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_trading_bot)
    bot_thread.daemon = True
    bot_thread.start()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
