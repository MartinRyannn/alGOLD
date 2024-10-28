import oandapyV20.endpoints.trades as trades
import oandapyV20
import configparser
import os

def load_config():
    """Function to load OANDA credentials from config file"""
    config = configparser.ConfigParser()
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "oanda.cfg")
    config.read(config_file)
    
    return {
        "account_id": config['oanda']['account_id'],
        "access_token": config['oanda']['access_token']
    }

# Initialize OANDA API client with credentials from config
credentials = load_config()
client = oandapyV20.API(access_token=credentials['access_token'])

def get_active_trades():
    """Fetch active trades and return relevant details."""
    credentials = load_config()  # Refresh credentials in case they've changed
    r = trades.OpenTrades(accountID=credentials['account_id'])
    try:
        # Make the API request
        client.request(r)
        trades_data = r.response.get('trades', [])
        
        # Extract only the necessary fields ('currentUnits' and 'unrealizedPL')
        active_trades = [
            {
                "currentUnits": trade["currentUnits"],
                "unrealizedPL": trade["unrealizedPL"]
            }
            for trade in trades_data
        ]
        return active_trades  # Return the list of active trades
    except Exception as e:
        print(f"Error fetching active trades: {e}")
        return []

if __name__ == "__main__":
    active_trades = get_active_trades()
    print(f"Active trades: {active_trades}")
