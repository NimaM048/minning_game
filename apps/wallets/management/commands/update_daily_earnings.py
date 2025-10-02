# management/commands/update_daily_earnings.py

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from apps.miners.models import UserMiner
from apps.reward.models import Reward


class Command(BaseCommand):
    help = "Calculates and creates daily reward records for all active miners."

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.now().date()
        active_stakes = (
            UserMiner.objects
            .filter(is_online=True, staked_amount__gt=0)
            .select_related("user", "miner", "miner__plan")
        )

        if not active_stakes.exists():
            self.stdout.write(
                self.style.WARNING("هیچ استیک فعالی برای محاسبه سود روزانه پیدا نشد.")
            )
            return

        rewards_to_create = []
        for stake in active_stakes:
            already_exists = Reward.objects.filter(
                user=stake.user,
                miner=stake.miner,
                created_at__date=today
            ).exists()

            if already_exists:
                continue

            # محاسبه سود روزانه
            plan = stake.miner.plan
            if not plan or not plan.monthly_reward_percent:
                continue

            staked_amount = stake.staked_amount
            monthly_percent = plan.monthly_reward_percent

            daily_reward = (
                staked_amount * (monthly_percent / Decimal("100"))
            ) / Decimal("30")

            if daily_reward > 0:
                rewards_to_create.append(
                    Reward(
                        user=stake.user,
                        miner=stake.miner,
                        amount=daily_reward,
                        status="paid"  # "paid" یعنی سود این روز واریز شده
                    )
                )

        if rewards_to_create:
            Reward.objects.bulk_create(rewards_to_create)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {len(rewards_to_create)} رکورد سود روزانه با موفقیت ثبت شد."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "برای استیک‌های فعال، سود امروز قبلاً محاسبه شده است."
                )
            )
