def get_market_intelligence(self):
        try:
            # Sirf 2 line ka debug print add kiya hai
            depth_res = requests.get(f"{BASE_URL}{DEPTH_ENDPOINT}?symbol={SYMBOL}&limit=5", timeout=5)
            print(f"[{time.strftime('%I:%M:%S %p')}] DEBUG DEPTH API RESPONSE: {depth_res.text}", flush=True)
            
            res_json = depth_res.json()
            bids, asks = [], []
            if isinstance(res_json, dict) and res_json.get("code", 0) == 0:
                depth_data = res_json.get('data', res_json)
                bids = depth_data.get('bids', [])
                asks = depth_data.get('asks', [])
            
            bid_vol = sum([float(b[1]) for b in bids]) if bids else 10.0
            ask_vol = sum([float(a[1]) for a in asks]) if asks else 10.0
            
            kline_res = requests.get(f"{BASE_URL}{KLINE_ENDPOINT}?symbol={SYMBOL}&interval=1m&limit=5", timeout=5)
            print(f"[{time.strftime('%I:%M:%S %p')}] DEBUG KLINE API RESPONSE: {kline_res.text}", flush=True)

            k_json = kline_res.json()
            klines = []
            if isinstance(k_json, dict) and k_json.get("code", 0) == 0:
                klines = k_json.get('data', [])
            elif isinstance(k_json, list):
                klines = k_json
            
            if klines and len(klines) > 0:
                current_price = float(klines[-1][4])
                current_vol = float(klines[-1][5])
                avg_vol = sum([float(k[5]) for k in klines[:-1]]) / max(len(klines[:-1]), 1)
            else:
                current_price = 81000.0
                current_vol, avg_vol = 1.0, 1.0

            return current_price, bid_vol, ask_vol, avg_vol, current_vol

        except Exception as e:
            print(f"[{time.strftime('%I:%M:%S %p')}] API Error: {str(e)}", flush=True)
            return 81000.0, 10.0, 10.0, 1.0, 1.0
