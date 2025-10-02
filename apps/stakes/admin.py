from django.contrib import admin
from django.utils.html import format_html
from django.utils.timezone import localtime
from .models import Stake


@admin.register(Stake)
class StakeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_email', 'miner_name', 'token_name', 'amount_formatted', 'created_at_local')
    list_filter = ('token', 'created_at', 'miner')
    search_fields = ('user__email', 'miner__name', 'token__name')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    list_per_page = 50
    list_select_related = ('user', 'miner', 'token')

    def user_email(self, obj):
        return format_html('<a href="/admin/users/user/{}/change/">{}</a>', obj.user.id, obj.user.email)
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'

    def miner_name(self, obj):
        return obj.miner.name
    miner_name.short_description = 'Miner'
    miner_name.admin_order_field = 'miner__name'

    def token_name(self, obj):
        return obj.token.name
    token_name.short_description = 'Token'
    token_name.admin_order_field = 'token__name'

    def amount_formatted(self, obj):
        return f"{obj.amount:.8f}"
    amount_formatted.short_description = 'Amount'

    def created_at_local(self, obj):
        return localtime(obj.created_at).strftime('%Y-%m-%d %H:%M:%S')
    created_at_local.short_description = 'Created At'
    created_at_local.admin_order_field = 'created_at'
