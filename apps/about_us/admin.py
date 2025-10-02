from django.contrib import admin
from .models import ContactInfo

@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = (
        'support_phone',
        'email',
        'address',
        'telegram',
        'instagram',
        'twitter',
        'linkedin',
        'youtube',  # ✅ اضافه شد
    )
    readonly_fields = ()
    search_fields = ('support_phone', 'email', 'address')

    fieldsets = (
        (None, {
            'fields': (
                'support_phone',
                'email',
                'address',
                'about_us',
            )
        }),
        ('Social Media Links', {
            'fields': (
                'telegram',
                'instagram',
                'twitter',
                'linkedin',
                'youtube',  # ✅ اضافه شد
            ),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request):
        return not ContactInfo.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
