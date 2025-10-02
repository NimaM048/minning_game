# apps/miners/models.py

from django.db import models
from django.conf import settings
from apps.plans.models import Plan
from apps.token_app.models import Token


class Miner(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    tokens = models.ManyToManyField(Token, related_name='miners')  # پشتیبانی از چند توکن مثل Plan
    name = models.CharField(max_length=255, default="Miner")
    staked_amount = models.DecimalField(max_digits=30, decimal_places=8, default=0)
    power = models.FloatField(default=0)
    is_online = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def auto_upgrade_plan(self):
        """
        اگر staked_amount به پلن بالاتری برسد، ماینر را به پلن جدید ارتقا بده.
        """
        total = self.staked_amount
        current_plan_level = self.plan.level if self.plan else 0

        next_plan = Plan.objects.filter(price__lte=total).order_by("-price").first()

        if next_plan and next_plan.level > current_plan_level:
            new_miner = Miner.objects.filter(plan=next_plan).first()
            if new_miner:
                self.plan = new_miner.plan
                self.name = new_miner.name
                self.power = new_miner.power
                self.staked_amount = new_miner.staked_amount
                self.is_online = new_miner.is_online
                self.save()

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Miner"
        verbose_name_plural = "Miners"

    def __str__(self):
        return f"{self.name} (Plan: {self.plan.name})"


class UserMiner(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_miners')
    miner = models.ForeignKey(Miner, on_delete=models.CASCADE)
    staked_amount = models.DecimalField(max_digits=30, decimal_places=8, default=0)
    is_online = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    token = models.ForeignKey(Token, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "User Miner"
        verbose_name_plural = "User Miners"

    def __str__(self):
        return f"UserMiner #{self.id} for {self.user.email}"
