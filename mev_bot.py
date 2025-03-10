import json
import requests
import numpy as np
from web3 import Web3
import os
import logging
import pandas as pd
import time
import random
import sys

# ✅ Setup logging
logging.basicConfig(filename='mev_bot.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# ✅ Load environment variables
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ETH_RPC = os.getenv("ETH_RPC")  
BSC_RPC = os.getenv("BSC_RPC")
AVAX_RPC = os.getenv("AVAX_RPC")
SOL_RPC = os.getenv("SOL_RPC")
ARBITRUM_RPC = os.getenv("ARBITRUM_RPC")
OPTIMISM_RPC = os.getenv("OPTIMISM_RPC")

# ✅ Multi-Blockchain RPCs
RPC_URLS = {
    "ETH": ETH_RPC,
    "BSC": BSC_RPC,
    "AVAX": AVAX_RPC,
    "SOL": SOL_RPC,
    "ARBITRUM": ARBITRUM_RPC,
    "OPTIMISM": OPTIMISM_RPC
}

# ✅ Initialize Web3 connections (Skip RPCs that fail)
w3 = {}
for chain, url in RPC_URLS.items():
    try:
        w3[chain] = Web3(Web3.HTTPProvider(url))
        if not w3[chain].is_connected():
            logging.warning(f"{chain} RPC is not working. Skipping...")
            del w3[chain]
    except Exception as e:
        logging.warning(f"Error connecting to {chain}: {e}")

# ✅ Function to collect mempool data (Skip failed RPCs)
def fetch_mempool_data(chain):
    if chain not in w3:
        logging.warning(f"Skipping {chain}, RPC is not available.")
        return

    try:
        pending_transactions = w3[chain].eth.get_block('pending')['transactions']
        data = []
        for tx_hash in pending_transactions:
            try:
                tx = w3[chain].eth.get_transaction(tx_hash)
                data.append([
                    tx['value'], tx['gasPrice'], tx['gas'],
                    tx.get('maxFeePerGas', 0),
                    tx.get('maxPriorityFeePerGas', 0)
                ] + [0] * 10)  # Padding for input size
            except:
                continue
        df = pd.DataFrame(data, columns=['Value', 'GasPrice', 'Gas', 'MaxFeePerGas', 'MaxPriorityFeePerGas'] + [f'Feature_{i}' for i in range(10)])
        df.to_csv(f'mempool_data_{chain}.csv', mode='a', header=False, index=False)
        logging.info(f"Fetched mempool data for {chain}.")
    except Exception as e:
        logging.error(f"Error fetching mempool data for {chain}: {e}")

# ✅ Function to execute MEV trades using simple rules
def execute_profitable_trade(chain, transaction):
    if chain not in w3:
        logging.warning(f"Skipping {chain}, RPC is not available.")
        return

    value = transaction[0]  # ETH/BSC/SOL value
    gas_price = transaction[1]  # Gas price in Wei

    # ✅ Trade if transaction value is high & gas is low
    if value > 10**18 and gas_price < 50 * 10**9:  # Adjust as needed
        logging.info(f"Executing trade on {chain}: Value={value}, GasPrice={gas_price}")
        tx_hash = send_transaction(chain, transaction)
        if tx_hash:
            logging.info(f"✅ Trade Successful on {chain}: {tx_hash}")
        else:
            logging.warning(f"❌ Trade Failed on {chain}")
    else:
        logging.info(f"Skipping trade on {chain}, not profitable.")

# ✅ Function to send transactions using Private RPCs
def send_transaction(chain, tx_data):
    if chain not in w3:
        logging.warning(f"Skipping {chain}, RPC is not available.")
        return None

    try:
        signed_tx = w3[chain].eth.account.sign_transaction(tx_data, PRIVATE_KEY)
        tx_hash = w3[chain].eth.send_raw_transaction(signed_tx.rawTransaction)
        logging.info(f"Transaction sent on {chain}: {tx_hash.hex()}")
        return tx_hash.hex()
    except Exception as e:
        logging.error(f"Transaction failed on {chain}: {e}")
        return None

# ✅ Main Trading Loop (Handles RPC failures & logs everything)
def start_trading():
    while True:
        try:
            logging.info("🚀 MEV Bot Running... Checking RPCs & Mempool Data")
            print("🚀 MEV Bot Running... Checking RPCs & Mempool Data")  # Force Print to GitHub Logs
            
            for chain in list(w3.keys()):
                logging.info(f"🔍 Fetching mempool data for {chain}...")
                print(f"🔍 Fetching mempool data for {chain}...")  # Print to console
                fetch_mempool_data(chain)

                logging.info(f"📊 Checking transactions for {chain}...")
                print(f"📊 Checking transactions for {chain}...")  # Print to console
                try:
                    transactions = pd.read_csv(f'mempool_data_{chain}.csv').to_numpy()
                except FileNotFoundError:
                    logging.warning(f"⚠️ No transaction data found for {chain}. Skipping.")
                    print(f"⚠️ No transaction data found for {chain}. Skipping.")
                    continue

                for transaction in transactions:
                    logging.info(f"💰 Attempting trade on {chain} for transaction: {transaction}")
                    print(f"💰 Attempting trade on {chain} for transaction: {transaction}")
                    execute_profitable_trade(chain, transaction)

            logging.info("⏳ Sleeping before the next cycle...")
            print("⏳ Sleeping before the next cycle...")
            time.sleep(random.uniform(300, 600))
        except Exception as e:
            logging.error(f"❌ Critical error: {e}")
            print(f"❌ Critical error: {e}")
            logging.info("🔄 Continuing bot execution despite the error...")
            print("🔄 Continuing bot execution despite the error...")
            time.sleep(5)
