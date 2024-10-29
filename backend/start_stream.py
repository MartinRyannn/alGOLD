import pandas as pd
from flask import Flask, jsonify
from flask_cors import CORS
import threading
import io
import time
from datetime import datetime, timedelta
import os
import subprocess
import sys
import tpqoa
import math
import oandapyV20
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.accounts as accounts
# from scraper import fetch_events
from get_history import main as get_history_main
from get_trades import get_active_trades
import requests
import numpy as np
from datetime import datetime
import configparser

# upcoming_events = []
history_data = []

app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

def load_config():
    """Function to load OANDA credentials from config file"""
    config = configparser.ConfigParser()
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "oanda.cfg")
    config.read(config_file)
    
    return {
        "account_id": config['oanda']['account_id'],
        "access_token": config['oanda']['access_token']
    }

credentials = load_config()

api = tpqoa.tpqoa("oanda.cfg")
accountID = credentials['account_id']
client = oandapyV20.API(access_token=credentials['access_token'])
balance_data = {'balance': 0.0}

balance_data = {'balance': 0.0}



local_csv_file = 'live_price_data.csv'
csv_url_candles = "http://13.60.228.39:8000/resampled_data.csv"
csv_url_live_price = "http://16.170.247.104:8000/resampled_data.csv"

data_cache = []
live_price_cache = None

volatility_threshold = 0.1


trading_app_running = False
history_app_running = False

time_weighted_vwap = 0.0
time_weighted_sum = 0.0
last_timestamp = None

breakout_period = 100
last_signal = None
breakout_high, breakout_low = None, None 

lag_period = 40
price_update_count = 0

cooldown_counter = 0

active_order = None
stop_loss_price = None
take_profit_price = None

cooldown_period = 250 
last_trade_time = None

tvwap_window = 300
tvwap_prices = []
tvwap_times = []

last_csv_update_time = None

def calculate_moving_average(data, window=50):
    return data['close'].rolling(window=window).mean().iloc[-1]



def fetch_open_trades():
    """Fetch open trades using the OANDA API."""
    try:
        r = trades.OpenTrades(accountID=accountID)
        client.request(r)
        open_trades = r.response.get('trades', [])
        return open_trades
    except Exception as e:
        print(f"Error fetching open trades: {e}")
        return [] 
    
def fetch_balance():
    """Function to fetch balance every 10 seconds and update the balance_data."""
    global balance_data
    while True:
        try:
            r = accounts.AccountDetails(accountID)
            client.request(r)
            balance_data['balance'] = round(float(r.response['account']['balance']), 2) 
            balance_data['unrealizedPL'] = round(float(r.response['account']['unrealizedPL']), 2)
            balance_data['pl'] = round(float(r.response['account']['pl']), 2)
            print(f"Updated Balance: {balance_data['balance']}, Unrealized PL: {balance_data['unrealizedPL']}, PL: {balance_data['pl']}")
        except Exception as e:
            print(f"Error fetching balance: {e}")
        time.sleep(10)



current_volatility = None

def calculate_volatility(data, period=75):
    """Calculate volatility using standard deviation of price changes over the last 'period' candles."""
    if len(data) < period:
        return None

    recent_closes = data['close'].iloc[-period:]
    pct_changes = recent_closes.pct_change().dropna()
    volatility = np.std(pct_changes)
    
    return volatility

def update_volatility_from_live_price():
    """Updates the volatility based on live price data fetched every 3 seconds."""
    global current_volatility

    if len(tvwap_prices) < 20:
        current_volatility = None
        return

    returns = [(tvwap_prices[i] - tvwap_prices[i-1]) / tvwap_prices[i-1] for i in range(1, len(tvwap_prices[-10:]))]

    print(f"Live Prices: {tvwap_prices[-20:]}")
    print(f"Calculated Returns from Live Prices: {returns[-20:]}")

    current_volatility = np.std(returns)

    print(f"Updated Volatility (Live Data, Scaled): {round(current_volatility, 4) * 10000}")





def calculate_atr(data, period=14):
    data['high_low'] = data['high'] - data['low']
    data['high_close'] = abs(data['high'] - data['close'].shift())
    data['low_close'] = abs(data['low'] - data['close'].shift())
    tr = data[['high_low', 'high_close', 'low_close']].max(axis=1)
    atr = tr.rolling(period).mean().iloc[-1]
    return atr


