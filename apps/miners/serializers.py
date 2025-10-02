from rest_framework import serializers
from .models import Miner
from ..plans.models import Plan
from ..plans.serializers import PlanSerializer
from ..token_app.serializers import TokenSerializer


class MinerSerializer(serializers.ModelSerializer):
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.all(), source='plan', write_only=True
    )
    tokens = TokenSerializer(many=True, read_only=True)  # اصلاح شد

    class Meta:
        model = Miner
        fields = [
            "id",
            "plan_id",
            "tokens",       # اصلاح به tokens
            "name",
            "staked_amount",
            "power",
            "is_online",
            "created_at",
        ]
        read_only_fields = ["power", "created_at"]
