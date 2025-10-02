from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmailVerification
from .models import ReferralBonusConfig

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'email', 'username', 'full_name', 'is_verified',
        'is_staff', 'is_active', 'image_display'
    )
    list_filter = ('is_verified', 'is_staff', 'is_active')
    search_fields = ('email', 'username', 'full_name')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'image_preview')

    fieldsets = (
        (None, {'fields': ('email', 'username', 'full_name', 'password')}),
        ('Profile', {'fields': ('image_preview', 'image', 'address')}),
        ('Statuses', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified')}),
        ('Referral Info', {'fields': ('referral_code', 'referred_by')}),
        ('Dates', {'fields': ('date_joined',)}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )

    def image_display(self, obj):
        return obj.image.url if obj.image else "-"
    image_display.short_description = "Profile Image"

    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" width="80" style="border-radius: 4px;" />'
        return "No Image"
    image_preview.allow_tags = True
    image_preview.short_description = "Image Preview"


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('email', 'otp_code', 'is_used', 'expires_at')
    list_filter = ('is_used',)
    search_fields = ('email', 'otp_code')
    ordering = ('-expires_at',)



@admin.register(ReferralBonusConfig)
class ReferralBonusConfigAdmin(admin.ModelAdmin):
    list_display = ('bonus_percentage', 'updated_at')
    ordering = ('-updated_at',)
    search_fields = ('bonus_percentage',)