# def background_event_scraper():
#     global upcoming_events
#     while True:
#         upcoming_events = fetch_events()
#         time.sleep(300)

# event_scraper_thread = threading.Thread(target=background_event_scraper)
# event_scraper_thread.daemon = True
# event_scraper_thread.start()

def run_get_history():
    """Run the get_history main function every 20 seconds."""
    global history_data
    while True:
        try:
            history_data = get_history_main()
            time.sleep(20)
        except Exception as e:
            print(f"Error in get_history execution: {e}")

get_history_thread = threading.Thread(target=run_get_history)
get_history_thread.daemon = True
get_history_thread.start()


def send_notification(title, message):
    """Sends a dialog notification using AppleScript."""
    script = f'display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK"'
    subprocess.run(["osascript", "-e", script])

def calculate_rsi(data, period=14):
    """Calculates the RSI (Relative Strength Index)"""
    if 'Close' not in data.columns or len(data) < period:
        return None

    deltas = pd.Series(data['Close']).diff()
    gain = deltas.where(deltas > 0, 0).rolling(window=period).mean()
    loss = -deltas.where(deltas < 0, 0).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1] if not rsi.isna().all() else None

def generate_signal_with_rsi_ma(current_price, breakout_high, breakout_low, data):
    rsi = calculate_rsi(data)
    short_ma = calculate_moving_average(data, window=50)
    long_ma = calculate_moving_average(data, window=200)

    if short_ma > long_ma and rsi < 70 and current_price > breakout_high:
        return 'buy', True
    elif short_ma < long_ma and rsi > 30 and current_price < breakout_low:
        return 'sell', True
    return None, False

def calculate_breakout(data):
    """Calculates breakout levels based on the last 'breakout_period' periods."""
    if len(data) < breakout_period:
        return None, None

    high = data['close'].rolling(window=breakout_period).max().iloc[-1]
    low = data['close'].rolling(window=breakout_period).min().iloc[-1]

    return high, low

def test_api_connection():
    try:
        account_details = api.get_account_summary()
        print(f"API Connection Test - Account Details: {account_details}")
        return True
    except Exception as e:
        print(f"API Connection Test Failed: {str(e)}")
        return False

def generate_signal(current_price, breakout_high, breakout_low):
    global last_signal, active_order

    open_trades = fetch_open_trades()

    if open_trades:
        print("Active trade detected. Suppressing signal generation.")
        return None, False

    if current_price > breakout_high and last_signal != 'buy': 
        last_signal = 'buy'
        return 'buy', True
    elif current_price < breakout_low and last_signal != 'sell': 
        last_signal = 'sell'
        return 'sell', True

    if breakout_low < current_price < breakout_high:
        last_signal = None

    return None, False

def calculate_typical_price(row):
    """Calculates the typical price (TP) for a given row of OHLC data"""
    return (row['open'] + row['high'] + row['low'] + row['close']) / 4

def calculate_time_vwap(new_data):
    """Updates the time-weighted VWAP using the new data"""
    global time_weighted_vwap, time_weighted_sum, last_timestamp
    
    row = new_data.iloc[-1]
    
    timestamp = pd.to_datetime(row['timestamp'])
    typical_price = calculate_typical_price(row)
    
    if last_timestamp is None:
        last_timestamp = timestamp
        return time_weighted_vwap 

    time_interval = (timestamp - last_timestamp).total_seconds()
    
    time_weighted_sum += typical_price * time_interval
    total_time = (timestamp - pd.to_datetime(new_data.iloc[0]['timestamp'])).total_seconds()
    
    time_weighted_vwap = time_weighted_sum / total_time if total_time > 0 else time_weighted_vwap
    
    last_timestamp = timestamp
    
    return time_weighted_vwap

def calculate_t_vwap():
    global tvwap_prices, tvwap_times

    if len(tvwap_prices) < 2:
        return 0.0

    time_diffs = [tvwap_times[i+1] - tvwap_times[i] for i in range(len(tvwap_times) - 1)]
    
    total_time = sum([td.total_seconds() for td in time_diffs])
    # If the total time is zero (guard against division by zero)
    if total_time == 0:
        return 0.0

    # Weighted price sum
    weighted_price_sum = sum([tvwap_prices[i] * time_diffs[i].total_seconds() for i in range(len(time_diffs))])

    # Calculate the time-weighted VWAP
    t_vwap = weighted_price_sum / total_time

    return t_vwap

