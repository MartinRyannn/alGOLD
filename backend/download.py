import tpqoa
import pandas as pd
import os
from datetime import datetime

# Initialize tpqoa with the config file
api = tpqoa.tpqoa('oanda.cfg')

# Define the instrument and date range
instrument = "XAU_USD"
start_date = "2024-09-01"  # Start date
end_date = "2024-09-30"    # End date

# Create a list of dates to download (excluding weekends)
date_range = pd.date_range(start=start_date, end=end_date, freq='B')  # 'B' for business days

# Define the granularity and their corresponding folder names
granularities = {
    'M1': '1min',
    'M5': '5min',
    'M10': '10min',
    'M15': '15min',
    'M30': '30min'
}

# Loop through each granularity and create corresponding folder if not exists
for granularity, folder in granularities.items():
    os.makedirs(f"data/{folder}", exist_ok=True)

# Loop through each business day and download data for each granularity
for date in date_range:
    for granularity, folder in granularities.items():
        try:
            # Download historical data for the given granularity
            data = api.get_history(
                instrument=instrument,
                start=date.date().isoformat() + "T00:00:00",  # Start of the day
                end=date.date().isoformat() + "T23:59:59",    # End of the day
                granularity=granularity,  # Use current granularity in the loop
                price='M',  # Mid prices
                localize=False
            )

            # Check if data is empty
            if data.empty:
                print(f"No data returned for {date.date()} (Granularity: {granularity})")
                continue

            # Save each day's data to a separate CSV file in the corresponding folder
            csv_file_path = f"data/{folder}/XAU_USD_{date.date()}_{granularity}.csv"
            data.to_csv(csv_file_path, index=True)
            print(f"Data for {date.date()} (Granularity: {granularity}) downloaded and saved to {csv_file_path}")

        except Exception as e:
            print(f"Error downloading data for {date.date()} (Granularity: {granularity}): {e}")

print("Data download process completed.")
