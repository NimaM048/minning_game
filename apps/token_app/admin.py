from django.contrib import admin
from .models import Token

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name')
    search_fields = ('symbol', 'name')



from .models import Token, TokenSettings

@admin.register(TokenSettings)
class TokenSettingsAdmin(admin.ModelAdmin):
    list_display = ['token', 'receiver_address', 'gas_limit']