last_written_data = None  # Store last written data to avoid duplicates

def can_write_csv(current_time):
    """Check if enough time has passed to allow a CSV write."""
    global last_csv_update_time
    if last_csv_update_time is None or (current_time - last_csv_update_time >= 5):
        last_csv_update_time = current_time  # Update time
        return True
    return False

def fetch_live_price():
    """Fetches live price and writes to CSV every 3 seconds."""
    global last_written_data
    try:
        response = requests.get(csv_url_live_price)
        if response.status_code == 200:
            new_data = pd.read_csv(io.StringIO(response.text))
            if 'close' in new_data.columns:
                live_price_cache = new_data['close'].iloc[-1]
                timestamp = pd.to_datetime(new_data['timestamp'].iloc[-1])
                t_vwap = calculate_t_vwap()

                current_data = {
                    'timestamp': timestamp,
                    'open': new_data['open'].iloc[-1],
                    'high': new_data['high'].iloc[-1],
                    'low': new_data['low'].iloc[-1],
                    'close': live_price_cache,
                    't_vwap': t_vwap
                }

                current_time = time.time()
                if can_write_csv(current_time):
                    if last_written_data != current_data:  # Avoid duplicates
                        write_to_csv(timestamp, new_data, live_price_cache, t_vwap)
                        last_written_data = current_data  # Update last written data
                    else:
                        print("Duplicate data detected. Skipping write.")
                else:
                    print("Time limit not reached. Skipping write.")

    except Exception as e:
        print(f"Error fetching live price data: {e}")
csv_lock = threading.Lock()

def write_to_csv(timestamp, new_data, live_price_cache, t_vwap):
    """Writes the data to the CSV file, ensuring no duplicate entries and thread safety."""
    row_data = pd.DataFrame({
        'timestamp': [timestamp],
        'open': [new_data['open'].iloc[-1]],
        'high': [new_data['high'].iloc[-1]],
        'low': [new_data['low'].iloc[-1]],
        'close': [live_price_cache],
        't_vwap': [t_vwap]
    })

    with csv_lock:
        if os.path.exists(local_csv_file):
            last_row = pd.read_csv(local_csv_file).tail(1)
            if not last_row.empty and last_row['timestamp'].iloc[-1] == timestamp:
                print(f"Duplicate entry detected for timestamp: {timestamp}. Skipping write.")
                return

        mode = 'a' if os.path.exists(local_csv_file) else 'w'

        row_data.to_csv(local_csv_file, mode=mode, header=(mode == 'w'), index=False)
        print(f"CSV updated: {timestamp}, Price: {live_price_cache}, T-VWAP: {t_vwap}")




def check_signals(current_price, t_vwap):
    global breakout_high, breakout_low, price_update_count

    if price_update_count >= lag_period:
        full_data = pd.read_csv(local_csv_file)
        volatility = full_data['close'].std()
        print(f"Volatility (Std Dev): {volatility:.2f}")

        if volatility < volatility_threshold:
            print(f"Volatility too low ({volatility:.2f}), skipping the trade.")
            return

        breakout_high, breakout_low = calculate_breakout(full_data)
        price_update_count = 0

        if breakout_high is not None and breakout_low is not None:
            print(f"Recalculated Breakout Levels - High: {breakout_high}, Low: {breakout_low}")
        else:
            print("Not enough data to recalculate breakout levels.")
    
    if breakout_high is None or breakout_low is None:
        return

    if current_price > t_vwap and current_price > breakout_high:
        signal = 'buy'
    elif current_price < t_vwap and current_price < breakout_low:
        signal = 'sell'
    else:
        signal = None

    if signal:
        print(f"Generated Signal: {signal.upper()} at price {current_price} (T-VWAP: {t_vwap})")
        full_data = pd.read_csv(local_csv_file)
        execute_trade(signal, current_price, full_data)
    else:
        price_update_count += 1

    candles_left = lag_period - price_update_count
    print(f"Candles until next recalculation: {max(candles_left, 0)}")






