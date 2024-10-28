import oandapyV20
import oandapyV20.endpoints.transactions as trans
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

def get_last_transaction_id(account_id):
    """Function to get the last transaction ID from the transaction history"""
    r = trans.TransactionList(account_id)
    try:
        client.request(r)
        last_transaction_id = int(r.response['lastTransactionID'])
        print(f"Last Transaction ID: {last_transaction_id}")
        return last_transaction_id
    except Exception as e:
        print(f"Error fetching last transaction: {e}")
        return None

def get_transactions_since_id(account_id, transaction_id):
    """Function to get transactions since a specified transaction ID"""
    params = {
        "id": transaction_id
    }
    r = trans.TransactionsSinceID(accountID=account_id, params=params)
    try:
        client.request(r)
        return r.response  # Return the fetched transactions
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return None

def log_transaction_details(transactions):
    """Function to log relevant details of transactions with 'units' and 'pl' > 0"""
    logged_transactions = []  # List to hold logged transaction details
    for transaction in transactions['transactions']:
        if 'units' in transaction and 'pl' in transaction and 'price' in transaction:
            units = transaction['units']
            pl = float(transaction['pl'])
            price = transaction['price']
            order_id = transaction['id']
            # Skip logging transactions where 'pl' is 0
            if pl != 0:
                # Append the order details to the list instead of printing
                logged_transactions.append({
                    "order_id": order_id,
                    "units": units,
                    "pl": pl,
                    "price": price
                })
    return logged_transactions  # Return the logged transaction details

def main():
    credentials = load_config()
    # Step 1: Get the last transaction ID
    last_transaction_id = get_last_transaction_id(credentials['account_id'])
    if last_transaction_id:
        # Step 2: Subtract 50 from the last transaction ID
        adjusted_transaction_id = last_transaction_id - 100
        print(f"Fetching transactions starting from ID: {adjusted_transaction_id}")
        # Step 3: Fetch transactions since the adjusted ID
        transactions = get_transactions_since_id(credentials['account_id'], adjusted_transaction_id)
        if transactions:
            # Return the transactions that have 'units', 'pl' (not zero), and 'price'
            return log_transaction_details(transactions)
        else:
            print("No transactions found.")
            return []  # Return an empty list if no transactions found
    else:
        print("Could not retrieve the last transaction ID.")
        return []  # Return an empty list if last transaction ID could not be retrieved

if __name__ == "__main__":
    main()
