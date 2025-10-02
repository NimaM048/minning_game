from django.urls import path
from .views import (
    # 🔐 Auth & Connection
    WalletDisconnectView,
    WalletSummaryView,
    WalletTransactionListView,
    MetaMaskNonceView,
    MetaMaskSignatureVerifyView,
    WalletConnectionStatusView,
    WalletConnectView,
    GetConnectedWalletInfoView,
    SendPublicAddressView,
    WithdrawStatusView,
    RecentTransactionsView,

    # ⚙ Cron Jobs
    RunDistributeRewardsAPIView,
    RunSyncStakeAPIView, WithdrawableAmountView, WithdrawCreateView,
)

urlpatterns = [
    # ===========================
    # 🔐 Wallet Auth & Connection
    # ===========================
    path("wallet/metamask/nonce/", MetaMaskNonceView.as_view(), name="metamask-nonce"),
    path("wallet/metamask/verify-signature/", MetaMaskSignatureVerifyView.as_view(), name="metamask-verify"),
    path("wallet/connect/", WalletConnectView.as_view(), name="wallet-connect"),
    path("wallet/get-public-address/", SendPublicAddressView.as_view(), name="wallet-get-public-address"),
    path("wallet/connected-info/", GetConnectedWalletInfoView.as_view(), name="wallet-connected-info"),

    # 🔹 مسیر اصلی متامسک
    path("wallet/metamask/disconnect/", WalletDisconnectView.as_view(), name="wallet-disconnect"),
    # 🔹 مسیر عمومی بدون ذکر provider
    path("wallet/disconnect/", WalletDisconnectView.as_view(), name="wallet-disconnect-generic"),

    path("wallet/metamask/status/", WalletConnectionStatusView.as_view(), name="wallet-connection-status"),

    # ===========================
    # 📊 Cron Jobs (Token Protected)
    # ===========================
    path("cron/distribute-rewards/", RunDistributeRewardsAPIView.as_view(), name="cron-distribute-rewards"),
    path("cron/sync-stakes/", RunSyncStakeAPIView.as_view(), name="cron-sync-stakes"),

    # ===========================
    # 📈 Wallet Summary & Transactions
    # ===========================
    path("wallet/summary/", WalletSummaryView.as_view(), name="wallet-summary"),
    path("wallet/transactions/", WalletTransactionListView.as_view(), name="wallet-transactions"),
    path('withdrawable/', WithdrawableAmountView.as_view(), name='withdrawable-amount'),
    path('withdraw/', WithdrawCreateView.as_view(), name='withdraw-create'),
    path('withdraw/status', WithdrawStatusView.as_view(), name='withdraw-status'),
    path('transactions/recent', RecentTransactionsView.as_view(), name='recent-transactions'),
]
