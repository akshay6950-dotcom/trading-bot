import time
import logging
import threading
import os
import urllib.request
from flask import Flask
import ccxt
import pandas as pd
import pandas_ta as ta

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - INFO - %(message)s')

# Active trades tracker - tracks both long and short
active_trades = {
    'SOLUSDT': None,
    'BTCUSDT': None
}

# Fixed Quantities (BTC is set to 35 contracts = 0.035 BTC)
QUANTITIES = {
    'SOLUSDT': 25,     
    'BTCUSDT': 35     
}

# --- API KEYS (Directly Updated & Locked with IP 74.220.48.219) ---
API_KEY = '0ba307c551a7b66600a0d8a7a5586c20' 
API_SECRET = '09abb3d1bf0ad3f6fe453474a220acd2'

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
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=250)
        if not bars or len(bars) == 0:
            return None

        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df.ta.ema(length=50, append=True)
        df.ta.ema(length=200, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.rsi(length=14, append=True)
        df['vol_ma'] = df['volume'].rolling(window=20).mean()

        latest = df.iloc[-1]
        
        return {
            'price': float(latest['close']),
            'ema_50': float(latest['EMA_50']),
            'ema_200': float(latest['EMA_200']),
            'macd': float(latest['MACD_12_26_9']),
            'signal': float(latest['MACDs_12_26_9']),
            'rsi': float(latest['RSI_14']),
            'vol': float(latest['volume']),
            'vol_ma': float(latest['vol_ma'])
        }
    except Exception as e:
        logging.error(f"Data fetch error for {symbol}: {e}")
        return None

def check_strategies(symbol, data):
    price, ema_50, ema_200 = data['price'], data['ema_50'], data['ema_200']
    macd, signal, rsi = data['macd'], data['signal'], data['rsi']
    vol, vol_ma = data['vol'], data['vol_ma']

    # ================= LONG STRATEGIES (BUY) =================
    if symbol == 'SOLUSDT':
        long_1 = (price > ema_50) and (ema_50 > ema_200) and (macd > signal) and (45 <= rsi <= 70)
        long_2 = (rsi < 40) and (macd > signal) and (price > ema_200)
        long_3 = (macd > signal) and (50 <= rsi <= 75) and (price > ema_50)
        
        if long_1: return "SOL Long 1", 'buy'
        elif long_2: return "SOL Long 2", 'buy'
        elif long_3: return "SOL Long 3", 'buy'
        
    elif symbol == 'BTCUSDT':
        long_1 = (price > ema_50) and (macd > signal) and (50 < rsi < 68) and (vol > vol_ma * 1.2)
        long_2 = (price > ema_50) and (ema_50 > ema_200) and (macd > signal) and (45 <= rsi <= 70)
        long_3 = (rsi < 40) and (macd > signal) and (price > ema_200)
        
        if long_1: return "BTC Long 1", 'buy'
        elif long_2: return "BTC Long 2", 'buy'
        elif long_3: return "BTC Long 3", 'buy'

    # ================= SHORT STRATEGIES (SELL) =================
    if symbol == 'SOLUSDT':
        short_1 = (price < ema_50) and (ema_50 < ema_200) and (macd < signal) and (30 <= rsi <= 55)
        short_2 = (rsi > 60) and (macd < signal) and (price < ema_200)
        short_3 = (macd < signal) and (25 <= rsi <= 50) and (price < ema_50)
        
        if short_1: return "SOL Short 1", 'sell'
        elif short_2: return "SOL Short 2", 'sell'
        elif short_3: return "SOL Short 3", 'sell'
        
    elif symbol == 'BTCUSDT':
        short_1 = (price < ema_50) and (macd < signal) and (32 < rsi < 50) and (vol > vol_ma * 1.2)
        short_2 = (price < ema_50) and (ema_50 < ema_200) and (macd < signal) and (30 <= rsi <= 55)
        short_3 = (rsi > 60) and (macd < signal) and (price < ema_200)
        
        if short_1: return "BTC Short 1", 'sell'
        elif short_2: return "BTC Short 2", 'sell'
        elif short_3: return "BTC Short 3", 'sell'

    return None, None

def manage_active_trade(symbol, current_price):
    global active_trades
    trade = active_trades[symbol]
    if not trade: return

    side = trade['side']
    qty = trade['quantity']
    
    if side == 'buy': # LONG TRADE LOGIC
        if current_price > trade['extreme_price']:
            trade['extreme_price'] = current_price
            new_tsl = current_price * 0.985
            if new_tsl > trade['sl']:
                trade['sl'] = new_tsl
                logging.info(f"[{symbol} LONG] TSL updated to: {trade['sl']:.2f}")

        if current_price <= trade['sl']:
            logging.info(f"[{symbol}] LONG SL/TSL Hit! Closing trade...")
            try:
                exchange.create_market_order(symbol, 'sell', qty)
                active_trades[symbol] = None
            except Exception as e: logging.error(f"Exit error: {e}")
            
        elif current_price >= trade['target']:
            logging.info(f"[{symbol}] LONG Target Hit! Closing trade...")
            try:
                exchange.create_market_order(symbol, 'sell', qty)
                active_trades[symbol] = None
            except Exception as e: logging.error(f"Exit error: {e}")

    elif side == 'sell': # SHORT TRADE LOGIC
        if current_price < trade['extreme_price']:
            trade['extreme_price'] = current_price
            new_tsl = current_price * 1.015 
            if new_tsl < trade['sl']:
                trade['sl'] = new_tsl
                logging.info(f"[{symbol} SHORT] TSL updated to: {trade['sl']:.2f}")

        if current_price >= trade['sl']:
            logging.info(f"[{symbol}] SHORT SL/TSL Hit! Closing trade...")
            try:
                exchange.create_market_order(symbol, 'buy', qty) 
                active_trades[symbol] = None
            except Exception as e: logging.error(f"Exit error: {e}")
            
        elif current_price <= trade['target']:
            logging.info(f"[{symbol}] SHORT Target Hit! Closing trade...")
            try:
                exchange.create_market_order(symbol, 'buy', qty)
                active_trades[symbol] = None
            except Exception as e: logging.error(f"Exit error: {e}")

def run_trading_bot():
    global active_trades
    logging.info("Real-Execution LONG+SHORT DUAL Bot Started...")
    
    symbols = ['SOLUSDT', 'BTCUSDT']

    while True:
        try:
            for symbol in symbols:
                data = fetch_market_data(symbol)
                if not data: continue
                    
                price, rsi = data['price'], data['rsi']
                status = f"Active: {active_trades[symbol]['side'].upper()}" if active_trades[symbol] else "Active: None"
                logging.info(f"SCAN {symbol} - Price: {price:.2f} | RSI: {rsi:.2f} | {status}")

                if active_trades[symbol] is not None:
                    manage_active_trade(symbol, price)
                else:
                    strategy_name, trade_side = check_strategies(symbol, data)
                    
                    if strategy_name and trade_side:
                        qty = QUANTITIES[symbol]
                        logging.info(f"SIGNAL: {strategy_name}! Placing REAL {trade_side.upper()} Order...")
                        
                        try:
                            exchange.create_market_order(symbol, trade_side, qty)
                            
                            if trade_side == 'buy':
                                sl = price * 0.985
                                target = price * 1.03
                            else:
                                sl = price * 1.015
                                target = price * 0.97
                                
                            active_trades[symbol] = {
                                'side': trade_side,
                                'strategy': strategy_name,
                                'entry_price': price,
                                'quantity': qty,
                                'sl': sl,      
                                'target': target,   
                                'extreme_price': price 
                            }
                            logging.info(f"REAL ORDER PLACED SUCCESSFULLY!")
                        except Exception as order_error:
                            logging.error(f"Real Order Failed for {symbol}: {order_error}")

            time.sleep(30)
        except Exception as e:
            logging.error(f"Bot loop error: {e}")
            time.sleep(10)

app = Flask(__name__)
@app.route('/')
def keep_alive():
    try:
        ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
        return f"""
        <div style='text-align:center; margin-top:50px; font-family:Arial;'>
            <h2>Aapka Render Server IP hai:</h2>
            <h1 style='color:blue; background:#f0f0f0; display:inline-block; padding:10px; border-radius:5px;'>{ip}</h1>
            <p>Isko copy karein aur Shark Exchange mein 'Add IP' wale box mein paste karein.</p>
        </div>
        """
    except Exception as e:
        return f"Real Execution DUAL Bot is Live! IP Error: {e}"

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_trading_bot)
    bot_thread.daemon = True
    bot_thread.start()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
