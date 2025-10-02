from rest_framework import serializers
from .models import Plan
from apps.token_app.models import Token
from .utils import build_absolute_image_url


class TokenSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Token
        fields = ['id', 'symbol', 'name']


class PlanSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(read_only=True)
    tokens = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Token.objects.all()
    )
    token_details = TokenSimpleSerializer(source='tokens', many=True, read_only=True)
    name = serializers.SerializerMethodField(read_only=True)  # 👈 ویرایش شد تا از ماینر بخونه

    class Meta:
        model = Plan
        fields = [
            'id',
            'name',  # حالا این اسم، اسم ماینر اولی هست
            'level',
            'power',
            'price',
            'tokens',
            'token_details',
            'image',
            'monthly_reward_percent',
        ]

    def get_image(self, obj):
        request = self.context.get('request')
        return build_absolute_image_url(request, getattr(obj, 'image', None))

    def get_name(self, obj):
        first_miner = obj.miner_set.first()
        return first_miner.name if first_miner else obj.name
