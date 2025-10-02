from decimal import Decimal, ROUND_DOWN, getcontext
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
import logging

from apps.stakes.models import Stake
from apps.wallets.models import PendingReward

logger = logging.getLogger("reward")
getcontext().prec = 28

class Command(BaseCommand):
    help = "Create daily PendingReward records for all stakes with amount > 0"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            help="Calculate rewards for a specific date (YYYY-MM-DD). Default: today",
            required=False,
        )

    def handle(self, *args, **options):
        if options.get("date"):
            target_date = timezone.datetime.strptime(options["date"], "%Y-%m-%d").date()
        else:
            target_date = timezone.now().date()

        self.stdout.write(f"▶ Starting daily reward creation for {target_date}")

        # فقط فیلدهای واقعی
        stakes = Stake.objects.filter(amount__gt=0).select_related("user", "token", "miner")

        created, skipped, errors = 0, 0, 0

        for stake in stakes:
            try:
                user = stake.user
                token = stake.token

                if not token:
                    skipped += 1
                    continue

                staked_amount = Decimal(stake.amount)

   
                daily_percent = Decimal(getattr(stake, "daily_percent", 1))
                daily_reward = (staked_amount * daily_percent / Decimal("100"))

                decimals = getattr(token, "decimals", 18)
                quant = Decimal(1) / (Decimal(10) ** decimals)
                daily_reward_q = daily_reward.quantize(quant, rounding=ROUND_DOWN)

                if daily_reward_q <= 0:
                    skipped += 1
                    continue

      
                exists = PendingReward.objects.filter(
                    user=user,
                    stake=stake,
                    token=token,
                    created_at__date=target_date
                ).exists()
                if exists:
                    skipped += 1
                    continue

                with transaction.atomic():
                    pr = PendingReward.objects.create(
                        user=user,
                        stake=stake,
                        token=token,
                        amount=daily_reward_q,
                        status="pending",
                        withdrawn=False,
                    )
                    created += 1
                    logger.info(f"✅ Created PendingReward id={pr.id} user={user.id} stake={stake.id} amount={pr.amount}")

            except Exception as e:
                errors += 1
                logger.exception(f"❌ Error processing stake {stake.id}: {e}")

        self.stdout.write(
            self.style.SUCCESS(
                f"🎯 Daily rewards finished. created={created}, skipped={skipped}, errors={errors}"
            )
        )
