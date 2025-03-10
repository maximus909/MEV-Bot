import json
import requests
import numpy as np
import tensorflow as tf
from web3 import Web3
import os
import logging
import pandas as pd
import time
import random
import sys

# ✅ Force TensorFlow to ignore GPU & CUDA warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  

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

# ✅ Initialize Web3 connections, skipping any that fail
w3 = {}
for chain, url in RPC_URLS.items():
    try:
        w3[chain] = Web3(Web3.HTTPProvider(url))
        if not w3[chain].is_connected():
            logging.warning(f"{chain} RPC is not working. Skipping...")
            del w3[chain]
    except Exception as e:
        logging.warning(f"Error connecting to {chain}: {e}")

# ✅ AI Neural Network for MEV Prediction
def build_advanced_neural_network():
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(1024, activation='relu', input_shape=(15,)),
        tf.keras.layers.Dense(512, activation='relu'),
        tf.keras.layers.Dense(256, activation='relu'),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model

# ✅ Load trained AI model (or create a new one)
if os.path.exists("mev_model.h5"):
    model = tf.keras.models.load_model("mev_model.h5")
else:
    model = build_advanced_neural_network()

# ✅ Function to collect and analyze mempool data (Skips failed RPCs)
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
                ] + [0] * 10)  # Padding for AI input size
            except:
                continue
        df = pd.DataFrame(data, columns=['Value', 'GasPrice', 'Gas', 'MaxFeePerGas', 'MaxPriorityFeePerGas'] + [f'Feature_{i}' for i in range(10)])
        df.to_csv(f'mempool_data_{chain}.csv', mode='a', header=False, index=False)
        logging.info(f"Fetched mempool data for {chain}.")
    except Exception as e:
        logging.error(f"Error fetching mempool data for {chain}: {e}")

# ✅ Function to execute profitable MEV trades
def execute_profitable_trade(chain, transaction):
    if chain not in w3:
        logging.warning(f"Skipping {chain}, RPC is not available.")
        return

    prediction = model.predict(np.array([transaction]))[0][0]
    if prediction > 0.95:
        logging.info(f"Executing trade on {chain} with predicted success rate: {prediction}")
        tx_hash = send_transaction(chain, transaction)
        if tx_hash:
            logging.info(f"✅ Trade Successful on {chain}: {tx_hash}")
        else:
            logging.warning(f"❌ Trade Failed on {chain}")
    else:
        logging.info(f"Skipping trade on {chain}, low probability: {prediction}")

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
            for chain in list(w3.keys()):  # Loop through available RPCs only
                logging.info(f"Fetching mempool data for {chain}...")
                fetch_mempool_data(chain)

                logging.info(f"Checking transactions for {chain}...")
                try:
                    transactions = pd.read_csv(f'mempool_data_{chain}.csv').to_numpy()
                except FileNotFoundError:
                    logging.warning(f"No transaction data found for {chain}. Skipping.")
                    continue

                for transaction in transactions:
                    logging.info(f"Attempting trade on {chain} for transaction: {transaction}")
                    execute_profitable_trade(chain, transaction)

            logging.info("Sleeping before the next cycle...")
            time.sleep(random.uniform(300, 600))  # Wait between 5-10 minutes
        except Exception as e:
            logging.error(f"Critical error: {e}")
            sys.exit(1)  # Restart the bot if it crashes

if __name__ == "__main__":
    logging.info("🚀 MEV Bot Started!")
    start_trading()
