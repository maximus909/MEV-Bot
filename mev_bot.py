import os
import json
import time
import numpy as np
from web3 import Web3
from web3.middleware import geth_poa_middleware
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
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
RPC_URLS = {
    "ETH": os.getenv("ETH_RPC"),
    "BSC": os.getenv("BSC_RPC"),
    "AVAX": os.getenv("AVAX_RPC"),
    "SOL": os.getenv("SOL_RPC"),
    "ARBITRUM": os.getenv("ARBITRUM_RPC"),
}

if not PRIVATE_KEY or not WALLET_ADDRESS:
    send_alert("❌ CRITICAL ERROR: PRIVATE_KEY or WALLET_ADDRESS is missing!")
    sys.exit(1)

wallet_address = Web3.to_checksum_address(WALLET_ADDRESS)

# ✅ Initialize Web3 Connections
w3 = {}
for chain, rpc in RPC_URLS.items():
    if rpc:
        try:
            w3[chain] = Web3(Web3.HTTPProvider(rpc))
            w3[chain].middleware_onion.inject(geth_poa_middleware, layer=0)  # Fix PoA issues
            if w3[chain].is_connected():
                send_alert(f"✅ {chain} RPC connected successfully.")
            else:
                send_alert(f"⚠️ {chain} RPC failed to connect.")
                del w3[chain]
        except Exception as e:
            send_alert(f"❌ Error connecting to {chain} RPC: {e}")
            del w3[chain]

if not w3:
    send_alert("❌ CRITICAL ERROR: No working RPC connections. Exiting bot.")
    sys.exit(1)

send_alert("🚀 MEV Bot started successfully!")

# ✅ AI Model for Predicting Trades
model = RandomForestClassifier(n_estimators=100)
dummy_data = np.random.rand(1000, 5)
labels = np.random.randint(0, 2, 1000)
model.fit(dummy_data, labels)

# ✅ Execute Trade
def execute_trade(chain, transaction):
    if chain not in w3:
        send_alert(f"Skipping {chain}, RPC is unavailable.")
        return

    try:
        value, gas_price, gas, max_fee, max_priority = transaction

        gas_limit = 210000
        gas_fee_eth = (gas_price * gas_limit) / 10**18
        profit = value - gas_fee_eth

        if profit > 0:
            nonce = w3[chain].eth.get_transaction_count(wallet_address)
            tx = {
                'to': wallet_address,
                'value': int(value),
                'gas': gas_limit,
                'gasPrice': int(gas_price * 1.1),  # Front-run adjustment
                'nonce': nonce,
                'chainId': w3[chain].eth.chain_id
            }
            
            signed_tx = w3[chain].eth.account.sign_transaction(tx, PRIVATE_KEY)
            tx_hash = w3[chain].eth.send_raw_transaction(signed_tx.raw_transaction)  # ✅ Fix here

            send_alert(f"✅ Trade Executed on {chain}: TX Hash={tx_hash.hex()}, Profit={profit} ETH")
        else:
            send_alert(f"❌ Trade Skipped: Profit={profit} ETH, Gas={gas_fee_eth} ETH")
    except Exception as e:
        send_alert(f"❌ Trade Execution Failed: {e}")

# ✅ Start Trading Loop
while True:
    for chain in w3.keys():
        transactions = fetch_mempool_data(chain)
        if transactions:
            for tx in transactions:
                execute_trade(chain, tx)
    send_alert("🔄 Bot completed a cycle, sleeping for 5 minutes.")
    time.sleep(300)
