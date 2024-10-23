import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import time

# URL for candle data (removed the live price URL as requested)
csv_url_candles = "http://16.171.200.76:8000/resampled_data.csv"

# Cache for storing fetched data
data_cache = None

def fetch_candles():
    """Fetches candle data from the specified URL."""
    global data_cache
    try:
        response = requests.get(csv_url_candles)
        if response.status_code == 200:
            data_cache = pd.read_csv(io.StringIO(response.text))
        else:
            print(f"Error fetching candle data: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

# Strategy Indicator Calculations

def calculate_rsi(df, period=14):
    """Calculates the RSI (Relative Strength Index)"""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

def calculate_atr(df, period=14):
    """Calculates the Average True Range (ATR)"""
    df['high_low'] = df['High'] - df['Low']
    df['high_close'] = np.abs(df['High'] - df['Close'].shift(1))
    df['low_close'] = np.abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=period).mean()

def calculate_sar(df, acceleration=0.02, max_acceleration=0.2):
    """Calculates the Parabolic SAR"""
    df['SAR'] = np.zeros(len(df))
    df['SAR'][0] = df['Low'][0]
    is_uptrend = True
    ep = df['High'][0]
    af = acceleration

    for i in range(1, len(df)):
        if is_uptrend:
            df['SAR'][i] = df['SAR'][i - 1] + af * (ep - df['SAR'][i - 1])
            if df['Low'][i] < df['SAR'][i]:
                is_uptrend = False
                df['SAR'][i] = ep
                ep = df['Low'][i]
                af = acceleration
            else:
                if df['High'][i] > ep:
                    ep = df['High'][i]
                    af = min(af + acceleration, max_acceleration)
        else:
            df['SAR'][i] = df['SAR'][i - 1] + af * (ep - df['SAR'][i - 1])
            if df['High'][i] > df['SAR'][i]:
                is_uptrend = True
                df['SAR'][i] = ep
                ep = df['High'][i]
                af = acceleration
            else:
                if df['Low'][i] < ep:
                    ep = df['Low'][i]
                    af = min(af + acceleration, max_acceleration)

def calculate_moving_average(df, period=50):
    """Calculates the Moving Average (MA)"""
    df['MA'] = df['Close'].rolling(window=period).mean()

def apply_strategy(df):
    """Applies the trading strategy and logs trades."""
    calculate_rsi(df, period=14)
    calculate_atr(df, period=14)
    calculate_sar(df)
    calculate_moving_average(df, period=50)

    # Placeholder to store trades
    trade_log = []
    active_trade = False
    entry_price = None
    stop_loss = None
    take_profit = None

    for i in range(1, len(df)):
        if active_trade:
            # Check stop loss or take profit
            if df['Close'][i] <= stop_loss:
                trade_log[-1]['Exit'] = stop_loss
                trade_log[-1]['Exit Time'] = df['Time'][i]
                trade_log[-1]['P/L'] = stop_loss - entry_price  # Profit/Loss
                active_trade = False
            elif df['Close'][i] >= take_profit:
                trade_log[-1]['Exit'] = take_profit
                trade_log[-1]['Exit Time'] = df['Time'][i]
                trade_log[-1]['P/L'] = take_profit - entry_price  # Profit/Loss
                active_trade = False
            continue

        # Buy signal
        if df['Close'][i] > df['SAR'][i] and df['RSI'][i] < 80 and df['Close'][i] > df['MA'][i]:
            entry_price = df['Close'][i]
            stop_loss = entry_price - df['ATR'][i]
            take_profit = entry_price + (df['ATR'][i] * 2)
            active_trade = True
            trade_log.append({
                'Entry': entry_price,
                'Entry Time': df['Time'][i],
                'Direction': 'Buy',
                'Exit': None,
                'Exit Time': None,
                'P/L': None  # Profit/Loss will be calculated when the trade is closed
            })

    return trade_log

def print_trade_results(trades):
    """Prints the trade results (entry, exit, profit/loss)."""
    total_profit_loss = 0
    print("\nTrade Results:")
    print("---------------------------------------------------")
    for trade in trades:
        print(f"Entry Time: {trade['Entry Time']}, Entry Price: {trade['Entry']}")
        if trade['Exit'] is not None:
            print(f"Exit Time: {trade['Exit Time']}, Exit Price: {trade['Exit']}, P/L: {trade['P/L']}")
            total_profit_loss += trade['P/L']
        else:
            print("Trade still active...")
        print("---------------------------------------------------")

    print(f"Total Profit/Loss: {total_profit_loss}")
    print("---------------------------------------------------")

# Fetch data and plot the strategy
def run_strategy():
    fetch_candles()
    if data_cache is not None:
        df = data_cache.copy()
        df['Time'] = pd.to_datetime(df['Time'])

        # Apply the strategy
        trades = apply_strategy(df)

        # Print trade results
        print_trade_results(trades)

        # Plotting the results
        plt.figure(figsize=(14, 8))
        plt.plot(df['Time'], df['Close'], label='Close Price', color='blue')
        plt.plot(df['Time'], df['SAR'], label='SAR', color='orange')
        plt.plot(df['Time'], df['MA'], label='Moving Average', color='purple')

        # Mark trades
        for trade in trades:
            plt.scatter(trade['Entry Time'], trade['Entry'], marker='^', color='green', s=100)
            if trade['Exit'] is not None:
                plt.scatter(trade['Exit Time'], trade['Exit'], marker='v', color='red', s=100)

        plt.legend()
        plt.show()
    else:
        print("No data available to run the strategy.")

# Continuously fetch candle data and run the strategy every 15 seconds
while True:
    run_strategy()
    time.sleep(15)  # Fetch and process every 15 seconds
