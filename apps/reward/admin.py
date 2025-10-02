from django.contrib import admin
from django.utils.html import format_html
from django.utils.timezone import localtime
from .models import Reward, RewardCycle


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_email', 'miner_name', 'amount_formatted', 'colored_status', 'created_at_local')
    list_filter = ('status', 'created_at')
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

    def amount_formatted(self, obj):
        return f"{obj.amount:.8f}"
    amount_formatted.short_description = 'Amount'

    def colored_status(self, obj):
        color_map = {
            'paid': 'green',
            'failed': 'red',
        }
        color = color_map.get(obj.status, 'black')
        return format_html('<strong><span style="color:{};">{}</span></strong>', color, obj.get_status_display())
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'

    def created_at_local(self, obj):
        return localtime(obj.created_at).strftime('%Y-%m-%d %H:%M:%S')
    created_at_local.short_description = 'Created At'
    created_at_local.admin_order_field = 'created_at'


@admin.register(RewardCycle)
class RewardCycleAdmin(admin.ModelAdmin):
    list_display = ('id', 'stake_link', 'amount_formatted', 'due_at_local', 'unlock_time_local', 'is_paid_colored', 'completed_colored', 'created_at_local')
    list_filter = ('is_paid', 'completed', 'due_at', 'unlock_time')
    search_fields = ('stake__id', 'stake__user__email')
    readonly_fields = ('created_at',)
    ordering = ('-due_at',)
    list_per_page = 25
    list_select_related = ('stake', 'stake__user')

    def stake_link(self, obj):
        stake = obj.stake
        return format_html(
            '<a href="/admin/stakes/stake/{}/change/">Stake #{} (User: {})</a>',
            stake.id, stake.id, stake.user.email
        )
    stake_link.short_description = 'Stake'

    def amount_formatted(self, obj):
        return f"{obj.amount:.8f}"
    amount_formatted.short_description = 'Amount'

    def due_at_local(self, obj):
        return localtime(obj.due_at).strftime('%Y-%m-%d %H:%M:%S')
    due_at_local.short_description = 'Due At'
    due_at_local.admin_order_field = 'due_at'

    def unlock_time_local(self, obj):
        return localtime(obj.unlock_time).strftime('%Y-%m-%d %H:%M:%S')
    unlock_time_local.short_description = 'Unlock Time'
    unlock_time_local.admin_order_field = 'unlock_time'

    def is_paid_colored(self, obj):
        color = 'green' if obj.is_paid else 'orange'
        status = 'Paid' if obj.is_paid else 'Pending'
        return format_html('<strong><span style="color:{};">{}</span></strong>', color, status)
    is_paid_colored.short_description = 'Is Paid'
    is_paid_colored.admin_order_field = 'is_paid'

    def completed_colored(self, obj):
        color = 'green' if obj.completed else 'red'
        status = 'Completed' if obj.completed else 'Incomplete'
        return format_html('<strong><span style="color:{};">{}</span></strong>', color, status)
    completed_colored.short_description = 'Completed'
    completed_colored.admin_order_field = 'completed'

    def created_at_local(self, obj):
        return localtime(obj.created_at).strftime('%Y-%m-%d %H:%M:%S')
    created_at_local.short_description = 'Created At'
    created_at_local.admin_order_field = 'created_at'
