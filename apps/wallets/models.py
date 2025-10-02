# wallet/models.py

from django.db import models
from django.conf import settings
from decimal import Decimal

from apps.reward.models import RewardCycle
from apps.stakes.models import Stake
from apps.token_app.models import Token


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=30, decimal_places=8, default=Decimal("0"))

    def __str__(self):
        return f"Wallet of {self.user.email} - Balance: {self.balance}"



class NonceReservation(models.Model):
    """
    Simple DB-backed nonce manager for the server wallet.
    One row per address (we use server wallet only).
    We keep next_nonce which is the next nonce to use.
    """
    address = models.CharField(max_length=255, unique=True)
    next_nonce = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.address} -> {self.next_nonce}"

class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=30, decimal_places=8)  # مثبت=شارژ، منفی=پرداخت
    tx_type = models.CharField(max_length=50)  # charge, payment, reward, ...
    txn_hash = models.CharField(max_length=255, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tx_type} {self.amount} for {self.wallet.user.email}"


class WalletConnection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet_connections")
    wallet_address = models.CharField(max_length=255, unique=True)
    provider = models.CharField(max_length=100, default="tonkeeper")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"WalletConnection {self.wallet_address} for {self.user.email}"


class WithdrawRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="withdraw_requests")
    amount = models.DecimalField(max_digits=30, decimal_places=8)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    destination_wallet = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"WithdrawRequest {self.id} by {self.user.email} - {self.status}"




class WithdrawalItem(models.Model):
    pending_reward = models.ForeignKey(
        "PendingReward", on_delete=models.CASCADE, related_name="withdrawal_items"
    )
    outgoing_tx = models.ForeignKey(
        "OutgoingTransaction", on_delete=models.CASCADE, related_name="items"
    )
    consumed_amount = models.DecimalField(max_digits=36, decimal_places=18, default=Decimal("0"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["outgoing_tx"]),
            models.Index(fields=["pending_reward"]),
        ]

    def __str__(self):
        return f"{self.pending_reward_id} -> {self.consumed_amount}"


from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class PendingReward(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('claimed', 'Claimed'),
        ('failed', 'Failed'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pending_rewards')
    stake = models.ForeignKey('stakes.Stake', on_delete=models.CASCADE, related_name='pending_rewards')
    token = models.ForeignKey('token_app.Token', on_delete=models.CASCADE)
    reward_cycle = models.ForeignKey('reward.RewardCycle', on_delete=models.CASCADE, null=True, blank=True)

    amount = models.DecimalField(max_digits=36, decimal_places=18)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    processing_started = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)

 
    withdrawn = models.BooleanField(default=False)  # whether this pending reward has been withdrawn to user
    withdraw_tx = models.ForeignKey(
        'OutgoingTransaction', null=True, blank=True, on_delete=models.SET_NULL, related_name='withdrawn_rewards'
    )

    class Meta:
        unique_together = ("user", "stake", "reward_cycle")

    def __str__(self):
        return f"{self.user} - {self.amount} ({self.status})"



class WalletAuthNonce(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nonce = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now=True)
    
    
    
    
class OutgoingTransaction(models.Model):
    STATUS_CHOICES = [
        ("sending", "Sending"), 
        ("sent", "Sent"),      
        ("failed", "Failed"),   
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="outgoing_transactions"
    )
    token = models.ForeignKey(
        "token_app.Token",
        on_delete=models.CASCADE,
        related_name="outgoing_transactions"
    )
    token_contract = models.CharField(max_length=255)
    amount = models.DecimalField(
        max_digits=36, decimal_places=18, default=Decimal("0")
    )
    tx_hash = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="sending"
    )
    details = models.JSONField(blank=True, null=True)  # برای ذخیره پیام خطا یا متادیتای تراکنش
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    destination_address = models.CharField(max_length=255, null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["tx_hash"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.amount} {self.token.symbol} ({self.status})"





