import oandapyV20.endpoints.trades as trades
import oandapyV20

# Define OANDA account and API access
accountID = "101-011-29517098-001"
client = oandapyV20.API(access_token="42f110c2d99aee8e029b112fb90def99-0c621211f1009bac68c51ff13b2202f3")

def get_active_trades():
    """Fetch active trades and return relevant details."""
    r = trades.OpenTrades(accountID=accountID)
    
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


