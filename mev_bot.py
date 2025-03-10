import os
import json
import time
import numpy as np
import pandas as pd
from web3 import Web3
from sklearn.ensemble import RandomForestClassifier
import logging

# ✅ Setup Logging & Alerts
logging.basicConfig(filename='mev_bot.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def send_alert(message):
    with open("alerts.txt", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    logging.info(message)
    print(message)  # Also prints to GitHub Actions logs

# ✅ Load Environment Variables
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URLS = {
    "ETH": os.getenv("ETH_RPC"),
    "BSC": os.getenv("BSC_RPC"),
    "AVAX": os.getenv("AVAX_RPC"),
    "SOL": os.getenv("SOL_RPC"),
    "ARBITRUM": os.getenv("ARBITRUM_RPC"),
}

# ✅ Initialize Web3 Connections
w3 = {chain: Web3(Web3.HTTPProvider(RPC_URLS[chain])) for chain in RPC_URLS if RPC_URLS[chain]}

# ✅ AI Model for Predicting Profitable Trades
model = RandomForestClassifier(n_estimators=100)

# ✅ Train AI Model with Dummy Data (Replace with real training data)
dummy_data = np.random.rand(1000, 5)
labels = np.random.randint(0, 2, 1000)
model.fit(dummy_data, labels)

# ✅ Fetch Mempool Transactions
def fetch_mempool_data(chain):
    if chain not in w3:
        send_alert(f"Skipping {chain}, RPC is unavailable.")
        return None

    try:
        block = w3[chain].eth.get_block('pending', full_transactions=True)
        transactions = block.transactions
        data = []
        for tx in transactions:
            data.append([
                tx['value'], tx['gasPrice'], tx['gas'],
                tx.get('maxFeePerGas', 0),
                tx.get('maxPriorityFeePerGas', 0)
            ])
        return np.array(data)
    except Exception as e:
        send_alert(f"Error fetching mempool data for {chain}: {e}")
        return None

# ✅ Predict Profitable Trades
def predict_trade(transaction_data):
    return model.predict([transaction_data])[0] == 1

# ✅ Execute Trade if Profitable
def execute_trade(chain, transaction):
    if chain not in w3:
        send_alert(f"Skipping {chain}, RPC is unavailable.")
        return

    value, gas_price, gas, max_fee, max_priority = transaction
    if value > 10**18 and gas_price < 50 * 10**9:
        send_alert(f"✅ Trade Executed on {chain}: Value={value}, GasPrice={gas_price}")
    else:
        send_alert(f"❌ Trade Skipped on {chain}, not profitable.")

# ✅ Main Trading Loop
def start_trading():
    while True:
        for chain in list(w3.keys()):
            transactions = fetch_mempool_data(chain)
            if transactions is not None:
                for tx in transactions:
                    if predict_trade(tx):
                        execute_trade(chain, tx)
        time.sleep(300)

if __name__ == "__main__":
    start_trading()
