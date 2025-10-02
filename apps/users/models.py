# apps/users/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from rest_framework_simplejwt.tokens import RefreshToken


class UserManager(BaseUserManager):
    def create_user(self, email, username=None, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=150, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    referral_code = models.CharField(max_length=32, unique=True, null=True, blank=True)
    referred_by = models.CharField(max_length=32, null=True, blank=True)
    referral_bonus = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # فیلد جدید


    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []


    def __str__(self):
        return self.email

    def get_tokens(self):
        refresh = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        
from django.utils import timezone
from datetime import timedelta        

def default_expiry():
    return timezone.now() + timedelta(minutes=5)




class EmailVerification(models.Model):
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    otp_type = models.CharField(max_length=50, default='general')  # Add default here
    created_at = models.DateTimeField(default=timezone.now)  # اینجا default بذار

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)
        
        
        


class ReferralBonusConfig(models.Model):
    bonus_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=1)  # درصد سود برای دعوت
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Referral Bonus: {self.bonus_percentage}%"

