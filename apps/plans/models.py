# plans/models.py

from django.db import models
from apps.token_app.models import Token

# plans/models.py

class Plan(models.Model):
    name = models.CharField(max_length=100, verbose_name="Plan Name")
    level = models.PositiveIntegerField(verbose_name="Level")
    power = models.FloatField(verbose_name="Power")
    price = models.FloatField(verbose_name="Price")
    
    tokens = models.ManyToManyField(
        Token,
        related_name='plans',
        verbose_name="Tokens"
    )

    image = models.ImageField(
        upload_to='plans/',
        verbose_name="Plan Image",
        null=True,
        blank=True,
        help_text="Upload an image representing this plan"
    )

    monthly_reward_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=4.5,
        help_text="درصد سود ماهانه به صورت درصد (مثلاً 4.5)"
    )

    class Meta:
        ordering = ['level', 'name']
        verbose_name = "Plan"
        verbose_name_plural = "Plans"

    def __str__(self):
        return f"{self.name} (Level {self.level})"