def fetch_and_update_data():
    """Fetches candle data and updates the data cache and volatility"""
    global data_cache
    try:
        response = requests.get(csv_url_candles)
        if response.status_code == 200:
            new_data = pd.read_csv(io.StringIO(response.text))

            if 'Close' in new_data.columns and 'Time' in new_data.columns:
                rsi_value = calculate_rsi(new_data)

                # Update the data cache
                data_cache = new_data.to_dict(orient='records')
                data_cache[-1]['RSI'] = rsi_value if rsi_value is not None else 'N/A'

        else:
            print(f"Error fetching candles data: {response.status_code}")
    except Exception as e:
        print(f"An error occurred while fetching candles data: {e}")


def fetch_live_price():
    """Fetches the live price data and calculates T-VWAP and volatility."""
    global live_price_cache, price_update_count, cooldown_counter, tvwap_prices, tvwap_times
    try:
        response = requests.get(csv_url_live_price)
        if response.status_code == 200:
            new_data = pd.read_csv(io.StringIO(response.text))

            if 'close' in new_data.columns:
                live_price_cache = new_data['close'].iloc[-1]
                timestamp = pd.to_datetime(new_data['timestamp'].iloc[-1])

                # Append the current price and timestamp to the T-VWAP window data
                tvwap_prices.append(live_price_cache)
                tvwap_times.append(timestamp)

                # Remove old data if we exceed the T-VWAP window
                while (timestamp - tvwap_times[0]).total_seconds() > tvwap_window:
                    tvwap_prices.pop(0)
                    tvwap_times.pop(0)

                # Calculate T-VWAP
                t_vwap = calculate_t_vwap()

                print(f"Live Price: {live_price_cache}, Timestamp: {timestamp}, T-VWAP: {t_vwap:.4f}")

                # Store the price data locally
                row_data = pd.DataFrame({
                    'timestamp': [timestamp],
                    'open': [new_data['open'].iloc[-1]],
                    'high': [new_data['high'].iloc[-1]],
                    'low': [new_data['low'].iloc[-1]],
                    'close': [live_price_cache],
                    't_vwap': [t_vwap]  # Add T-VWAP to the saved data
                })

                mode = 'a' if os.path.exists(local_csv_file) else 'w'
                row_data.to_csv(local_csv_file, mode=mode, header=mode == 'w', index=False)

                price_update_count += 1
                cooldown_counter += 1

                candles_left = lag_period - price_update_count
                print(f"Candles until breakout recalculation: {candles_left}")

                update_volatility_from_live_price()

                check_signals(live_price_cache, t_vwap)

                time.sleep(1)
            else:
                print("Error: 'close' column not found in live price data.")
        else:
            print(f"Error fetching live price data: {response.status_code}")
    except Exception as e:
        print(f"An error occurred while fetching live price data: {e}")




def background_data_fetcher():
    """Thread for continuously fetching candle data and updating volatility"""
    while True:
        fetch_and_update_data()
        time.sleep(1) 


def background_live_price_fetcher():
    """Thread for continuously fetching live price data"""
    while True:
        fetch_live_price()
        time.sleep(3)

def check_live_signals():
    """Thread for continuously checking live price signals and monitoring active orders."""
    while True:
        if live_price_cache is not None:
            monitor_active_order()
        time.sleep(1)

def calculate_pivot_points():
    """Calculates pivot points based on yesterday's candle data"""
    yesterday = datetime.now() - timedelta(1)
    yesterday_str = yesterday.strftime('%Y-%m-%d')

    data = api.get_history(instrument="XAU_USD", start=yesterday_str, end=(yesterday + timedelta(1)).strftime('%Y-%m-%d'), granularity="D", price="B")

    if not data.empty:
        open_price = data["o"].iloc[0]
        high = data["h"].iloc[0]
        low = data["l"].iloc[0]
        close = data["c"].iloc[0]

        pivot_point = (high + low + close) / 3
        s1 = (pivot_point * 2) - high
        s2 = pivot_point - (high - low)
        r1 = (pivot_point * 2) - low
        r2 = pivot_point + (high - low)

        return {
            "pivot_point": round(pivot_point, 2),
            "s1": round(s1, 2),
            "s2": round(s2, 2),
            "r1": round(r1, 2),
            "r2": round(r2, 2)
        }
    else:
        return None

def execute_trade(signal, current_price, data):
    global active_order, last_trade_time

    print(f"Executing {signal.upper()} trade at {current_price}")


    open_trades = fetch_open_trades()

    if open_trades:
        print("Cannot place a new trade. There is already an active trade.")
        return

    if signal == 'buy':
        place_buy_order(current_price, data) 
    elif signal == 'sell':
        place_sell_order(current_price, data)

    last_trade_time = datetime.now()


