# apps/users/serializers.py

from rest_framework import serializers
from .models import User


class EmailRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField()

class UsernameUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(min_length=3)
    password = serializers.CharField(required=False, allow_blank=True, min_length=6)
    referred_by = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    full_name = serializers.CharField(required=False, allow_blank=True)
    image = serializers.ImageField(required=False)



class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()



class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=16)
    password = serializers.CharField(min_length=6)






class GoogleAuthSerializer(serializers.Serializer):
    access_token = serializers.CharField()


class TokenSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.CharField(default="bearer")


class UserResponseSerializer(serializers.ModelSerializer):
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'full_name',
            'is_active',
            'is_verified',
            'image',
            'address',
            'is_admin',   # ← این باید اضافه بشه
        ]
        read_only_fields = ['email']

    def get_is_admin(self, obj):
        return obj.is_staff



class ReferralCodeSerializer(serializers.Serializer):
    referral_code = serializers.CharField()


class ReferralUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'username']
