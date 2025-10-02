# apps/core/serializers.py

from rest_framework import serializers
from .models import ContactInfo

class ContactInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInfo
        fields = [
            'email',
            'support_phone',
            'address',
            'about_us',
            'telegram',
            'instagram',
            'twitter',
            'linkedin',
            'youtube',  # 👈 اضافه شد
        ]
