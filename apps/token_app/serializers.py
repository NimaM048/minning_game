# token_app/serializers.py
from rest_framework import serializers
from .models import Token

class TokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Token
        fields = ['symbol', 'name']  # فقط این دو فیلد
