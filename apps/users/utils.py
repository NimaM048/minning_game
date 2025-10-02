import random
from datetime import timedelta
from django.utils import timezone
from .models import EmailVerification
from ..utils.email import send_otp_email

import secrets


def generate_otp_code(length=5):
    return ''.join(secrets.choice('0123456789') for _ in range(length))


from django.core.mail import send_mail

def send_reset_password_email(email, reset_link):
    subject = 'Password Reset Request'
    message = f'Click the link to reset your password: {reset_link}'
    send_mail(
        subject,
        message,
        'info@coinmaining.game',  # باید با EMAIL_HOST_USER مطابقت داشته باشد
        [email],
        fail_silently=False
    )

def create_otp_for_email(email, otp_type='general'):
    # حذف OTPهای منقضی شده (نه فعلی)
    EmailVerification.objects.filter(
        email=email,
        is_used=False,
        expires_at__lt=timezone.now()
    ).delete()

    code = generate_otp_code()
    expiry = timezone.now() + timedelta(minutes=5)

    otp = EmailVerification.objects.create(
        email=email,
        otp_code=code,
        expires_at=expiry,
        otp_type=otp_type  # اضافه کردن نوع OTP
    )

    send_otp_email(email, code)

    return otp


def verify_otp(email, otp_code, otp_type='general'):
    otp = EmailVerification.objects.filter(
        email=email,
        otp_code=otp_code,
        is_used=False,
        expires_at__gt=timezone.now(),
        otp_type=otp_type  # فیلتر کردن بر اساس نوع OTP
    ).first()

    if otp:
        otp.is_used = True
        otp.save()
        return True
    return False
