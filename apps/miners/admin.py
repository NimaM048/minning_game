from django.contrib import admin
from django.utils.html import format_html
from django.utils.timezone import localtime
from .models import Miner, UserMiner

@admin.register(Miner)
class MinerAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'plan_name', 'token_list',
        'staked_amount_formatted', 'power', 'colored_is_online', 'created_at_local'
    )
    list_filter = ('tokens', 'plan', 'is_online', 'created_at')
    search_fields = ('name', 'plan__name', 'tokens__symbol')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    list_per_page = 25
    list_select_related = ('plan',)

    def plan_name(self, obj):
        return obj.plan.name
    plan_name.short_description = 'Plan'
    plan_name.admin_order_field = 'plan__name'

    def token_list(self, obj):
        return ", ".join([t.symbol for t in obj.tokens.all()])
    token_list.short_description = 'Tokens'

    def staked_amount_formatted(self, obj):
        return f"{obj.staked_amount:.8f}"
    staked_amount_formatted.short_description = 'Staked Amount'

    def colored_is_online(self, obj):
        color = 'green' if obj.is_online else 'red'
        status = 'Online' if obj.is_online else 'Offline'
        return format_html('<strong><span style="color:{};">{}</span></strong>', color, status)
    colored_is_online.short_description = 'Status'
    colored_is_online.admin_order_field = 'is_online'

    def created_at_local(self, obj):
        return localtime(obj.created_at).strftime('%Y-%m-%d %H:%M:%S')
    created_at_local.short_description = 'Created At'
    created_at_local.admin_order_field = 'created_at'


@admin.register(UserMiner)
class UserMinerAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_email', 'miner_name',
        'staked_amount_formatted', 'colored_is_online', 'created_at_local'
    )
    list_filter = ('is_online', 'created_at')
    search_fields = ('user__email', 'user__username', 'miner__name')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    list_per_page = 25
    list_select_related = ('user', 'miner')

    def user_email(self, obj):
        return format_html(
            '<a href="/admin/users/user/{}/change/">{}</a>', obj.user.id, obj.user.email
        )
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'

    def miner_name(self, obj):
        return obj.miner.name
    miner_name.short_description = 'Miner'
    miner_name.admin_order_field = 'miner__name'

    def staked_amount_formatted(self, obj):
        return f"{obj.staked_amount:.8f}"
    staked_amount_formatted.short_description = 'Staked Amount'

    def colored_is_online(self, obj):
        color = 'green' if obj.is_online else 'red'
        status = 'Online' if obj.is_online else 'Offline'
        return format_html('<strong><span style="color:{};">{}</span></strong>', color, status)
    colored_is_online.short_description = 'Status'
    colored_is_online.admin_order_field = 'is_online'

    def created_at_local(self, obj):
        return localtime(obj.created_at).strftime('%Y-%m-%d %H:%M:%S')
    created_at_local.short_description = 'Created At'
    created_at_local.admin_order_field = 'created_at'
