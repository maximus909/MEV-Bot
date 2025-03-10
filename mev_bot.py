import os
import json
import time
from web3 import Web3
from decimal import Decimal

# ✅ Load Environment Variables (From GitHub Secrets)
INFURA_URL = os.getenv("ETH_RPC")
CONTRACT_ADDRESS = os.getenv("FLASH_LOAN_CONTRACT")

# ✅ Set up Web3 Connection
web3 = Web3(Web3.HTTPProvider(INFURA_URL))
assert web3.is_connected(), "❌ ERROR: Cannot connect to Ethereum network."

# ✅ Uniswap & Sushiswap Router Addresses
UNISWAP_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
SUSHISWAP_ROUTER = "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"

# ✅ Load Uniswap & Sushiswap contract ABIs (Fixes the ABI loading issue)
def load_abi(file_name):
    with open(file_name) as f:
        abi_data = json.load(f)
        return abi_data["abi"] if "abi" in abi_data else abi_data  # ✅ Extract ABI correctly

uniswap_abi = load_abi("uniswap_abi.json")
sushiswap_abi = load_abi("sushiswap_abi.json")

# ✅ Initialize Uniswap & Sushiswap Contracts
uniswap = web3.eth.contract(address=UNISWAP_ROUTER, abi=uniswap_abi)
sushiswap = web3.eth.contract(address=SUSHISWAP_ROUTER, abi=sushiswap_abi)

# ✅ Token Addresses
WETH = "0xC02aaa39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # Wrapped ETH
DAI = "0x6B175474E89094C44Da98b954EedeAC495271d0F"  # DAI Token

# ✅ Function to Get Token Prices
def get_price(router, token_in, token_out, amount):
    path = [token_in, token_out]
    try:
        price = router.functions.getAmountsOut(amount, path).call()
        return price[-1]  # Returns the final output amount
    except Exception as e:
        print(f"❌ Error fetching price: {e}")
        return None

# ✅ Function to Find Arbitrage Opportunities
def find_arbitrage():
    trade_amount = Web3.to_wei(1, "ether")  # 1 ETH

    # Fetch prices from Uniswap & Sushiswap
    uniswap_price = get_price(uniswap, WETH, DAI, trade_amount)
    sushiswap_price = get_price(sushiswap, WETH, DAI, trade_amount)

    if not uniswap_price or not sushiswap_price:
        print("⚠️ Skipping trade: Unable to fetch prices.")
        return

    # Convert to readable format
    uniswap_price_eth = Web3.from_wei(uniswap_price, "ether")
    sushiswap_price_eth = Web3.from_wei(sushiswap_price, "ether")

    print(f"🔍 Uniswap Price: {uniswap_price_eth} DAI")
    print(f"🔍 Sushiswap Price: {sushiswap_price_eth} DAI")

    # ✅ If Uniswap price is lower than Sushiswap, execute arbitrage
    if uniswap_price > sushiswap_price * 1.005:  # Ensuring at least 0.5% profit
        profit = Decimal(uniswap_price - sushiswap_price) / Decimal(10**18)
        print(f"✅ Arbitrage found! Estimated Profit: {profit} ETH")

        # ✅ Call Flash Loan Contract
        execute_flash_loan(WETH, DAI, trade_amount)
    else:
        print("❌ No arbitrage opportunity found.")

# ✅ Function to Execute Flash Loan Arbitrage
def execute_flash_loan(token_in, token_out, amount):
    print(f"🚀 Executing Flash Loan for {amount / 10**18} ETH...")

    flash_loan_contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=uniswap_abi)  # Use Uniswap ABI

    tx = flash_loan_contract.functions.startArbitrage(token_in, token_out, amount).build_transaction({
        "from": web3.eth.default_account,
        "gas": 500000,
        "gasPrice": web3.eth.gas_price,
        "nonce": web3.eth.get_transaction_count(web3.eth.default_account),
    })

    signed_tx = web3.eth.account.sign_transaction(tx, os.getenv("PRIVATE_KEY"))
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

    print(f"✅ Flash Loan Arbitrage Executed! TX Hash: {tx_hash.hex()}")

# ✅ Run the Bot Every 10 Minutes
while True:
    find_arbitrage()
    print("🔄 Sleeping for 10 minutes...")
    time.sleep(600)  # 10 minutes
