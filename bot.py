import hashlib
import hmac
import json
import time
from urllib.parse import urlencode
import pandas as pd
import pandas_ta as ta
import requests
import yfinance as yf

# =====================================================================
# SHARK EXCHANGE LIVE ADAPTIVE BTC BOT (PRODUCTION READY)
# =====================================================================

# API SETTINGS
BASE_URL = 'https://api.sharkexchange.in'
MARGIN_ASSET = 'INR'  # CRITICAL: Prevents Error 3029
DEVICE_TYPE = 'WEB'
USER_CATEGORY = 'EXTERNAL'

API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'

# BOT & RISK PARAMETERS (Strictly BTC Only, 1 Trade at a Time)
SYMBOL_YAHOO = 'BTC-USD'
SYMBOL_EXCHANGE = 'BTC_INR'
BTC_QUANTITY = 0.050
LEVERAGE = 5
TRAILING_DISTANCE = 0.008  # 0.8% dynamic trailing stop-loss buffer


class SharkLiveBTCBot:

  def __init__(self):
    self.position = 0  # 0 = Flat (No Trade), 1 = Long, -1 = Short
    self.entry_price = 0.0
    self.current_sl = 0.0
    self.current_tp = 0.0
    self.extreme_price = 0.0

  def generate_signature(self, params: dict) -> str:
    """Generates hmac_sha256 signature with alphabetically sorted payload parameters."""
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
    """Executes live market order on Shark Exchange."""
    endpoint = f'{BASE_URL}/api/v1/order'
    payload = {
        'symbol': SYMBOL_EXCHANGE,
        'side': side,  # 'BUY' or 'SELL'
        'type': 'MARKET',
        'quantity': BTC_QUANTITY,
        'leverage': LEVERAGE,
        'marginAsset': MARGIN_ASSET,  # 'INR' to avoid Error 3029
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

    # Adaptive Indicators: EMA 21/50, RSI 14, ADX 14, Bollinger Bands (20,2)
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

    # Market Regime Switcher
    if adx_val > 28:
      # TREND MODE: EMA 21/50 Crossover + Pullback
      mode = 'TREND_MODE'
      is_long = (e21 > e50) and (price <= e21) and (rsi_val < 45)
      is_short = (e21 < e50) and (price >= e21) and (rsi_val > 55)
      sl_pct, tp_pct = 0.010, 0.018

    elif adx_val < 20:
      # SIDEWAYS / CHOP MODE: Bollinger Bands Mean-Reversion
      mode = 'SIDEWAYS_MODE'
      is_long = (price <= bbl) and (rsi_val < 33)
      is_short = (price >= bbu) and (rsi_val > 67)
      sl_pct, tp_pct = 0.012, 0.018

    else:
      # BUFFER ZONE (20 <= ADX <= 28): No trade, avoid whipsaws
      mode = 'BUFFER_ZONE'

    return is_long, is_short, price, mode, sl_pct, tp_pct

  def run(self):
    print('=' * 78)
    print(
        f'   SHARK EXCHANGE LIVE BTC BOT ACTIVE | Symbol: {SYMBOL_EXCHANGE} |'
        f' Qty: {BTC_QUANTITY} BTC'
    )
    print(
        '   Rules: 1 Trade at a Time | 5x Leverage | INR Margin | Adaptive'
        ' Regime Strategy'
    )
    print('=' * 78)

    while True:
      try:
        is_long, is_short, current_price, mode, sl_pct, tp_pct = (
            self.get_adaptive_signals()
        )

        # --- 1. MANAGE ACTIVE POSITION & TRAILING SL ---
        if self.position == 1:  # ACTIVE LONG
          if current_price > self.extreme_price:
            self.extreme_price = current_price
            new_trail = self.extreme_price * (1 - TRAILING_DISTANCE)
            if new_trail > self.current_sl:
              self.current_sl = new_trail
              print(
                  f'[UPDATE] Long Trailing SL locked higher at:'
                  f' {self.current_sl:.2f}'
              )

          if current_price <= self.current_sl:
            print(
                f'🔴 STOP LOSS / TRAILING HIT (LONG) | Closing position at'
                f' {current_price}'
            )
            self.place_order('SELL')  # Exit Long via Sell order
            self.position = 0
          elif current_price >= self.current_tp:
            print(
                f'🟢 TAKE PROFIT HIT (LONG) | Closing position at'
                f' {current_price}'
            )
            self.place_order('SELL')
            self.position = 0

        elif self.position == -1:  # ACTIVE SHORT
          if current_price < self.extreme_price:
            self.extreme_price = current_price
            new_trail = self.extreme_price * (1 + TRAILING_DISTANCE)
            if new_trail < self.current_sl:
              self.current_sl = new_trail
              print(
                  f'[UPDATE] Short Trailing SL locked lower at:'
                  f' {self.current_sl:.2f}'
              )

          if current_price >= self.current_sl:
            print(
                f'🔴 STOP LOSS / TRAILING HIT (SHORT) | Closing position at'
                f' {current_price}'
            )
            self.place_order('BUY')  # Exit Short via Buy order
            self.position = 0
          elif current_price <= self.current_tp:
            print(
                f'🟢 TAKE PROFIT HIT (SHORT) | Closing position at'
                f' {current_price}'
            )
            self.place_order('BUY')
            self.position = 0

        # --- 2. LOOK FOR NEW ENTRY (ONLY IF FLAT: position == 0) ---
        elif self.position == 0:
          if mode == 'BUFFER_ZONE':
            print(
                '[STATUS] ADX in Buffer Zone (20-28). Staying flat in cash.'
            )
          elif is_long:
            if self.place_order('BUY'):
              self.position = 1
              self.entry_price = current_price
              self.extreme_price = current_price
              self.current_sl = current_price * (1 - sl_pct)
              self.current_tp = current_price * (1 + tp_pct)
              print(
                  f'🟢 OPEN LONG [{mode}] | Price: {self.entry_price:.2f} | SL:'
                  f' {self.current_sl:.2f} | TP: {self.current_tp:.2f}'
              )
          elif is_short:
            if self.place_order('SELL'):
              self.position = -1
              self.entry_price = current_price
              self.extreme_price = current_price
              self.current_sl = current_price * (1 + sl_pct)
              self.current_tp = current_price * (1 - tp_pct)
              print(
                  f'🔴 OPEN SHORT [{mode}] | Price: {self.entry_price:.2f} | SL:'
                  f' {self.current_sl:.2f} | TP: {self.current_tp:.2f}'
              )

        time.sleep(60)

      except Exception as e:
        print(f'[ERROR] Loop exception: {e}')
        time.sleep(30)


if __name__ == '__main__':
  bot = SharkLiveBTCBot()
  bot.run()
