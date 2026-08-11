import hashlib
import hmac
import json
import os
import threading
import time
from urllib.parse import urlencode
from flask import Flask
import pandas as pd
import pandas_ta as ta
import requests
import yfinance as yf

# =====================================================================
# SHARK EXCHANGE FREE WEB SERVICE BTC BOT (FLASK + BACKGROUND THREAD)
# =====================================================================

app = Flask(__name__)

BASE_URL = 'https://api.sharkexchange.in'
MARGIN_ASSET = 'INR'  # CRITICAL: Prevents Error 3029
DEVICE_TYPE = 'WEB'
USER_CATEGORY = 'EXTERNAL'

API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'

SYMBOL_YAHOO = 'BTC-USD'
SYMBOL_EXCHANGE = 'BTC_INR'
BTC_QUANTITY = 0.050
LEVERAGE = 5
TRAILING_DISTANCE = 0.008  # 0.8% dynamic trailing stop-loss buffer


class SharkLiveBTCBot:

  def __init__(self):
    self.position = 0  # 0 = Flat, 1 = Long, -1 = Short
    self.entry_price = 0.0
    self.current_sl = 0.0
    self.current_tp = 0.0
    self.extreme_price = 0.0

  def generate_signature(self, params: dict) -> str:
    sorted_params = sorted(params.items())
    query_string = urlencode(sorted_params)
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return signature

  def get_headers(self, params: dict) -> dict:
    signature = self.generate_signature(params)
    return {
        'Content-Type': 'application/json',
        'deviceType': DEVICE_TYPE,
        'userCategory': USER_CATEGORY,
        'X-API-KEY': API_KEY,
        'X-SIGNATURE': signature,
    }

  def place_order(self, side: str):
    endpoint = f'{BASE_URL}/api/v1/order'
    payload = {
        'symbol': SYMBOL_EXCHANGE,
        'side': side,
        'type': 'MARKET',
        'quantity': BTC_QUANTITY,
        'leverage': LEVERAGE,
        'marginAsset': MARGIN_ASSET,
        'timestamp': int(time.time() * 1000),
    }

    headers = self.get_headers(payload)

    try:
      response = requests.post(
          endpoint, headers=headers, data=json.dumps(payload), timeout=10
      )
      result = response.json()
      print(f'🟢 LIVE ORDER EXECUTED [{SYMBOL_EXCHANGE}] | Side: {side}')
      print(f'   Response: {result}')
      return True
    except Exception as e:
      print(f'[API ERROR] Order execution failed: {e}')
      return False

  def fetch_data(self):
    df = yf.download(SYMBOL_YAHOO, period='7d', interval='1h', progress=False)
    if isinstance(df.columns, pd.MultiIndex):
      df.columns = [col[0] for col in df.columns]
    df.dropna(subset=['Close'], inplace=True)

    df.ta.ema(length=21, append=True)
    df.ta.ema(length=50, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.adx(length=14, append=True)
    bb = df.ta.bbands(length=20, std=2)
    df = pd.concat([df, bb], axis=1)
    df.dropna(inplace=True)
    df.columns = [c.upper() for c in df.columns]
    return df

  def get_adaptive_signals(self):
    df = self.fetch_data()
    row = df.iloc[-1]

    price = row['CLOSE']
    adx_val = row['ADX_14']
    rsi_val = row['RSI']

    e21 = row[[c for c in df.columns if 'EMA_21' in c][0]]
    e50 = row[[c for c in df.columns if 'EMA_50' in c][0]]
    bbl = row[[c for c in df.columns if 'BBL_20' in c][0]]
    bbu = row[[c for c in df.columns if 'BBU_20' in c][0]]

    is_long = False
    is_short = False
    mode = 'BUFFER_ZONE'
    sl_pct = 0.010
    tp_pct = 0.018

    if adx_val > 28:
      mode = 'TREND_MODE'
      is_long = (e21 > e50) and (price <= e21) and (rsi_val < 45)
      is_short = (e21 < e50) and (price >= e21) and (rsi_val > 55)
      sl_pct, tp_pct = 0.010, 0.018
    elif adx_val < 20:
      mode = 'SIDEWAYS_MODE'
      is_long = (price <= bbl) and (rsi_val < 33)
      is_short = (price >= bbu) and (rsi_val > 67)
      sl_pct, tp_pct = 0.012, 0.018

    return is_long, is_short, price, mode, sl_pct, tp_pct

  def run(self):
    print('=' * 78)
    print(
        '   SHARK EXCHANGE FREE BOT ACTIVE | Symbol: {SYMBOL_EXCHANGE} | Qty:'
        f' {BTC_QUANTITY}'
    )
    print('=' * 78)

    while True:
      try:
        is_long, is_short, current_price, mode, sl_pct, tp_pct = (
            self.get_adaptive_signals()
        )

        if self.position == 1:
          if current_price > self.extreme_price:
            self.extreme_price = current_price
            new_trail = self.extreme_price * (1 - TRAILING_DISTANCE)
            if new_trail > self.current_sl:
              self.current_sl = new_trail
          if current_price <= self.current_sl or current_price >= self.current_tp:
            self.place_order('SELL')
            self.position = 0

        elif self.position == -1:
          if current_price < self.extreme_price:
            self.extreme_price = current_price
            new_trail = self.extreme_price * (1 + TRAILING_DISTANCE)
            if new_trail < self.current_sl:
              self.current_sl = new_trail
          if current_price >= self.current_sl or current_price <= self.current_tp:
            self.place_order('BUY')
            self.position = 0

        elif self.position == 0:
          if is_long:
            if self.place_order('BUY'):
              self.position = 1
              self.entry_price = current_price
              self.extreme_price = current_price
              self.current_sl = current_price * (1 - sl_pct)
              self.current_tp = current_price * (1 + tp_pct)
          elif is_short:
            if self.place_order('SELL'):
              self.position = -1
              self.entry_price = current_price
              self.extreme_price = current_price
              self.current_sl = current_price * (1 + sl_pct)
              self.current_tp = current_price * (1 - tp_pct)

        time.sleep(60)
      except Exception as e:
        print(f'[ERROR]: {e}')
        time.sleep(30)


@app.route('/')
def home():
  return 'BTC Trading Bot is running live and free!'


def start_bot_thread():
  bot = SharkLiveBTCBot()
  bot.run()


if __name__ == '__main__':
  # Run trading bot in background thread
  bot_thread = threading.Thread(target=start_bot_thread)
  bot_thread.daemon = True
  bot_thread.start()

  # Run Flask to satisfy Render Web Service port requirement
  port = int(os.environ.get('PORT', 10000))
  app.run(host='0.0.0.0', port=port)
