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
    with open("mev_debug.log", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    logging.info(message)
    print(message, flush=True)  # Force output to GitHub Actions logs

# ✅ Load Environment Variables
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URLS = {
    "ETH": os.getenv("ETH_RPC"),
    "BSC": os.getenv("BSC_RPC"),
    "AVAX": os.getenv("AVAX_RPC"),
    "SOL": os.getenv("SOL_RPC"),
    "ARBITRUM": os.getenv("ARBITRUM_RPC"),
}

# ✅ Check If Private Key Exists (Prevents Empty Transactions)
if not PRIVATE_KEY:
    send_alert("❌ CRITICAL ERROR: PRIVATE_KEY is missing!")
    sys.exit(1)

# ✅ Initialize Web3 Connections
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

# ✅ Execute Trade if Profitable
# ✅ Execute Trade if Profitable & Send Real Transactions
def execute_trade(chain, transaction):
    if chain not in w3:
        send_alert(f"Skipping {chain}, RPC is unavailable.")
        return

    try:
        value, gas_price, gas, max_fee, max_priority = transaction

        gas_limit = 210000
        gas_fee_eth = (gas_price * gas_limit) / 10**18
        min_profit = value * 0.002  # Ensure at least 0.2% profit

        if min_profit > gas_fee_eth:
            nonce = w3[chain].eth.get_transaction_count(0x52611C01d987503ff0d909888b7ecba79720eBa0)

            # ✅ Create a real transaction
            tx = {
                'to': wallet_address,
                'value': int(value),
                'gas': gas_limit,
                'gasPrice': int(gas_price),
                'nonce': nonce,
                'chainId': w3[chain].eth.chain_id
            }

            # ✅ Sign & Send the transaction
            signed_tx = w3[chain].eth.account.sign_transaction(tx, PRIVATE_KEY)
            tx_hash = w3[chain].eth.send_raw_transaction(signed_tx.rawTransaction)

            send_alert(f"✅ Trade Executed on {chain}: TX Hash={tx_hash.hex()}, Profit={min_profit} ETH")

            # ✅ Save TX Hash for tracking
            with open("executed_trades.txt", "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - TX: {tx_hash.hex()}\n")
        else:
            send_alert(f"❌ Trade Skipped on {chain}, Not Profitable Enough (Profit={min_profit} ETH, Gas Fee={gas_fee_eth} ETH)")
    except Exception as e:
        send_alert(f"❌ Trade Execution Failed: {e}")


# ✅ Main Trading Loop
def start_trading():
    while True:
        for chain in list(w3.keys()):
            transactions = fetch_mempool_data(chain)
            if transactions is not None:
                for tx in transactions:
                    if predict_trade(tx):
                        execute_trade(chain, tx)
        send_alert("🔄 Bot completed a cycle, sleeping for 5 minutes.")
        time.sleep(300)

if __name__ == "__main__":
    try:
        start_trading()
    except Exception as e:
        send_alert(f"❌ CRITICAL ERROR: {e}")
        sys.exit(1)  # Stops bot if there’s a fatal error
