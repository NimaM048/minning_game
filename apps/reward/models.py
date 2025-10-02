from django.db import models
from django.conf import settings
from decimal import Decimal
from django.utils.timezone import now

class Reward(models.Model):
    STATUS_CHOICES = [
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    miner = models.ForeignKey("miners.Miner", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=30, decimal_places=8)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="paid")

    def __str__(self):
        return f"Reward {self.id} for User {self.user_id} - {self.amount}"

from django.db import models
from django.conf import settings
from decimal import Decimal
from django.utils.timezone import now



class RewardCycle(models.Model):
    stake = models.ForeignKey("stakes.Stake", on_delete=models.CASCADE)
    due_at = models.DateTimeField()
    unlock_time = models.DateTimeField()
    is_paid = models.BooleanField(default=False)
    amount = models.DecimalField(max_digits=30, decimal_places=8, default=Decimal("0"))
    created_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    reward_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("4.5"))

    def calculate_amount(self):
        stake_amount = self.stake.amount if self.stake and self.stake.amount else Decimal("0")

        # گرفتن درصد جدید از پلن فعلی
        plan = getattr(self.stake, "plan", None)
        percent = plan.monthly_reward_percent if plan and plan.monthly_reward_percent else Decimal("4.5")

        self.reward_percent = percent  # ذخیره درصد لحظه‌ای
        calculated_amount = (stake_amount * percent) / Decimal("100")
        self.amount = calculated_amount.quantize(Decimal("0.00000001"))
        self.save(update_fields=["amount", "reward_percent"])
        return self.amount

    def check_and_complete(self):
        if now() >= self.unlock_time:
            if not self.completed:
                self.completed = True
                self.save(update_fields=['completed'])
                return True
        return False

    def __str__(self):
        return f"RewardCycle {self.id} for Stake {self.stake_id} - Completed: {self.completed}"
