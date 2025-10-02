import logging
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from web3 import Web3

from apps.wallets.models import WalletConnection
from apps.miners.models import UserMiner
from apps.plans.models import Plan

logger = logging.getLogger(__name__)

w3 = Web3(Web3.HTTPProvider(settings.BSC_RPC_URL))

ERC20_ABI = [{
    "constant": True,
    "name": "balanceOf",
    "inputs": [{"name": "_owner", "type": "address"}],
    "outputs": [{"name": "balance", "type": "uint256"}],
    "type": "function",
}]

LOCK_KEY = 987654321


def try_acquire_lock(key=LOCK_KEY):
    if 'postgresql' in settings.DATABASES['default']['ENGINE']:
        with connection.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s);", [key])
            return cur.fetchone()[0]
    return True


def release_lock(key=LOCK_KEY):
    if 'postgresql' in settings.DATABASES['default']['ENGINE']:
        with connection.cursor() as cur:
            cur.execute("SELECT pg_advisory_unlock(%s);", [key])
            return cur.fetchone()[0]
    return True


def get_onchain_balance(address, contract_address, decimals=18):
    try:
        contract = w3.eth.contract(
            address=w3.to_checksum_address(contract_address),
            abi=ERC20_ABI
        )
        raw_balance = contract.functions.balanceOf(
            w3.to_checksum_address(address)
        ).call()
        return Decimal(raw_balance) / (Decimal(10) ** decimals)
    except Exception as e:
        logger.error(f"[Balance Error] {address}@{contract_address} → {e}")
        return None


class Command(BaseCommand):
    help = "⛓️ Sync user stakes with on-chain balances"

    def handle(self, *args, **options):
        logger.info("🔁 Stake sync started...")
        if not try_acquire_lock():
            logger.warning("Another sync job is running. Exiting.")
            return

        try:
            qs = WalletConnection.objects.select_related("user").iterator()
            for conn in qs:
                userminer = UserMiner.objects.select_related("miner__plan", "token").filter(user=conn.user).first()
                if not userminer or not userminer.token or not userminer.token.contract_address:
                    logger.debug(f"[Skip] No miner or token for {conn.user.email}")
                    continue

                balance = get_onchain_balance(
                    conn.wallet_address,
                    userminer.token.contract_address,
                    userminer.token.decimals or 18
                )
                if balance is None:
                    continue

                current_stake = userminer.staked_amount or Decimal("0")
                if balance < current_stake:
                    logger.info(f"{conn.user.email} stake reduced from {current_stake} → {balance}")
                    userminer.staked_amount = balance
                    userminer.save(update_fields=["staked_amount"])

                    if balance == 0:
                        userminer.is_online = False
                        userminer.save(update_fields=["is_online"])
                        userminer.miner.is_online = False
                        userminer.miner.save(update_fields=["is_online"])
                        logger.warning(f"{conn.user.email} miner turned off (zero balance)")
                        continue

                    downgraded_plan = Plan.objects.filter(price__lte=balance).order_by("-price").first()
                    if downgraded_plan and downgraded_plan.level < userminer.miner.plan.level:
                        new_miner = userminer.miner.__class__.objects.filter(
                            plan=downgraded_plan, tokens=userminer.token
                        ).first()
                        if new_miner:
                            userminer.miner = new_miner
                            userminer.save(update_fields=["miner"])
                            logger.info(f"{conn.user.email} downgraded to plan {downgraded_plan.name}")

        finally:
            release_lock()
            logger.info("✅ Stake sync completed.")