active_order = None
stop_loss_price = None
take_profit_price = None

def place_buy_order(current_price, data):
    global active_order, stop_loss_price, take_profit_price
    try:
        take_profit_price = math.ceil(current_price + 6)
        sl_distance = 3  # Stop loss distance in pips
        
        print(f"Attempting to place BUY order: Current Price: {current_price}, TP: {take_profit_price}, SL Distance: {sl_distance}")

        # Add error handling and validation
        if not api:
            print("Error: API client is not initialized")
            return

        response = api.create_order(
            instrument="XAU_USD",
            units=1,
            tp_price=take_profit_price,
            sl_distance=sl_distance
        )

        # Add proper response validation
        if response is None:
            print("Error: Received null response from API")
            return

        print(f"Full API Response: {response}")

        if isinstance(response, dict) and 'id' in response:
            print(f"Successfully executed BUY trade at {current_price}, TP at {take_profit_price}, Order ID: {response['id']}")
            active_order = {
                'id': response['id'],
                'type': 'buy',
                'price': current_price,
                'tp_price': take_profit_price,
                'sl_price': current_price - sl_distance
            }
        else:
            print(f"Error: Invalid response format from API: {response}")

    except Exception as e:
        print(f"Error placing buy order: {str(e)}")
        # Print the full traceback for debugging
        import traceback
        print(traceback.format_exc())



def place_sell_order(current_price, data):
    global active_order, stop_loss_price, take_profit_price
    try:
        take_profit_price = math.floor(current_price - 6)
        sl_distance = 3  # Stop loss distance in pips

        print(f"Attempting to place SELL order: Current Price: {current_price}, TP: {take_profit_price}, SL Distance: {sl_distance}")

        if not api:
            print("Error: API client is not initialized")
            return

        response = api.create_order(
            instrument="XAU_USD",
            units=-1,  # Negative for sell
            tp_price=take_profit_price,
            sl_distance=sl_distance,
        )

        if response is None:
            print("Error: Received null response from API")
            return

        print(f"Full API Response: {response}")

        if isinstance(response, dict) and 'id' in response:
            print(f"Successfully executed SELL trade at {current_price}, TP at {take_profit_price}, Order ID: {response['id']}")
            active_order = {
                'id': response['id'],
                'type': 'sell',
                'price': current_price,
                'tp_price': take_profit_price,
                'sl_price': current_price + sl_distance
            }
        else:
            print(f"Error: Invalid response format from API: {response}")

    except Exception as e:
        print(f"Error placing sell order: {str(e)}")
        import traceback
        print(traceback.format_exc())







def monitor_active_order():
    """Monitors the active order and checks if it hits the TP or SL."""
    global active_order, live_price_cache

    if not active_order:
        return

    try:
        if active_order['type'] == 'buy':
            if live_price_cache >= active_order['tp_price']:
                print(f"Take Profit hit for BUY order at {active_order['tp_price']}. Closing trade.")
                close_order() 
            elif live_price_cache <= active_order['sl_price']:
                print(f"Stop Loss hit for BUY order at {active_order['sl_price']}. Closing trade.")
                close_order() 

        elif active_order['type'] == 'sell':
            if live_price_cache <= active_order['tp_price']:
                print(f"Take Profit hit for SELL order at {active_order['tp_price']}. Closing trade.")
                close_order() 
            elif live_price_cache >= active_order['sl_price']:
                print(f"Stop Loss hit for SELL order at {active_order['sl_price']}. Closing trade.")
                close_order() 

    except Exception as e:
        print(f"Error while monitoring active order: {e}")

def close_order():
    """Closes the active order and resets relevant variables."""
    global active_order, cooldown_counter

    try:

        print(f"Closing order ID: {active_order['id']}")
        
    
        active_order = None
        cooldown_counter = 0  
    except Exception as e:
        print(f"Error closing the order: {e}")




@app.route('/start_stream', methods=['GET'])
def start_stream():
    return jsonify({"status": "Stream started"}), 200

@app.route('/get_data', methods=['GET'])
def get_data():
    return jsonify(data_cache)

@app.route('/get_live_price', methods=['GET'])
def get_live_price():
    return jsonify({"live_price": live_price_cache})

@app.route('/get_pivots', methods=['GET'])
def get_pivots():
    pivots = calculate_pivot_points()
    if pivots:
        return jsonify(pivots)
    else:
        return jsonify({"error": "No data found for the specified date."}), 404

