from django.contrib import admin
from django.utils.html import format_html
from django.utils.timezone import localtime
from .models import (
    Wallet, WalletTransaction, WalletConnection, WithdrawRequest,
    PendingReward, OutgoingTransaction, WithdrawalItem
)

# ------------------- Wallet -------------------
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_email', 'balance_formatted', 'total_transactions')
    search_fields = ('user__email', 'user__username')
    ordering = ('-balance',)
    list_per_page = 25
    list_select_related = ('user',)

    def user_email(self, obj):
        return format_html('<a href="/admin/users/user/{}/change/">{}</a>', obj.user.id, obj.user.email)
    user_email.short_description = 'User Email'

    def balance_formatted(self, obj):
        return f"{obj.balance:.8f}"
    balance_formatted.short_description = 'Balance'

    def total_transactions(self, obj):
        return obj.transactions.count()
    total_transactions.short_description = 'Total Transactions'

# ------------------- WalletTransaction -------------------
@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet_user_email', 'tx_type', 'amount_formatted', 'txn_hash', 'created_at_local')
    list_filter = ('tx_type', 'created_at')
    search_fields = ('wallet__user__email', 'txn_hash')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    list_per_page = 50
    list_select_related = ('wallet', 'wallet__user')

    def wallet_user_email(self, obj):
        user = obj.wallet.user
        return format_html('<a href="/admin/users/user/{}/change/">{}</a>', user.id, user.email)
    wallet_user_email.short_description = 'User Email'

    def amount_formatted(self, obj):
        color = 'green' if obj.amount >= 0 else 'red'
        return format_html('<span style="color:{};">{:.8f}</span>', color, obj.amount)
    amount_formatted.short_description = 'Amount'

    def created_at_local(self, obj):
        return localtime(obj.created_at).strftime('%Y-%m-%d %H:%M:%S')
    created_at_local.short_description = 'Created At'

# ------------------- WalletConnection -------------------
@admin.register(WalletConnection)
class WalletConnectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_email', 'wallet_address', 'provider', 'created_at_local', 'updated_at_local')
    search_fields = ('user__email', 'wallet_address')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)
    list_per_page = 25
    list_select_related = ('user',)

    def user_email(self, obj):
        return format_html('<a href="/admin/users/user/{}/change/">{}</a>', obj.user.id, obj.user.email)
    user_email.short_description = 'User Email'

    def created_at_local(self, obj):
        return localtime(obj.created_at).strftime('%Y-%m-%d %H:%M:%S')
    created_at_local.short_description = 'Created At'

    def updated_at_local(self, obj):
        return localtime(obj.updated_at).strftime('%Y-%m-%d %H:%M:%S')
    updated_at_local.short_description = 'Updated At'

# ------------------- PendingReward -------------------
@admin.register(PendingReward)
class PendingRewardAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_email', 'stake_id', 'reward_cycle_id', 'amount_formatted', 'status', 'withdrawn')
    list_filter = ('status', 'withdrawn', 'created_at')
    search_fields = ('user__email', 'stake__id', 'reward_cycle__id')
    list_editable = ('status', 'withdrawn')
    ordering = ('-created_at',)
    list_per_page = 50
    readonly_fields = ('created_at', 'claimed_at', 'processing_started')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'

    def amount_formatted(self, obj):
        return f"{obj.amount:.8f}"
    amount_formatted.short_description = 'Amount'

# ------------------- WithdrawRequest -------------------
@admin.register(WithdrawRequest)
class WithdrawRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_email', 'amount_formatted', 'colored_status', 'destination_wallet', 'created_at_local')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'destination_wallet')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    list_per_page = 50
    list_select_related = ('user',)

    actions = ['approve_requests', 'reject_requests']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'

    def amount_formatted(self, obj):
        return f"{obj.amount:.8f}"
    amount_formatted.short_description = 'Amount'

    def colored_status(self, obj):
        color_map = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
        }
        color = color_map.get(obj.status, 'black')
        return format_html('<strong><span style="color:{};">{}</span></strong>', color, obj.get_status_display())
    colored_status.short_description = 'Status'

    def created_at_local(self, obj):
        return localtime(obj.created_at).strftime('%Y-%m-%d %H:%M:%S')
    created_at_local.short_description = 'Created At'

    @admin.action(description='Approve selected withdraw requests')
    def approve_requests(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='approved')
        self.message_user(request, f"{updated} withdraw requests have been approved.")

    @admin.action(description='Reject selected withdraw requests')
    def reject_requests(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f"{updated} withdraw requests have been rejected.")

# ------------------- OutgoingTransaction -------------------
@admin.register(OutgoingTransaction)
class OutgoingTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_email', 'token_symbol', 'amount_formatted', 'status', 'destination_address', 'created_at_local')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'tx_hash', 'destination_address')
    ordering = ('-created_at',)
    list_per_page = 50
    list_select_related = ('user', 'token')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'

    def token_symbol(self, obj):
        return obj.token.symbol
    token_symbol.short_description = 'Token'

    def amount_formatted(self, obj):
        return f"{obj.amount:.8f}"
    amount_formatted.short_description = 'Amount'

    def created_at_local(self, obj):
        return localtime(obj.created_at).strftime('%Y-%m-%d %H:%M:%S')
    created_at_local.short_description = 'Created At'

# ------------------- WithdrawalItem -------------------
@admin.register(WithdrawalItem)
class WithdrawalItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'pending_reward_id', 'outgoing_tx_id', 'consumed_amount')
    search_fields = ('pending_reward__id', 'outgoing_tx__tx_hash')
    readonly_fields = ('created_at',)

    def pending_reward_id(self, obj):
        return obj.pending_reward.id
    pending_reward_id.short_description = 'PendingReward ID'

    def outgoing_tx_id(self, obj):
        return obj.outgoing_tx.id
    outgoing_tx_id.short_description = 'OutgoingTransaction ID'
