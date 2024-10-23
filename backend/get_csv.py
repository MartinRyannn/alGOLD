import requests
import pandas as pd
import time

# Replace this with your EC2's public IP and port 8000
ec2_ip = "13.60.206.187"
csv_url = f"http://{ec2_ip}:8000/resampled_data.csv"

local_file_path = "downloaded_resampled_data.csv"

def fetch_csv():
    try:
        # Send GET request to fetch the CSV
        response = requests.get(csv_url)

        # Check if the request was successful
        if response.status_code == 200:
            # Save the CSV file locally
            with open(local_file_path, 'wb') as file:
                file.write(response.content)
            
            # Optionally, read the CSV into a pandas DataFrame
            df = pd.read_csv(local_file_path)

        else:
            pass  # You can log the error or handle it silently
    except Exception:
        pass  # Handle the exception silently

# Continuously fetch the CSV every 10 seconds
while True:
    fetch_csv()
    time.sleep(10)
