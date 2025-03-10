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

# Setup logging
logging.basicConfig(filename='mev_bot.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Load environment variables
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ETH_RPC = os.getenv("ETH_RPC")  # This is now your private RPC (e.g., MEV-Blocker)
BSC_RPC = os.getenv("BSC_RPC")
AVAX_RPC = os.getenv("AVAX_RPC")
SOL_RPC = os.getenv("SOL_RPC")
ARBITRUM_RPC = os.getenv("ARBITRUM_RPC")
OPTIMISM_RPC = os.getenv("OPTIMISM_RPC")

# Multi-Blockchain RPCs
RPC_URLS = {
    "ETH": ETH_RPC,
    "BSC": BSC_RPC,
    "AVAX": AVAX_RPC,
    "SOL": SOL_RPC,
    "ARBITRUM": ARBITRUM_RPC,
    "OPTIMISM": OPTIMISM_RPC
}

w3 = {chain: Web3(Web3.HTTPProvider(RPC_URLS[chain])) for chain in RPC_URLS}

# AI Neural Network for MEV Prediction
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

# Load trained AI model
if os.path.exists("mev_model.h5"):
    model = tf.keras.models.load_model("mev_model.h5")
else:
    model = build_advanced_neural_network()

# Function to collect and analyze mempool data
def fetch_mempool_data(chain):
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
                ] + [0] * 10)
            except:
                continue
        df = pd.DataFrame(data, columns=['Value', 'GasPrice', 'Gas', 'MaxFeePerGas', 'MaxPriorityFeePerGas'] + [f'Feature_{i}' for i in range(10)])
        df.to_csv(f'mempool_data_{chain}.csv', mode='a', header=False, index=False)
    except Exception as e:
        logging.error(f"Error fetching mempool data for {chain}: {e}")

# Function to execute profitable MEV trades
def execute_profitable_trade(chain, transaction):
    if model.predict(np.array([transaction]))[0][0] > 0.95:
        send_transaction(transaction)

# Function to send transactions using Private RPCs
def send_transaction(tx_data):
    try:
        signed_tx = w3["ETH"].eth.account.sign_transaction(tx_data, PRIVATE_KEY)
        tx_hash = w3["ETH"].eth.send_raw_transaction(signed_tx.rawTransaction)
        logging.info(f"Transaction sent: {tx_hash.hex()}")
        return tx_hash.hex()
    except Exception as e:
        logging.error(f"Transaction failed: {e}")
        return None

# Main Trading Loop
def start_trading():
    while True:
        try:
            for chain in RPC_URLS:
                fetch_mempool_data(chain)
                transactions = pd.read_csv(f'mempool_data_{chain}.csv').to_numpy()
                for transaction in transactions:
                    execute_profitable_trade(chain, transaction)
            time.sleep(random.uniform(300, 600))
        except Exception as e:
            logging.error(f"Critical error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    start_trading()