@app.route('/get_balance', methods=['GET'])
def get_balance():
    """API route to get the current balance."""
    return jsonify(balance_data)

@app.route('/get_unrealised', methods=['GET'])
def get_unrealised():
    """API route to get the current unrealized profit/loss."""
    return jsonify({'unrealizedPL': balance_data['unrealizedPL']})


@app.route('/get_volatility', methods=['GET'])
def get_volatility():
    """Fetch current volatility and T-VWAP."""
    if current_volatility is not None:
        # Send back last 5 closing prices to verify data changes
        last_5_closes = [record['Close'] for record in data_cache[-5:]]

        # Calculate T-VWAP
        t_vwap = calculate_t_vwap()

        return jsonify({
            "volatility": round(current_volatility * 10000, 4),  # Multiply by 10000
            "t_vwap": round(t_vwap, 4),  # Add T-VWAP to the response
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "recent_closes": last_5_closes  # Add recent close prices for debugging
        })
    else:
        return jsonify({"error": "Volatility not calculated yet."}), 400






    
@app.route('/get_profit', methods=['GET'])
def get_profit():
    """API route to get the current profit/loss."""
    return jsonify({'pl': balance_data['pl']})

# @app.route('/get_events', methods=['GET'])
# def get_upcoming_events():
#     """API route to get upcoming events."""
#     return jsonify(upcoming_events)



@app.route('/get_history', methods=['GET'])
def get_history():
    """API route to execute the get_history main function and return its result."""
    try:
        return jsonify({"status": "Success", "data": history_data}), 200
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500
    
@app.route('/get_active_trades', methods=['GET'])
def get_active_trades_route():
    """API route to fetch active trades data."""
    try:
        active_trades = get_active_trades()
        return jsonify({"data": active_trades, "status": "Success"})
    except Exception as e:
        return jsonify({"data": None, "status": f"Error: {e}"})
    
import sys

@app.route('/launch-trading-app', methods=['POST'])
def launch_trading_app():
    global trading_app_running
    try:
        if trading_app_running:
            return jsonify({"error": "Trading app is already running."}), 400
        
        # Use sys.executable to get the current Python interpreter
        subprocess.Popen([sys.executable, "start.py"])
        trading_app_running = True
        return jsonify({"message": "Trading app launched successfully!"}), 200
    except Exception as e:
        print(f"Error launching trading app: {e}")  # Log the error
        return jsonify({"error": str(e)}), 500
    

@app.route('/trading-app-closed', methods=['POST'])
def trading_app_closed():
    global trading_app_running
    trading_app_running = False
    return jsonify({"message": "Trading app status updated."}), 200

@app.route('/launch-history-app', methods=['POST'])
def launch_history_app():
    global history_app_running
    try:
        if history_app_running:
            return jsonify({"error": "History app is already running."}), 400
        
        # Use sys.executable to get the current Python interpreter
        subprocess.Popen([sys.executable, "historical.py"])
        history_app_running = True
        print("History app launched successfully.")
        return jsonify({"message": "History app launched successfully!"}), 200
    except Exception as e:
        print(f"Error launching trading app: {e}")  # Log the error
        return jsonify({"error": str(e)}), 500
    
@app.route('/history-app-closed', methods=['POST'])
def history_app_closed():
    global history_app_running
    history_app_running = False
    print("Received notification that the history app has closed.")  # Log the closure
    return jsonify({"message": "Trading app status updated."}), 200


if __name__ == '__main__':

    if not test_api_connection():
        print("Failed to connect to OANDA API. Please check your credentials and connection.")
        sys.exit(1)

    if os.path.exists(local_csv_file):
        os.remove(local_csv_file)

    # Start threads only once
    candle_thread = threading.Thread(target=background_data_fetcher)
    candle_thread.daemon = True 
    candle_thread.start()

    live_price_thread = threading.Thread(target=background_live_price_fetcher)
    live_price_thread.daemon = True
    live_price_thread.start()

    signal_thread = threading.Thread(target=check_live_signals)
    signal_thread.daemon = True 
    signal_thread.start()

    balance_thread = threading.Thread(target=fetch_balance)
    balance_thread.daemon = True 
    balance_thread.start()

    app.run(host='localhost', port=3001, debug=True, use_reloader=False)
