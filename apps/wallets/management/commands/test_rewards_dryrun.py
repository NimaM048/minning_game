from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal, ROUND_DOWN
import logging

from apps.wallets.management.commands.distribute_rewards import SERVER_WALLET, ERC20_ABI
from apps.wallets.models import PendingReward, WalletConnection
from apps.token_app.models import TokenSettings
from apps.reward.models import RewardCycle, Reward

logger = logging.getLogger(__name__)

# کلاس شبیه‌ساز Web3 و contract
class FakeContract:
    def __init__(self, token_symbol):
        self.token_symbol = token_symbol

    def functions(self):
        return self

    def balanceOf(self, address):
        # موجودی ساختگی برای سرور: 1000 توکن
        class Call:
            def call(self_inner):
                return 1000 * (10 ** 18)  # 1000 توکن با دسی‌مال 18
        return Call()

    def transfer(self, to_address, amount):
        # فقط ساختار تراکنش رو شبیه‌سازی می‌کنیم
        class TxBuilder:
            def build_transaction(self_inner, tx_params):
                return {
                    "from": tx_params.get("from"),
                    "to": to_address,
                    "amount": amount,
                    "gas": tx_params.get("gas"),
                    "gasPrice": tx_params.get("gasPrice"),
                    "nonce": tx_params.get("nonce"),
                    "chainId": tx_params.get("chainId"),
                }
        return TxBuilder()

class FakeWeb3:
    def __init__(self):
        self.eth = self
        self.gas_price = 20000000000  # 20 Gwei

    def to_checksum_address(self, addr):
        return addr.lower()

    def contract(self, address, abi):
        return FakeContract("FAKE")

    def get_balance(self, address):
        # موجودی ساختگی BNB سرور
        return 10 * (10 ** 18)  # 10 BNB

    def get_transaction_count(self, address, _pending):
        return 1

    def send_raw_transaction(self, raw_tx):
        # در حالت شبیه سازی، هیچ تراکنشی ارسال نمی‌شود
        return b"0xFAKE_TX_HASH"

    def to_hex(self, tx_hash):
        return "0xFAKE_TX_HASH"

w3 = FakeWeb3()

class Command(BaseCommand):
    help = "🧪 Dry run reward calculation and transaction preparation - Fully mocked, no blockchain connection"

    def handle(self, *args, **options):
        logger.info("🟡 Starting fully mocked dry run for rewards calculation...")

        reward_cycles = RewardCycle.objects.filter(
            is_paid=False,
            unlock_time__lte=timezone.now()
        ).select_related("stake", "stake__user", "stake__miner", "stake__token")

        for cycle in reward_cycles:
            try:
                amount = cycle.calculate_amount()
            except Exception as e:
                logger.error(f"Error calculating amount for RewardCycle {cycle.id}: {e}")
                continue

            if cycle.check_and_complete():
                logger.info(f"RewardCycle {cycle.id} marked as completed by check_and_complete()")

            pr, created = PendingReward.objects.get_or_create(
                user=cycle.stake.user,
                stake=cycle.stake,
                token=cycle.stake.token,
                reward_cycle=cycle,
                defaults={"amount": amount, "status": "pending"}
            )
            if created:
                logger.info(f"Created PendingReward {pr.id} for RewardCycle {cycle.id}")

        pending_qs = PendingReward.objects.filter(status="pending").select_related("user", "token")
        for pr in pending_qs:
            pr.status = "processing"
            pr.processing_started = timezone.now()
            pr.save(update_fields=["status", "processing_started"])

        processing_rewards = PendingReward.objects.filter(status="processing").select_related("user", "token")
        user_token_groups = {}
        for r in processing_rewards:
            key = (r.user.id, r.token.id)
            user_token_groups.setdefault(key, []).append(r)

        for (user_id, token_id), reward_list in user_token_groups.items():
            user = reward_list[0].user
            token = reward_list[0].token
            total_amount = sum((r.amount for r in reward_list), Decimal("0"))

            conn = WalletConnection.objects.filter(user=user).first()
            token_settings = TokenSettings.objects.filter(token=token).first()

            if not conn or not token_settings:
                logger.warning(f"Missing wallet or token settings for user {user.email}. Would mark rewards failed.")
                continue

            try:
                contract = w3.contract(address=w3.to_checksum_address(token.contract_address), abi=ERC20_ABI)

                server_token_balance_raw = contract.functions.balanceOf(SERVER_WALLET).call()
                server_token_balance = Decimal(server_token_balance_raw) / (Decimal(10) ** token.decimals)

                bnb_balance = Decimal(w3.get_balance(SERVER_WALLET)) / (Decimal(10) ** 18)
                estimated_gas_price = w3.gas_price
                gas_limit = int(token_settings.gas_limit or 100000)
                estimated_fee_bnb = (Decimal(estimated_gas_price) * Decimal(gas_limit)) / (10 ** 18)

                scaled_amount = (total_amount * (Decimal(10) ** token.decimals)).to_integral_value(rounding=ROUND_DOWN)

                tx = contract.functions.transfer(
                    w3.to_checksum_address(conn.wallet_address),
                    int(scaled_amount)
                ).build_transaction({
                    "from": SERVER_WALLET,
                    "nonce": w3.get_transaction_count(SERVER_WALLET, "pending"),
                    "gas": gas_limit,
                    "gasPrice": estimated_gas_price,
                    "chainId": 56,
                })

                logger.info(
                    f"[MOCKED RUN] Prepared transfer of {total_amount} {token.symbol} to {user.email} ({conn.wallet_address})"
                    f" | Server token balance: {server_token_balance}, BNB for gas: {bnb_balance} (need ~{estimated_fee_bnb})"
                    f" | TX details: {tx}"
                )

            except Exception as e:
                logger.error(f"[MOCKED RUN] Error preparing tx for {user.email}: {e}")

        logger.info("✅ Fully mocked dry run completed successfully.")
