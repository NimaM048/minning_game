from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from .serializers import *
from .utils import create_otp_for_email, verify_otp
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
import uuid
import httpx
from .utils import create_otp_for_email, verify_otp, send_reset_password_email
from pydantic import validate_email
from datetime import timedelta
from .models import EmailVerification
from drf_yasg import openapi
from django.db.models import Sum
from django.utils import timezone
from django.db.models import Sum
from ..config.models import Config
from ..core.utils.jwt import create_access_token
from ..miners.models import Miner
from django.core.exceptions import ValidationError as DjangoValidationError
from ..core.utils.jwt import create_access_token
from .models import EmailVerification, ReferralBonusConfig
import secrets
from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import EmailVerification, User
from .serializers import EmailRequestSerializer, ResetPasswordSerializer
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status


User = get_user_model()


class SendEmailCodeView(APIView):
    @swagger_auto_schema(request_body=EmailRequestSerializer)
    def post(self, request):
        serializer = EmailRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        # اعتبارسنجی ایمیل
        try:
            validate_email(email)
        except DjangoValidationError:
            return Response({"detail": "Invalid email address."}, status=400)

        user = User.objects.filter(email=email).first()

        # اگر کاربر وجود دارد
        if user:
            # اگر هنوز یوزرنیم و پسورد ست نکرده
            if user.username.startswith("temp_") or not user.has_usable_password():
                recent_otp = EmailVerification.objects.filter(
                    email=email,
                    created_at__gt=timezone.now() - timedelta(seconds=10)
                ).first()
                if recent_otp:
                    return Response({"detail": "OTP recently sent. Please wait."}, status=429)

                create_otp_for_email(email)
                return Response({
                    "detail": "You haven't completed registration. OTP sent again.",
                    "need_password": False,
                    "need_username": True
                })

            # اگر کاربر ثبت‌نام کامل دارد
            return Response({
                "detail": "User already exists. Proceed to password login.",
                "need_password": True,
                "need_username": False
            }, status=200)

        # اگر کاربر جدید است
        recent_otp = EmailVerification.objects.filter(
            email=email,
            created_at__gt=timezone.now() - timedelta(seconds=10)
        ).first()
        if recent_otp:
            return Response({"detail": "OTP recently sent. Please wait."}, status=429)

        create_otp_for_email(email)
        return Response({
            "detail": "OTP code sent to your email.",
            "need_password": False,
            "need_username": True
        })


class VerifyCodeView(APIView):
    @swagger_auto_schema(request_body=VerifyOTPRequestSerializer)
    def post(self, request):
        serializer = VerifyOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        code = serializer.validated_data['otp_code']

        if not verify_otp(email, code):
            return Response({"detail": "Invalid or expired verification code."}, status=400)

        user = User.objects.filter(email=email).first()

        # اگر کاربر جدید است، ایجاد کاربر با یوزرنیم موقت
        if not user:
            temp_username = f"temp_{uuid.uuid4().hex[:12]}"
            user = User.objects.create(
                email=email,
                username=temp_username,
                is_verified=True,
                referral_code=str(uuid.uuid4())[:8]
            )
        elif not user.is_verified:
            user.is_verified = True
            user.save()

        tokens = user.get_tokens()
        need_username = user.username.startswith("temp_") or not user.has_usable_password()

        return Response({
            "access_token": tokens["access"],
            "refresh_token": tokens["refresh"],
            "token_type": "bearer",
            "need_username": need_username,
            "message": (
                "Verification successful. Please set a username and password."
                if need_username else
                "Login successful."
            )
        })





def update_referral_bonus(user):

    bonus_config = ReferralBonusConfig.objects.first()
    if bonus_config:

        user.referral_bonus += bonus_config.bonus_percentage
        user.save()








