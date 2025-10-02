# apps/wallets/sync_stakes.py (بهبود یافته)
from decimal import Decimal
import logging
from web3 import Web3
from django.db import connection
from apps.wallets.models import WalletConnection
from apps.miners.models import UserMiner
from apps.plans.models import Plan

logger = logging.getLogger(__name__)
w3 = Web3(Web3.HTTPProvider("https://bsc-dataseed.binance.org/"))

ERC20_ABI = [{
    "constant": True,
    "inputs": [{"name": "_owner", "type": "address"}],
    "name": "balanceOf",
    "outputs": [{"name": "balance", "type": "uint256"}],
    "type": "function",
}]

def try_acquire_lock(key=123456789):
    
    with connection.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(%s);", [key])
        return cur.fetchone()[0]

def release_lock(key=123456789):
    with connection.cursor() as cur:
        cur.execute("SELECT pg_advisory_unlock(%s);", [key])
        return cur.fetchone()[0]

def get_onchain_balance(address, contract_address, decimals=18):
    try:
        contract = w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=ERC20_ABI)
        raw_balance = contract.functions.balanceOf(w3.to_checksum_address(address)).call()
        return Decimal(raw_balance) / (Decimal(10) ** decimals)
    except Exception as e:
        logger.error(f"[Balance Error] {address} @ {contract_address} -> {e}")
        return None

def sync_stakes_with_onchain_balances():
    logger.info("🔁 Starting stake sync with on-chain balances...")
    lock_key = 987654321
    if not try_acquire_lock(lock_key):
        logger.warning("Another sync job is running. Exiting.")
        return

    try:
        qs = WalletConnection.objects.select_related("user").iterator()
        for conn in qs:
            user = conn.user
            userminer = UserMiner.objects.filter(user=user).select_related("miner__plan", "token").first()
            if not userminer:
                continue

            token = userminer.token
            miner = userminer.miner
            plan = miner.plan

            if not token or not token.contract_address:
                logger.warning(f"[Skip] Missing contract for token in user {user.email}")
                continue

            balance = get_onchain_balance(conn.wallet_address, token.contract_address, token.decimals or 18)
            if balance is None:
                continue

            current_stake = userminer.staked_amount or Decimal("0")
            if balance < current_stake:
                logger.info(f"{user.email} balance dropped from {current_stake} to {balance}")
                userminer.staked_amount = balance
                userminer.save(update_fields=["staked_amount"])

                if balance == 0:
                    userminer.is_online = False
                    userminer.save(update_fields=["is_online"])
                    miner.is_online = False
                    miner.save(update_fields=["is_online"])
                    logger.warning(f"{user.email} miner turned off due to zero balance")
                    continue

                downgraded_plan = Plan.objects.filter(price__lte=balance).order_by("-price").first()
                if downgraded_plan and downgraded_plan.level < plan.level:
                    new_miner = miner.__class__.objects.filter(plan=downgraded_plan, tokens=token).first()
                    if new_miner:
                        userminer.miner = new_miner
                        userminer.save(update_fields=["miner"])
                        logger.info(f"{user.email} downgraded to {downgraded_plan.name}")
    finally:
        release_lock(lock_key)
        logger.info("✅ Stake sync completed.")
