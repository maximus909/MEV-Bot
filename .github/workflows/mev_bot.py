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
import telegram
from flashbots import Flashbots
import asyncio

# Setup logging
logging.basicConfig(filename='mev_bot.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Load environment variables (GitHub Actions support)
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ETH_RPC = os.getenv("ETH_RPC")
BSC_RPC = os.getenv("BSC_RPC")
AVAX_RPC = os.getenv("AVAX_RPC")
SOL_RPC = os.getenv("SOL_RPC")
ARBITRUM_RPC = os.getenv("ARBITRUM_RPC")
OPTIMISM_RPC = os.getenv("OPTIMISM_RPC")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize Telegram Bot
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

def send_telegram_alert(message):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        logging.error(f"Error sending Telegram alert: {e}")

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
flashbots = Flashbots(w3["ETH"], private_key=PRIVATE_KEY)

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
        send_flashbots_bundle([transaction])
        send_telegram_alert(f"Executed profitable trade on {chain}")

# Function to send Flashbots bundle
def send_flashbots_bundle(transactions):
    try:
        bundle = flashbots.send_bundle(transactions, target_block_number=w3["ETH"].eth.block_number + 1)
        return bundle
    except Exception as e:
        logging.error(f"Flashbots execution failed: {e}")
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
            send_telegram_alert("MEV Bot executed a cycle successfully!")
            time.sleep(random.uniform(300, 600))
        except Exception as e:
            logging.error(f"Critical error: {e}")
            send_telegram_alert(f"MEV Bot encountered an error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    start_trading()