class SetUsernameView(APIView):
    @swagger_auto_schema(
        manual_parameters=[],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'username'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, format='email'),
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING, minLength=6),
                'referred_by': openapi.Schema(type=openapi.TYPE_STRING),
                'full_name': openapi.Schema(type=openapi.TYPE_STRING),
                'image': openapi.Schema(type=openapi.TYPE_FILE), 
            },
        ),
        consumes=['multipart/form-data'],  
    )
    def post(self, request):
        serializer = UsernameUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        email = data['email']
        username = data['username']
        password = data.get('password')
        referred_by = data.get('referred_by')
        full_name = data.get('full_name', '')
        image = data.get('image', None)

        user = User.objects.filter(email=email).first()
        referral_user = User.objects.filter(referral_code=referred_by).first() if referred_by else None

        if not user:
            return Response({"detail": "User not found. Please verify email again."}, status=404)

        if User.objects.filter(username=username).exclude(email=email).exists():
            return Response({"detail": "Username already taken."}, status=400)

        user.username = username
        user.full_name = full_name

        if password:
            if len(password) < 6:
                return Response({"detail": "Password too short. Minimum 6 characters required."}, status=400)
            user.set_password(password)

        if image:
            user.image = image

        if referred_by:
            user.referred_by = referred_by

        user.save()

        if referral_user:
            update_referral_bonus(referral_user)

        tokens = user.get_tokens()

        return Response({
            "user": UserResponseSerializer(user).data,
            "access_token": tokens["access"],
            "refresh_token": tokens["refresh"],
            "token_type": "bearer",
        })


class EmailPasswordLoginView(APIView):
    @swagger_auto_schema(request_body=LoginSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"detail": "User not found."}, status=404)

        if not user.has_usable_password():
            return Response({"detail": "You haven't set your password yet. Please complete registration."}, status=403)

        if not user.check_password(password):
            return Response({"detail": "Incorrect password."}, status=401)

        if not user.is_verified:
            return Response({"detail": "Please verify your email first."}, status=403)

        if not user.is_active:
            return Response({"detail": "Your account is inactive."}, status=403)

        tokens = user.get_tokens()
        return Response({
            "access_token": tokens["access"],
            "refresh_token": tokens["refresh"],
            "token_type": "bearer",
            "user": UserResponseSerializer(user).data
        })

        
        
        



def generate_reset_token(length=16):
    return secrets.token_urlsafe(length)[:16]  # تولید توکن 16 کاراکتری امن


def create_reset_token_for_email(email, token_type='reset_password'):
    # حذف توکن‌های منقضی شده
    EmailVerification.objects.filter(
        email=email,
        is_used=False,
        expires_at__lt=timezone.now()
    ).delete()

    token = generate_reset_token()
    expiry = timezone.now() + timedelta(hours=1) 

    reset_token = EmailVerification.objects.create(
        email=email,
        otp_code=token,
        expires_at=expiry,
        otp_type=token_type
    )

 
    reset_link = f"https://coinmaining.game/reset-password?token={token}"
    send_reset_password_email(email, reset_link)

    return reset_token


def verify_reset_token(token, token_type='reset_password'):
    token_obj = EmailVerification.objects.filter(
        otp_code=token,
        is_used=False,
        expires_at__gt=timezone.now(),
        otp_type=token_type
    ).first()

    if token_obj:
        token_obj.is_used = True
        token_obj.save()
        return token_obj.email 
    return None


class RequestPasswordResetView(APIView):
    @swagger_auto_schema(
        request_body=EmailRequestSerializer,
        responses={
            200: "Password reset link sent to your email.",
            404: "User not found.",
            429: "Reset link recently sent. Please wait a moment before requesting again."
        }
    )
    def post(self, request):
        serializer = EmailRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"detail": "User not found."}, status=404)

        # جلوگیری از اسپم درخواست لینک
        recent_token = EmailVerification.objects.filter(
            email=email,
            otp_type='reset_password',
            expires_at__gt=timezone.now() - timedelta(seconds=120)
        ).first()
        if recent_token:
            return Response({"detail": "Reset link recently sent. Please wait a moment before requesting again."}, status=429)

        create_reset_token_for_email(email, token_type='reset_password')

        return Response({"detail": "Password reset link sent to your email."}, status=200)


