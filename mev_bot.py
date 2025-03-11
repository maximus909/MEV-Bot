import json
import requests
import time
import numpy as np
from web3 import Web3
import os
import logging

# ✅ Logging Setup
logging.basicConfig(filename="mev_bot.log", level=logging.DEBUG, format="%(asctime)s - %(message)s")

print("🚀 Starting MEV Bot...")  # Ensure we see this in GitHub logs

# ✅ Load Environment Variables
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URLS = {
    "ETH": os.getenv("ETH_RPC"),
    "ARBITRUM": os.getenv("ARBITRUM_RPC"),
}

# ✅ Web3 Setup
w3 = {}
for chain, rpc in RPC_URLS.items():
    if rpc:
        try:
            print(f"🔍 Connecting to {chain} RPC: {rpc}")  # Debug line
            w3[chain] = Web3(Web3.HTTPProvider(rpc))
            if w3[chain].is_connected():
                print(f"✅ {chain} RPC connected successfully.")
            else:
                print(f"⚠️ {chain} RPC failed to connect.")
                del w3[chain]
        except Exception as e:
            print(f"❌ Error connecting to {chain} RPC: {e}")
            del w3[chain]

if not w3:
    print("❌ CRITICAL ERROR: No working RPC connections. Exiting bot.")
    exit(1)
else:
    print("🚀 MEV Bot started successfully!")

# ✅ Fetch Mempool Transactions
def fetch_mempool_data(chain):
    if chain not in w3:
        print(f"Skipping {chain}, RPC is unavailable.")
        return None

    try:
        print(f"🔍 Fetching mempool data for {chain}...")
        block = w3[chain].eth.get_block("pending", full_transactions=True)
        transactions = block.transactions
        print(f"✅ Found {len(transactions)} transactions in mempool.")
        data = []
        for tx in transactions:
            data.append([
                int(tx["value"]),
                int(tx["gasPrice"]),
                int(tx["gas"]),
                int(tx.get("maxFeePerGas", 0)),
                int(tx.get("maxPriorityFeePerGas", 0)),
            ])
        return np.array(data)
    except Exception as e:
        print(f"❌ Error fetching mempool data for {chain}: {e}")
        return None


      def execute_trade(chain, transaction):
    if chain not in w3:
        print(f"Skipping {chain}, RPC is unavailable.")
        return

    try:
        value, gas_price, gas, max_fee, max_priority = map(int, transaction)
        account = w3[chain].eth.account.from_key(PRIVATE_KEY)
        nonce = w3[chain].eth.get_transaction_count(account.address)

        tx = {
            "from": account.address,
            "to": account.address,
            "value": value,
            "gas": 21000,
            "gasPrice": gas_price,
            "nonce": nonce,
            "chainId": w3[chain].eth.chain_id,
        }

        print(f"🔍 Signing transaction on {chain}: {tx}")

        # ✅ Fix: Correct Web3 signing method
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3[chain].eth.send_raw_transaction(signed_tx.raw_transaction)

        etherscan_link = f"https://etherscan.io/tx/{tx_hash.hex()}"
        print(f"✅ Trade Executed on {chain}: {etherscan_link}")

    except Exception as e:
        print(f"❌ Trade Execution Failed: {e}")


            
# ✅ Send transaction via Private Relay
def send_private_transaction(signed_tx_hex):
    try:
        relay_url = "https://api.edennetwork.io/v1/bundle"  # Replace with working relay
        headers = {"Content-Type": "application/json"}
        tx_data = {"tx": signed_tx_hex, "mev": True}
        response = requests.post(relay_url, json=tx_data, headers=headers)

        if response.status_code == 200:
            return response.json().get("tx_hash")
        else:
            print(f"❌ Relay Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Private Relay Failed: {e}")
        return None

# ✅ Start Bot
def start_trading():
    while True:
        for chain in list(w3.keys()):
            transactions = fetch_mempool_data(chain)
            if transactions is not None:
                for tx in transactions:
                    execute_trade(chain, tx)
        print("🔄 Bot completed a cycle, sleeping for 5 minutes.")
        time.sleep(300)

if __name__ == "__main__":
    start_trading()
