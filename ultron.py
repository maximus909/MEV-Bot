import os
import json
import time
import numpy as np
import pandas as pd
from web3 import Web3
from sklearn.ensemble import RandomForestClassifier
from telegram import Bot
import logging
import requests
from dotenv import load_dotenv

# ✅ Load Environment Variables
load_dotenv()

# ✅ Setup Logging
logging.basicConfig(filename='ultron.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# ✅ Load RPC URLs and Secrets
RPC_URLS = {
    "ETH": os.getenv("ETH_RPC"),
    "ARBITRUM": os.getenv("ARBITRUM_RPC"),
    "BSC": os.getenv("BSC_RPC"),
    "POLYGON": os.getenv("POLYGON_RPC"),
}

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# ✅ Initialize Web3 Connections
w3 = {}
for chain, rpc in RPC_URLS.items():
    try:
        w3[chain] = Web3(Web3.HTTPProvider(rpc))
        if w3[chain].is_connected():
            logging.info(f"✅ {chain} RPC connected successfully.")
        else:
            logging.info(f"⚠️ {chain} RPC failed to connect.")
            del w3[chain]
    except Exception as e:
        logging.info(f"❌ Error connecting to {chain} RPC: {e}")
        del w3[chain]

if not w3:
    logging.info("❌ CRITICAL ERROR: No working RPC connections. Exiting bot.")
    sys.exit(1)
else:
    logging.info("🚀 Ultron started successfully!")

# ✅ Initialize Telegram Bot
telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)

def send_telegram_message(message):
    try:
        telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        logging.info(f"❌ Telegram notification failed: {e}")

# ✅ GitHub Integration
def save_report_to_github(data):
    try:
        url = f"https://api.github.com/repos/{os.getenv('GITHUB_REPO')}/contents/report.json"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            sha = response.json().get("sha")
            content = json.dumps(data, indent=4)
            payload = {
                "message": "Update report",
                "content": content.encode("base64"),
                "sha": sha,
            }
            requests.put(url, headers=headers, json=payload)
        else:
            logging.info("❌ Failed to save report to GitHub.")
    except Exception as e:
        logging.info(f"❌ GitHub integration failed: {e}")

# ✅ AI Model for Predicting Profitable Trades
class SelfEvolvingModel:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100)
        self.data = []
        self.labels = []

    def train(self):
        if len(self.data) > 1000:  # Retrain when enough data is collected
            X_train, X_test, y_train, y_test = train_test_split(self.data, self.labels, test_size=0.2)
            self.model.fit(X_train, y_train)
            accuracy = accuracy_score(y_test, self.model.predict(X_test))
            logging.info(f"✅ AI Model Retrained. Accuracy: {accuracy * 100:.2f}%")

    def predict(self, transaction_data):
        try:
            prediction = self.model.predict([transaction_data])[0]
            self.data.append(transaction_data)  # Collect data for retraining
            self.labels.append(prediction)     # Collect labels (profitability)
            return prediction == 1
        except Exception as e:
            logging.info(f"❌ AI Prediction Failed: {e}")
            return False

# ✅ Main Trading Loop
def start_trading():
    model = SelfEvolvingModel()
    while True:
        for chain in list(w3.keys()):
            transactions = fetch_mempool_data(chain)
            if transactions is not None:
                for tx in transactions:
                    if model.predict(tx):
                        execute_trade(chain, tx)
        send_telegram_message("🔄 Bot completed a cycle, sleeping for 5 minutes.")
        time.sleep(300)

if __name__ == "__main__":
    try:
        start_trading()
    except Exception as e:
        send_telegram_message(f"❌ CRITICAL ERROR: {e}")
        sys.exit(1)
