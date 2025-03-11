import os
import time
import requests
from web3 import Web3

# ✅ Logging function
def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

# ✅ Load ENV Variables
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ETH_RPC = os.getenv("ETH_RPC")
ARBITRUM_RPC = os.getenv("ARBITRUM_RPC")

# ✅ Web3 Setup
w3 = {
    "ETH": Web3(Web3.HTTPProvider(ETH_RPC)),
    "ARBITRUM": Web3(Web3.HTTPProvider(ARBITRUM_RPC)),
}

# ✅ Validate Connection
for chain, web3 in w3.items():
    if web3.is_connected():
        log(f"✅ {chain} RPC connected successfully.")
    else:
        log(f"❌ {chain} RPC failed to connect. Check RPC URL.")
        del w3[chain]

if not w3:
    log("❌ No working RPCs. Exiting.")
    exit()

log("🚀 MEV Bot started successfully!")

# ✅ Private Relay Endpoint (Alternative to Flashbots)
MEV_RELAY_URL = "https://api.edennetwork.io/v1/bundle"

# ✅ Execute Trade Using Private Relay
def execute_trade(chain, transaction):
    if chain not in w3:
        log(f"Skipping {chain}, RPC unavailable.")
        return

    try:
        web3 = w3[chain]
        account = web3.eth.account.from_key(PRIVATE_KEY)
        nonce = web3.eth.get_transaction_count(account.address)

        tx = {
            "from": account.address,
            "to": account.address,  # Target contract or arbitrage address
            "value": int(transaction[0]),
            "gas": 21000,
            "gasPrice": int(transaction[1]),
            "nonce": nonce,
            "chainId": web3.eth.chain_id,
        }

        log(f"🔍 Signing transaction on {chain}: {tx}")

        signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)

        # ✅ Correct the error: Use `raw_transaction` instead of `rawTransaction`
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        etherscan_link = f"https://etherscan.io/tx/{tx_hash.hex()}"
        log(f"✅ Trade Executed on {chain}: {etherscan_link}")

    except Exception as e:
        log(f"❌ Trade Execution Failed: {e}")

# ✅ Main Bot Loop
def start_bot():
    while True:
        for chain in list(w3.keys()):
            sample_transaction = [10**18, 2000000000]  # Dummy transaction for testing
            execute_trade(chain, sample_transaction)

        log("🔄 Bot completed a cycle, sleeping for 5 minutes.")
        time.sleep(300)

if __name__ == "__main__":
    start_bot()
