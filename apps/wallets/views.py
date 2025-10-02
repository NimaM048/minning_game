# wallet/views.py
from decimal import Decimal, ROUND_DOWN
from decimal import Decimal
from uuid import uuid4
from django.utils.timezone import now
import logging
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db import transaction
from eth_account import Account
from eth_account.messages import encode_defunct
from .models import Wallet, WalletTransaction, WalletConnection, WithdrawRequest, PendingReward, WalletAuthNonce, \
    WithdrawalItem, NonceReservation
from .serializers import (
    WalletBalanceSerializer,
    WalletTransactionSerializer,
    WalletConnectRequestSerializer,
    WalletConnectResponseSerializer,
    WalletConnectionSerializer,
    WithdrawRequestSerializer,
    WithdrawRequestCreateSerializer, WalletSummarySerializer,
)
from apps.core.tonconnect import verify_ton_proof, verify_ton_transaction
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.core.management import call_command

import logging
from django.conf import settings
from django.core.management import call_command
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .sync_stakes import get_onchain_balance
from ..token_app.models import Token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from decimal import Decimal
from datetime import date
from .models import Wallet, WithdrawRequest, WalletConnection
from django.db import models
from django.db.models import F
from decimal import Decimal
from django.db import transaction, connection
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from web3 import Web3

from .models import PendingReward, OutgoingTransaction, WalletConnection
from .serializers import WithdrawableAmountSerializer, WithdrawRequestSerializer
from .utils import get_web3, get_erc20_contract, to_wei, from_wei, WAIT_RECEIPT_TIMEOUT, \
    build_and_send_erc20_transfer
User = get_user_model()


class MetaMaskSignatureVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        message = request.data.get("message")
        signature = request.data.get("signature")
        address = request.data.get("address")

        if not all([message, signature, address]):
            raise ValidationError("message, signature, and address are required")

        try:
            message_encoded = encode_defunct(text=message)
            recovered_address = Account.recover_message(message_encoded, signature=signature)
        except Exception as e:
            raise ValidationError(f"Signature verification failed: {str(e)}")

        if recovered_address.lower() != address.lower():
            raise ValidationError("Signature does not match address")

        return Response({"message": "Wallet verified", "address": recovered_address})


class WalletConnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        address = request.data.get("address")
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()

        if not address:
            raise ValidationError({"detail": "Wallet address is required"})

        # تشخیص provider از User-Agent
        if "trust" in user_agent:
            provider = "trustwallet"
        elif "safepal" in user_agent:
            provider = "safepal"
        elif "metamask" in user_agent:
            provider = "metamask"
        else:
            provider = "other"

        existing = WalletConnection.objects.filter(wallet_address=address).first()
        if existing and existing.user != request.user:
            raise ValidationError({"detail": "This wallet is already connected to another user"})

        WalletConnection.objects.filter(user=request.user).delete()

        WalletConnection.objects.create(
            user=request.user,
            wallet_address=address,
            provider=provider,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        return Response({
            "message": f"{provider.capitalize()} wallet connected successfully",
            "wallet_address": address,
            "provider": provider
        })


logger = logging.getLogger(__name__)

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from web3 import Web3
from .models import WalletConnection
from apps.token_app.models import Token
from .sync_stakes import get_onchain_balance


class GetConnectedWalletInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        provider = request.query_params.get("provider")
        qs = WalletConnection.objects.filter(user=request.user)

        if provider:
            provider = provider.lower()
            if provider not in ["metamask", "trustwallet", "safepal", "unknown"]:
                provider = "unknown"
            qs = qs.filter(provider=provider)

        connections = qs.all()
        if not connections.exists():
            return Response({"connected": False, "connections": []})

        data = []
        for conn in connections:
            wallet_address = conn.wallet_address

            if not Web3.is_address(wallet_address):
                data.append({
                    "wallet_address": wallet_address,
                    "provider": conn.provider,
                    "connected": False,
                    "error": "Invalid wallet address format"
                })
                continue

            rz_balance, mgc_balance = None, None

            try:
                rz_token = Token.objects.filter(symbol="RZ").first()
                mgc_token = Token.objects.filter(symbol="MGC").first()

                if rz_token and rz_token.contract_address and rz_token.decimals is not None:
                    rz_balance = get_onchain_balance(wallet_address, rz_token.contract_address, rz_token.decimals)

                if mgc_token and mgc_token.contract_address and mgc_token.decimals is not None:
                    mgc_balance = get_onchain_balance(wallet_address, mgc_token.contract_address, mgc_token.decimals)

            except Exception as e:
                logger.error(f"[Blockchain Error] Failed to get balances for {wallet_address}: {str(e)}")
                data.append({
                    "wallet_address": wallet_address,
                    "provider": conn.provider,
                    "connected": True,
                    "onchain_balances": {
                        "RZ": None,
                        "MGC": None
                    },
                    "error": str(e),
                    "created_at": conn.created_at,
                    "updated_at": conn.updated_at,
                })
                continue

            data.append({
                "wallet_address": wallet_address,
                "provider": conn.provider,
                "connected": True,
                "onchain_balances": {
                    "RZ": float(rz_balance) if rz_balance is not None else None,
                    "MGC": float(mgc_balance) if mgc_balance is not None else None,
                },
                "created_at": conn.created_at,
                "updated_at": conn.updated_at,
            })

        return Response({
            "connected": True,
            "connections": data,
        })


class SendPublicAddressView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        provider = request.data.get("provider", "").lower()
        wallet_address = request.data.get("wallet_address", "")

        if not wallet_address:
            raise ValidationError({"detail": "Wallet address is required"})

        if provider not in ["metamask", "trustwallet", "safepal"]:
            raise ValidationError({"detail": "Invalid wallet provider"})

        return Response({
            "message": f"{provider.capitalize()} wallet address received successfully",
            "wallet_address": wallet_address,
            "provider": provider,
        })





class BaseCronAPIView(APIView):
    """
    Base view for triggering cronjob management commands securely.
    """
    permission_classes = []

    command_name = None

    def get(self, request):
        print(f"CRON CALLED: {self.command_name}")  # لاگ چاپ در کنسول
        token = request.query_params.get("token")

        if token != getattr(settings, "CRONJOB_SECRET_TOKEN", None):
            logger.warning(f"Unauthorized access attempt to {self.command_name or 'unknown'} cron.")
            return Response({"detail": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        if not self.command_name:
            return Response({"detail": "No command specified."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            logger.info(f"🚀 Starting cronjob: {self.command_name}")
            call_command(self.command_name)
            logger.info(f"✅ Finished cronjob: {self.command_name}")
            return Response({"detail": f"✅ {self.command_name} executed successfully."}, status=200)
        except Exception as e:
            logger.exception(f"❌ Error running {self.command_name}: {e}")
            return Response({"detail": f"⛔ Error: {str(e)}"}, status=500)


class RunDistributeRewardsAPIView(BaseCronAPIView):
    command_name = "distribute_rewards"


class RunSyncStakeAPIView(BaseCronAPIView):
    command_name = "sync_stakes"


class MetaMaskNonceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        nonce = str(uuid4())
        WalletAuthNonce.objects.update_or_create(user=request.user, defaults={"nonce": nonce})
        return Response({"nonce": nonce})


class WalletDisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        WalletConnection.objects.filter(user=request.user).delete()
        return Response({"message": "Wallet disconnected"})


class WalletConnectionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        connections = WalletConnection.objects.filter(user=request.user)
        data = [
            {
                "provider": conn.provider,
                "wallet_address": conn.wallet_address,
                "connected": True,
                "updated_at": conn.updated_at,
            }
            for conn in connections
        ]
        return Response(data)


class WalletTransactionListView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WalletTransaction.objects.filter(wallet__user=self.request.user).order_by('-created_at')


class WalletSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        provider = request.query_params.get("provider", "metamask").lower()
        wallet = Wallet.objects.filter(user=user).first()

        conn = WalletConnection.objects.filter(user=user, provider=provider).first()
        wallet_connected = bool(conn)
        wallet_address = conn.wallet_address if conn else None

        token = Token.objects.filter(symbol="RZ").first()
        on_chain_balance = None
        if conn and token and token.contract_address:
            on_chain_balance = get_onchain_balance(
                conn.wallet_address,
                token.contract_address,
                token.decimals or 18
            )

        pending_rewards = PendingReward.objects.filter(user=user, status="pending").aggregate(
            total=models.Sum("amount"))["total"] or Decimal("0")

        claimed_qs = PendingReward.objects.filter(user=user, status="claimed")
        claimed_rewards = claimed_qs.aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
        last_claimed_at = claimed_qs.aggregate(last=models.Max("claimed_at"))["last"]

        today = date.today()
        daily_earning = claimed_qs.filter(claimed_at__date=today).aggregate(
            total=models.Sum("amount"))["total"] or Decimal("0")

        total_tx = WalletTransaction.objects.filter(wallet=wallet).count() if wallet else 0
        total_withdrawn = WithdrawRequest.objects.filter(user=user, status="approved").aggregate(
            total=models.Sum("amount"))["total"] or Decimal("0")

        data = {
            "balance": wallet.balance if wallet else 0,
            "pending_rewards": pending_rewards,
            "claimed_rewards": claimed_rewards,
            "daily_earning": daily_earning,
            "last_claimed_at": last_claimed_at,
            "wallet_connected": wallet_connected,
            "wallet_address": wallet_address,
            "total_transactions": total_tx,
            "total_withdrawn": total_withdrawn,
            "on_chain_balance": float(on_chain_balance) if on_chain_balance is not None else None,
        }

        return Response(WalletSummarySerializer(data).data)


class WithdrawableAmountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        results = []

        tokens = Token.objects.filter(symbol__in=list(MIN_WITHDRAWALS.keys()))
        for token in tokens:
            s = PendingReward.objects.filter(user=user, token=token, status='claimed', withdrawn=False).aggregate(
                total=Sum('amount'))
            available = s['total'] or Decimal("0")
            min_with = MIN_WITHDRAWALS.get(token.symbol, Decimal("0"))
            can_withdraw = available >= Decimal(min_with)
            results.append({
                "token": token.symbol,
                "available": available,
                "min_withdraw": Decimal(min_with),
                "can_withdraw": can_withdraw
            })

        serializer = WithdrawableAmountSerializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)




ADVISORY_LOCK_KEY_BASE = getattr(settings, "ADVISORY_LOCK_KEY", 4242424242)
MIN_WITHDRAWALS = getattr(settings, "MIN_WITHDRAWALS", {"MGC": Decimal("100"), "RZ": Decimal("40")})
SERVER_WALLET_ADDRESS = getattr(settings, "SERVER_WALLET_ADDRESS", None)
SERVER_WALLET_PRIVATE_KEY = getattr(settings, "SERVER_WALLET_PRIVATE_KEY", None)
BSC_CHAIN_ID = getattr(settings, "BSC_CHAIN_ID", 56)
REWARD_WAIT_RECEIPT_TIMEOUT = getattr(settings, "REWARD_WAIT_RECEIPT_TIMEOUT", 180)

from django.conf import settings

logger = logging.getLogger("wallet")

MIN_WITHDRAWALS = getattr(settings, "MIN_WITHDRAWALS", {"MGC": Decimal("100"), "RZ": Decimal("40")})


def sanitize_receipt(receipt, w3):
    r = {}
    if hasattr(receipt, "transactionHash") and receipt.transactionHash is not None:
        r["transactionHash"] = w3.toHex(receipt.transactionHash)
    r["status"] = int(getattr(receipt, "status", 0) or 0)
    if getattr(receipt, "blockNumber", None) is not None:
        r["blockNumber"] = int(receipt.blockNumber)
    if getattr(receipt, "gasUsed", None) is not None:
        r["gasUsed"] = int(receipt.gasUsed)
    return r


class WithdrawCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def _validate_amount_precision(self, amount: Decimal, decimals: int):
        q = Decimal(1) / (Decimal(10) ** decimals)
        quantized = amount.quantize(q, rounding=ROUND_DOWN)
        if quantized != amount:
            raise ValueError(f"Amount has precision beyond token.decimals={decimals}")

    def _reserve_nonce(self, w3, server_address: str):

        from django.db import transaction
        with transaction.atomic():
            nr, created = NonceReservation.objects.select_for_update().get_or_create(address=server_address)
            if created or nr.next_nonce == 0:
                # initialize from chain
                onchain = w3.eth.get_transaction_count(server_address)
                nr.next_nonce = onchain
            reserved = nr.next_nonce
            nr.next_nonce = nr.next_nonce + 1
            nr.save(update_fields=["next_nonce", "updated_at"])
            return int(reserved)

    def post(self, request):
        serializer = WithdrawRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_symbol = serializer.validated_data['token'].upper()
        amount: Decimal = serializer.validated_data['amount']
        destination = serializer.validated_data.get('destination')

        token = get_object_or_404(Token, symbol=token_symbol)

        # precision check
        try:
            self._validate_amount_precision(amount, token.decimals)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        min_allowed = MIN_WITHDRAWALS.get(token_symbol, Decimal("0"))
        if amount < min_allowed:
            return Response({"detail": f"Minimum withdraw for {token_symbol} is {min_allowed}"},
                            status=status.HTTP_400_BAD_REQUEST)

        if not destination:
            conn = WalletConnection.objects.filter(user=request.user).first()
            if not conn:
                return Response({"detail": "No connected wallet found; provide destination parameter"},
                                status=status.HTTP_400_BAD_REQUEST)
            destination = conn.wallet_address

        try:
            w3 = get_web3()
            destination = w3.toChecksumAddress(destination)
            server_addr = w3.toChecksumAddress(SERVER_WALLET_ADDRESS)
        except Exception as e:
            logger.exception("RPC or address invalid")
            return Response({"detail": "Invalid or unreachable destination / RPC"}, status=status.HTTP_400_BAD_REQUEST)

        # Stage A: reserve pending rewards + create outgoing tx + reserve nonce
        with transaction.atomic():
            available_qs = PendingReward.objects.select_for_update().filter(
                user=request.user, token=token, status='claimed', withdrawn=False
            ).order_by('id')

            tot = available_qs.aggregate(total=Sum('amount'))['total'] or Decimal("0")
            if amount > tot:
                return Response({"detail": "Requested amount exceeds available withdrawable amount"},
                                status=status.HTTP_400_BAD_REQUEST)

            gathered = []
            acc = Decimal("0")
            for pr in available_qs:
                gathered.append(pr)
                acc += pr.amount
                if acc >= amount:
                    break

            now = timezone.now()
            PendingReward.objects.filter(id__in=[p.id for p in gathered]).update(status='processing',
                                                                                 processing_started=now)

            # create outgoing tx record (destination stored)
            out_tx = OutgoingTransaction.objects.create(
                user=request.user,
                token=token,
                token_contract=token.contract_address,
                amount=amount,
                destination_address=destination,
                status="sending",
            )

            # reserve a nonce (DB-backed) - this is short and atomic
            reserved_nonce = self._reserve_nonce(w3, server_addr)

            # commit transaction here - we have reserved rewards and nonce
        # end with transaction.atomic()

        logger.info("Reserved nonce %s for outgoing_tx=%s user=%s", reserved_nonce, out_tx.id, request.user.id)

        # Stage B: perform on-chain send (outside DB tx and without holding locks)
        token_contract = get_erc20_contract(w3, token.contract_address)
        amount_wei = to_wei(amount, token.decimals)

        # quick on-chain balances check (not protected, but ok)
        try:
            token_balance_int = token_contract.functions.balanceOf(server_addr).call()
            token_balance = from_wei(token_balance_int, token.decimals)
        except Exception as e:
            logger.exception("Failed to read server token balance")
            # revert processing marks and mark out_tx failed
            with transaction.atomic():
                PendingReward.objects.filter(id__in=[p.id for p in gathered], status='processing').update(
                    status='claimed', processing_started=None)
                out_tx.status = "failed"
                out_tx.details = {"error": "failed_token_balance_check", "exc": str(e)}
                out_tx.save(update_fields=["status", "details", "updated_at"])
            return Response({"detail": "Token balance check failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if Decimal(token_balance) < amount:
            with transaction.atomic():
                PendingReward.objects.filter(id__in=[p.id for p in gathered], status='processing').update(
                    status='claimed', processing_started=None)
                out_tx.status = "failed"
                out_tx.details = {"error": "insufficient_server_token_balance"}
                out_tx.save(update_fields=["status", "details", "updated_at"])
            return Response({"detail": "Server token balance insufficient"}, status=status.HTTP_400_BAD_REQUEST)

        # estimate gas (with fallback)
        try:
            est_gas = token_contract.functions.transfer(destination, amount_wei).estimateGas({'from': server_addr})
        except Exception as e:
            logger.warning("estimateGas failed, using fallback: %s", e)
            est_gas = int(getattr(settings, "GAS_FALLBACK", 150000))

        gas_price = w3.eth.gas_price
        gas_cost_native_wei = est_gas * gas_price
        server_native = w3.eth.get_balance(server_addr)
        if server_native < gas_cost_native_wei:
            with transaction.atomic():
                PendingReward.objects.filter(id__in=[p.id for p in gathered], status='processing').update(
                    status='claimed', processing_started=None)
                out_tx.status = "failed"
                out_tx.details = {"error": "insufficient_native_gas"}
                out_tx.save(update_fields=["status", "details", "updated_at"])
            return Response({"detail": "Server native balance insufficient for gas"},
                            status=status.HTTP_400_BAD_REQUEST)

        # send tx using reserved nonce
        try:
            tx_hash, receipt = build_and_send_erc20_transfer(
                token_contract=token_contract,
                server_address=SERVER_WALLET_ADDRESS,
                server_private_key=SERVER_WALLET_PRIVATE_KEY,
                to_address=destination,
                amount_wei=amount_wei,
                nonce=reserved_nonce,
                gas_limit=est_gas + 20000,
                gas_price_wei=gas_price,
                chain_id=BSC_CHAIN_ID,
                wait_timeout=WAIT_RECEIPT_TIMEOUT,
            )
        except Exception as e:
            logger.exception("Failed to send tx for out_tx=%s", out_tx.id)
            with transaction.atomic():
                PendingReward.objects.filter(id__in=[p.id for p in gathered], status='processing').update(
                    status='claimed', processing_started=None)
                out_tx.status = "failed"
                out_tx.details = {"error": "send_failed", "exc": str(e)}
                out_tx.save(update_fields=["status", "details", "updated_at"])
            return Response({"detail": "Transaction failed to send", "error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Stage C: finalize DB updates in short atomic block
        receipt_json = sanitize_receipt(receipt, w3)
        with transaction.atomic():
            out_tx.status = "sent" if receipt_json.get("status", 0) == 1 else "failed"
            out_tx.tx_hash = tx_hash
            out_tx.details = {"receipt": receipt_json}
            out_tx.save()

            # consume pending rewards (create WithdrawalItem entries)
            amount_left = amount
            for pr in gathered:
                pr_ref = PendingReward.objects.select_for_update().get(pk=pr.pk)
                if pr_ref.amount <= amount_left:
                    consumed = pr_ref.amount
                    pr_ref.withdrawn = True
                    pr_ref.withdraw_tx = out_tx
                    pr_ref.status = 'claimed'
                    pr_ref.save(update_fields=["withdrawn", "withdraw_tx", "status"])
                    WithdrawalItem.objects.create(pending_reward=pr_ref, outgoing_tx=out_tx, consumed_amount=consumed)
                    amount_left -= consumed
                else:
                    consumed = amount_left
                    remaining = pr_ref.amount - consumed
                    pr_ref.amount = remaining
                    pr_ref.save(update_fields=["amount"])
                    WithdrawalItem.objects.create(pending_reward=pr_ref, outgoing_tx=out_tx, consumed_amount=consumed)
                    amount_left = Decimal("0")
                if amount_left <= 0:
                    break

        if receipt_json.get("status", 0) != 1:
            logger.warning("Transaction reverted on chain for out_tx=%s tx=%s", out_tx.id, out_tx.tx_hash)
            return Response({"detail": "Transaction reverted on chain", "tx_hash": out_tx.tx_hash},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"detail": "Withdrawal processed", "tx_hash": out_tx.tx_hash, "status": out_tx.status},
                        status=status.HTTP_200_OK)


class WithdrawStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get("limit", 10))
        offset = int(request.query_params.get("offset", 0))

        txs = (OutgoingTransaction.objects
               .filter(user=request.user)
               .order_by("-created_at")[offset:offset + limit])

        results = []
        for tx in txs:
            results.append({
                "id": str(tx.id),
                "token": tx.token.symbol,
                "amount": str(tx.amount),
                "tx_hash": tx.tx_hash,
                "status": tx.status,
                "created_at": tx.created_at.isoformat(),
                "updated_at": tx.updated_at.isoformat(),
                "details": tx.details or {}
            })

        return Response(results, status=status.HTTP_200_OK)


class RecentTransactionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get("limit", 5))


        withdrawals = (
            OutgoingTransaction.objects
            .filter(user=request.user)
            .annotate(token=F("token__symbol"))
            .values("id", "token", "amount", "created_at")
        )
        for w in withdrawals:
            w["type"] = "withdrawal"
            w["amount"] = f"-{Decimal(w['amount']):.2f}"
            w["color"] = "red"


        deposits = (
            PendingReward.objects
            .filter(user=request.user, status="claimed")
            .annotate(token=F("token__symbol"))
            .values("id", "token", "amount", "created_at")
        )
        for d in deposits:
            d["type"] = "deposit"
            d["amount"] = f"+{Decimal(d['amount']):.2f}"
            d["color"] = "green"


        all_txs = list(withdrawals) + list(deposits)


        all_txs.sort(key=lambda x: x["created_at"], reverse=True)


        results = [
            {
                "id": tx["id"],
                "type": tx["type"],  # deposit یا withdrawal
                "token": tx["token"],
                "amount": tx["amount"],
                "color": tx["color"],
                "created_at": tx["created_at"].isoformat(),
            }
            for tx in all_txs[:limit]
        ]

        return Response(results, status=status.HTTP_200_OK)