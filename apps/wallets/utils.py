# apps/wallet/utils.py

import time
import logging
from decimal import Decimal
from web3 import Web3, HTTPProvider
from web3.exceptions import TransactionNotFound
from django.conf import settings
from eth_account import Account

logger = logging.getLogger("wallet")

BSC_RPC = getattr(settings, "BSC_RPC_URL", None)
CHAIN_ID = getattr(settings, "BSC_CHAIN_ID", 56)
WAIT_RECEIPT_TIMEOUT = int(getattr(settings, "REWARD_WAIT_RECEIPT_TIMEOUT", 180))
GAS_FALLBACK = int(getattr(settings, "GAS_FALLBACK", 150000))  # default fallback

def get_web3():
    if not BSC_RPC:
        raise RuntimeError("BSC_RPC_URL not configured in settings")
    w3 = Web3(HTTPProvider(BSC_RPC))
    if not w3.isConnected():
        raise RuntimeError("Unable to connect to BSC RPC")
    return w3

def to_wei(amount_decimal: Decimal, decimals: int) -> int:
    return int((amount_decimal * (Decimal(10) ** decimals)).to_integral_value())

def from_wei(amount_int: int, decimals: int) -> Decimal:
    return (Decimal(amount_int) / (Decimal(10) ** decimals)).quantize(Decimal("0.000000000000000001"))

def get_erc20_contract(w3: Web3, contract_address: str):
    abi = [
        # minimal ABI for balanceOf, transfer, decimals
        {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
        {"constant":False,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"},
        {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
    ]
    return w3.eth.contract(address=w3.toChecksumAddress(contract_address), abi=abi)

def get_token_balance(w3: Web3, contract, address: str) -> int:
    return contract.functions.balanceOf(w3.toChecksumAddress(address)).call()

def build_and_send_erc20_transfer(
    token_contract,
    server_address: str,
    server_private_key: str,
    to_address: str,
    amount_wei: int,
    nonce: int,
    gas_limit: int = None,
    gas_price_wei: int = None,
    chain_id: int = CHAIN_ID,
    wait_timeout: int = WAIT_RECEIPT_TIMEOUT,
):
    """
    Build, sign and send tx using an explicit nonce (provided by nonce-reservation).
    Returns (tx_hash_hex, receipt).
    """
    w3 = token_contract.web3
    server_address = w3.toChecksumAddress(server_address)
    to_address = w3.toChecksumAddress(to_address)

    tx = token_contract.functions.transfer(to_address, amount_wei).buildTransaction({
        'from': server_address,
        'nonce': int(nonce),
    })

    # gas estimation with fallback
    try:
        est_gas = token_contract.functions.transfer(to_address, amount_wei).estimateGas({'from': server_address})
    except Exception as e:
        logger.warning("estimateGas failed, fallback used: %s", e)
        est_gas = GAS_FALLBACK

    tx['gas'] = gas_limit or (est_gas + 20000)
    if gas_price_wei:
        tx['gasPrice'] = gas_price_wei
    else:
        tx['gasPrice'] = w3.eth.gas_price

    tx['chainId'] = chain_id

    signed = Account.sign_transaction(tx, server_private_key)
    raw = signed.rawTransaction
    tx_hash = w3.eth.send_raw_transaction(raw)

    # wait for receipt with timeout
    start = time.time()
    while True:
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            return tx_hash.hex(), receipt
        except TransactionNotFound:
            if time.time() - start > wait_timeout:
                raise TimeoutError("Timeout waiting for transaction receipt")
            time.sleep(2)  # polling interval
