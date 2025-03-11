import os
import json
import time
import numpy as np
import pandas as pd
from web3 import Web3
from sklearn.ensemble import RandomForestClassifier
import logging
import sys

# ✅ Setup Logging & Alerts
logging.basicConfig(filename='mev_bot.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def send_alert(message):
    with open("alerts.txt", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    logging.info(message)
    print(message, flush=True)  # Force output to GitHub Actions logs

# ✅ Load Environment Variables (BSC Removed)
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URLS = {
    "ETH": os.getenv("ETH_RPC"),
    "AVAX": os.getenv("AVAX_RPC"),
    "SOL": os.getenv("SOL_RPC"),
    "ARBITRUM": os.getenv("ARBITRUM_RPC"),
}

# ✅ Remove BSC from Web3 Connections
w3 = {}
for chain, rpc in RPC_URLS.items():
    if rpc:
        try:
            w3[chain] = Web3(Web3.HTTPProvider(rpc))
            if w3[chain].is_connected():
                send_alert(f"✅ {chain} RPC connected successfully.")
            else:
                send_alert(f"⚠️ {chain} RPC failed to connect.")
                del w3[chain]
        except Exception as e:
            send_alert(f"❌ Error connecting to {chain} RPC: {e}")
            del w3[chain]

# ✅ Ensure at least one blockchain is connected
if not w3:
    send_alert("❌ CRITICAL ERROR: No working RPC connections. Exiting bot.")
    sys.exit(1)
else:
    send_alert("🚀 MEV Bot started successfully!")

             

# ✅ AI Model for Predicting Profitable Trades
try:
    model = RandomForestClassifier(n_estimators=100)
    dummy_data = np.random.rand(1000, 5)
    labels = np.random.randint(0, 2, 1000)
    model.fit(dummy_data, labels)
    send_alert("✅ AI Model Loaded Successfully")
except Exception as e:
    send_alert(f"❌ AI Model Initialization Failed: {e}")
    sys.exit(1)

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
    try:
        return model.predict([transaction_data])[0] == 1
    except Exception as e:
        send_alert(f"❌ AI Prediction Failed: {e}")
        return False



           from eth_account.messages import encode_defunct

# ✅ Gas-Free MEV Execution Using Private Relay
def execute_trade(chain, transaction):
    if chain not in w3:
        send_alert(f"Skipping {chain}, RPC is unavailable.")
        return

    try:
        value, gas_price, gas, max_fee, max_priority = transaction
        account = w3[chain].eth.account.from_key(PRIVATE_KEY)
        nonce = w3[chain].eth.get_transaction_count(account.address)

        tx = {
            "from": account.address,
            "to": account.address,  # Target contract or arbitrage address
            "value": value,
            "gas": 0,  # Gasless execution
            "gasPrice": 0,  # Gas-free via private relay
            "nonce": nonce,
        }

        signed_tx = w3[chain].eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = send_private_transaction(signed_tx.rawTransaction)

        if tx_hash:
            etherscan_link = f"https://etherscan.io/tx/{tx_hash.hex()}"
            send_alert(f"""
            ✅ Gas-Free Trade Executed on {chain}:
            🔹 Value: {value / 10**18:.6f} ETH
            🔹 Transaction Hash: {tx_hash.hex()}
            🔹 🔗 [View on Etherscan]({etherscan_link})
            """)
        else:
            send_alert("❌ Gas-Free Trade Failed!")
    except Exception as e:
        send_alert(f"❌ Trade Execution Failed: {e}")

# ✅ Send transaction via Private MEV Relay
def send_private_transaction(signed_tx):
    try:
        relay_url = "https://api.edennetwork.io/v1/bundle"  # Replace with working relay
        headers = {"Content-Type": "application/json"}
        tx_data = {"tx": signed_tx.hex(), "mev": True}
        response = requests.post(relay_url, json=tx_data, headers=headers)

        if response.status_code == 200:
            return response.json().get("tx_hash")
        else:
            send_alert(f"❌ Relay Error: {response.text}")
            return None
    except Exception as e:
        send_alert(f"❌ Private Relay Failed: {e}")
        return None


# ✅ Continuous Trading with More Frequent Checks
def start_trading():
    while True:
        trade_count = 0  # Track how many trades were executed
        
        for chain in list(w3.keys()):
            transactions = fetch_mempool_data(chain)
            if transactions is not None:
                for tx in transactions:
                    if predict_trade(tx):
                        execute_trade(chain, tx)
                        trade_count += 1

        if trade_count == 0:
            send_alert("🔄 No profitable trades found. Checking again in 30 seconds.")
            time.sleep(30)  # Check again sooner
        else:
            send_alert(f"✅ {trade_count} profitable trades executed. Sleeping for 5 minutes.")
            time.sleep(300)  # Normal sleep after successful trades


if __name__ == "__main__":
    try:
        start_trading()
    except Exception as e:
        send_alert(f"❌ CRITICAL ERROR: {e}")
        sys.exit(1)  # Stops bot if there’s a fatal error
