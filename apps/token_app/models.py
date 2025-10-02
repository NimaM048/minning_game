# token_app/models.py

from django.db import models

class Token(models.Model):
    symbol = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)

    # 👇 این دو فیلد جدید
    contract_address = models.CharField(max_length=100, blank=True, null=True)
    decimals = models.IntegerField(default=18)

    def __str__(self):
        return self.symbol

# apps/token_app/models.py

class TokenSettings(models.Model):
    token = models.OneToOneField(Token, on_delete=models.CASCADE, related_name="settings")
    receiver_address = models.CharField(max_length=255)
    gas_limit = models.PositiveIntegerField(default=21000)

    def __str__(self):
        return f"Settings for {self.token.symbol}"
