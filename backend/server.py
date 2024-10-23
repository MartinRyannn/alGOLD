from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import pandas as pd

app = Flask(__name__)
CORS(app)

@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()

    account_id = data.get('id')
    access_token = data.get('token')
    account_type = data.get('type')

    with open("oanda.cfg", "w") as file:
        file.write(f"[oanda]\naccount_id = {account_id}\naccess_token = {access_token}\naccount_type = {account_type}")

    try:
        import tpqoa
        api = tpqoa.tpqoa("oanda.cfg")
        historical_data = api.get_history(
            instrument="XAU_USD",
            start="2022-09-01",
            end="2022-09-02",
            granularity="D",
            price="M" 
        )

        historical_data_dict = historical_data.reset_index().to_dict(orient="records")
        for record in historical_data_dict:
            record["time"] = record["time"].strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({"message": "Success", "historical_data": historical_data_dict})
    except Exception as e:
        return jsonify({"message": f"Failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(port=3000)
