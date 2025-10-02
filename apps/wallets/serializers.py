# wallet/serializers.py
from decimal import Decimal

from rest_framework import serializers
from .models import Wallet, WalletTransaction, WalletConnection, WithdrawRequest





class WithdrawableAmountSerializer(serializers.Serializer):
    token = serializers.CharField()
    available = serializers.DecimalField(max_digits=36, decimal_places=18)
    min_withdraw = serializers.DecimalField(max_digits=36, decimal_places=18)
    can_withdraw = serializers.BooleanField()

class WithdrawRequestSerializer(serializers.Serializer):
    token = serializers.CharField()
    amount = serializers.DecimalField(max_digits=36, decimal_places=18)
    destination = serializers.CharField(required=False, allow_blank=True)  # if not provided, use user's connected wallet

    def validate_amount(self, value: Decimal):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value













class WalletBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ["balance"]


class WalletSummarySerializer(serializers.Serializer):
    balance = serializers.DecimalField(max_digits=30, decimal_places=8)
    pending_rewards = serializers.DecimalField(max_digits=30, decimal_places=8)
    claimed_rewards = serializers.DecimalField(max_digits=30, decimal_places=8)
    daily_earning = serializers.DecimalField(max_digits=30, decimal_places=8)
    last_claimed_at = serializers.DateTimeField(allow_null=True)
    wallet_connected = serializers.BooleanField()
    wallet_address = serializers.CharField(allow_null=True)
    total_transactions = serializers.IntegerField()
    total_withdrawn = serializers.DecimalField(max_digits=30, decimal_places=8)


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ["id", "amount", "tx_type", "txn_hash", "created_at"]


class WalletConnectRequestSerializer(serializers.Serializer):
    proof = serializers.JSONField()


class WalletConnectResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    wallet_address = serializers.CharField()


class WalletConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletConnection
        fields = ["wallet_address", "provider", "updated_at"]



class WithdrawRequestCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=30, decimal_places=8)
    destination_wallet = serializers.CharField()