class ResetPasswordView(APIView):
    @swagger_auto_schema(
        request_body=ResetPasswordSerializer,
        responses={
            200: "Password reset successfully.",
            400: "Invalid or expired reset token.",
            404: "User not found."
        }
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        new_password = serializer.validated_data['password']

        # تأیید توکن و دریافت ایمیل کاربر
        email = verify_reset_token(token, token_type='reset_password')
        if not email:
            return Response({"detail": "Invalid or expired reset token."}, status=400)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"detail": "User not found."}, status=404)

        user.set_password(new_password)
        user.save()

        return Response({"detail": "Password reset successfully."}, status=200)













        
        
        
        
        
    
class GoogleLoginView(APIView):
    async def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['access_token']

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            )

        if response.status_code != 200:
            return Response({"detail": "توکن گوگل معتبر نیست"}, status=401)

        data = response.json()
        email = data.get("email")

        if not email:
            return Response({"detail": "ایمیل یافت نشد"}, status=400)

        user = User.objects.filter(email=email).first()
        if not user:
            user = User.objects.create(
                email=email,
                username=email.split("@")[0] + str(uuid.uuid4())[:4],
                referral_code=str(uuid.uuid4())[:8],
                is_verified=True
            )
            user.set_password("")
            user.save()

        token = create_access_token({"sub": user.email})
        return Response({"access_token": token, "token_type": "bearer"})






# class UpdateProfileView(APIView):
#
#     permission_classes = [IsAuthenticated]
#     parser_classes = [MultiPartParser, FormParser]  # اگر عکس پروفایل باشه
#
#     @swagger_auto_schema(request_body=UserResponseSerializer)
#     def put(self, request):
#         serializer = UserResponseSerializer(request.user, data=request.data, partial=True)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data)




from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

class LogoutView(APIView):
   

    def post(self, request):
       
        return Response({"detail": "Logout successful"}, status=200)




class MeView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):

        return Response(UserResponseSerializer(request.user).data)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.users.models import User
from apps.users.serializers import ReferralCodeSerializer, ReferralUserSerializer

class MyReferralCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.referral_code:
            return Response({"detail": "Referral code not generated"}, status=500)

        # گرفتن درصد سود از تنظیمات
        config = ReferralBonusConfig.objects.first()
        bonus_percentage = float(config.bonus_percentage) if config else 0.0

        return Response({
            "referral_code": request.user.referral_code,
            "bonus_percentage": bonus_percentage
        })



class MyReferralsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        referred_users = User.objects.filter(referred_by=request.user.referral_code)
        serializer = ReferralUserSerializer(referred_users, many=True)
        referred_count = referred_users.count()
        mining_boost = Miner.objects.filter(user__in=referred_users).aggregate(
            total=Sum('power')
        )['total'] or 0

        # مقدار درصد سود دعوت از تنظیمات
        config = ReferralBonusConfig.objects.first()
        bonus_percentage = float(config.bonus_percentage) if config else 0.0

        return Response({
            "referrals": serializer.data,
            "referred_count": referred_count,
            "mining_boost": mining_boost,
            "bonus_percentage": bonus_percentage,  # 🎯 اضافه شد
        })


# apps/config/views.py


class ReferralPowerBonusView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        config = ReferralBonusConfig.objects.first()
        if config:
            return Response({"power_bonus_percentage": config.bonus_percentage})
        return Response({"detail": "Power bonus percentage not set"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request):
        power_bonus = request.data.get("power_bonus_percentage")
        if not power_bonus:
            return Response({"detail": "Power bonus percentage is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            power_bonus = float(power_bonus)
        except ValueError:
            return Response({"detail": "Invalid percentage value"}, status=status.HTTP_400_BAD_REQUEST)

        # ذخیره درصد جدید
        config, created = ReferralBonusConfig.objects.get_or_create(key="referral_power_bonus")
        config.bonus_percentage = power_bonus
        config.save()

        return Response({"detail": "Power bonus updated successfully"})

