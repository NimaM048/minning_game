from django.db import models
from django.conf import settings
from apps.miners.models import Miner
from apps.token_app.models import Token


class Stake(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stakes',
        verbose_name='User'
    )
    miner = models.ForeignKey(
        Miner,
        on_delete=models.CASCADE,
        related_name='stakes',
        verbose_name='Miner'
    )
    token = models.ForeignKey(
        Token,
        on_delete=models.CASCADE,
        verbose_name='Token',
        related_name='stakes'  
    )
    amount = models.DecimalField(
        max_digits=30,
        decimal_places=8,
        verbose_name='Amount'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stake'
        verbose_name_plural = 'Stakes'

    def __str__(self):
        return f"Stake #{self.id} by {self.user.email}"
