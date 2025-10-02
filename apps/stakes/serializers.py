# stake/serializers.py

from rest_framework import serializers
from .models import Stake
from apps.miners.models import Miner

class StakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stake
        fields = [
            "id",
            "user",
            "miner",
            "amount",
            "created_at",
            "token",
        ]
        read_only_fields = ["id", "created_at", "user"]

    def validate(self, data):
        miner = data.get('miner')
        amount = data.get('amount')

        if miner and amount:
            # اعتبارسنجی فقط اینکه کمتر از حداقل نباشه
            if amount < miner.plan.price:
                raise serializers.ValidationError(
                    f"Amount must be at least {miner.plan.price} RZ for this plan"
                )

        return data
