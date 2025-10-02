from django.utils.timezone import now
from datetime import datetime, timedelta
from collections import defaultdict
from decimal import Decimal
from django.db import transaction
from django.db.models.functions import TruncDate
from django.db.models import Sum, F, DecimalField
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from apps.plans.utils import build_absolute_image_url
from datetime import datetime, timedelta
from collections import defaultdict
from datetime import datetime, timedelta
from django.db.models import Sum
from django.db.models.functions import TruncDate
from collections import defaultdict
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from .models import Stake
from .serializers import StakeSerializer
from ..config.models import Config
from ..miners.models import Miner, UserMiner
from ..plans.models import Plan
from ..reward.models import Reward, RewardCycle
from ..users.models import User
from ..wallets.models import Wallet
from .models import Stake
from .serializers import StakeSerializer
from ..wallets.models import WalletConnection
from ..miners.models import Miner, UserMiner
from ..plans.models import Plan
from ..reward.models import Reward, RewardCycle
from ..users.models import User
from ..token_app.models import TokenSettings
from ..wallets.sync_stakes import get_onchain_balance


class StakeViewSet(viewsets.ModelViewSet):
    serializer_class = StakeSerializer
    queryset = Stake.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.is_anonymous:
            return Stake.objects.none()
        return Stake.objects.filter(user=user)

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        amount = serializer.validated_data['amount']
        token = serializer.validated_data.get('token')

        if not token:
            raise ValidationError("Token is required.")

        # بررسی اتصال کیف پول
        conn = WalletConnection.objects.filter(user=user).first()
        if not conn:
            raise ValidationError("Please connect a wallet before staking.")

        onchain_balance = get_onchain_balance(
            conn.wallet_address,
            token.contract_address,
            token.decimals
        )
        if onchain_balance is None:
            raise ValidationError("Could not fetch on-chain balance.")

        if onchain_balance < amount:
            raise ValidationError("Insufficient on-chain balance.")

        # مجموع استیک قبلی + جدید فقط برای همین توکن
        user_miners_with_token = UserMiner.objects.filter(user=user, token=token)
        total_staked = user_miners_with_token.aggregate(s=Sum("staked_amount"))["s"] or Decimal("0")
        new_total = total_staked + amount

        if new_total > onchain_balance:
            raise ValidationError("Total staked amount exceeds on-chain balance.")

        # پیدا کردن پلن و ماینر مناسب
        plan = Plan.objects.filter(tokens=token, price__lte=new_total).order_by('-price').first()
        if not plan:
            raise ValidationError("No suitable plan found for this amount and token.")

        miner = Miner.objects.filter(plan=plan, tokens=token).first()
        if not miner:
            raise ValidationError("No miner available for this plan and token.")

        # فقط یک UserMiner به ازای هر کاربر و توکن باید وجود داشته باشه
        userminer = UserMiner.objects.filter(user=user, token=token).first()

        if userminer:
            # آپدیت اطلاعات
            userminer.staked_amount = F('staked_amount') + amount
            userminer.miner = miner
            userminer.is_online = True
            userminer.save()
            userminer.refresh_from_db()
        else:
            # اولین بار
            userminer = UserMiner.objects.create(
                user=user,
                miner=miner,
                token=token,
                staked_amount=amount,
                is_online=True
            )

        # آپدیت staked_amount در Miner (کل این ماینر)
        miner.staked_amount = F('staked_amount') + amount
        miner.save()

        # ذخیره‌ی Stake
        stake = serializer.save(user=user, miner=miner, token=token)

        # ساخت RewardCycle بدون محاسبه و پرداخت
        RewardCycle.objects.create(
            stake=stake,
            due_at=now(),
            unlock_time=now() + timedelta(days=30),
            amount=Decimal("0"),
            is_paid=False,
            completed=False,
            reward_percent=plan.monthly_reward_percent or Decimal("4.5")
        )

        # اینجا هیچ پاداشی ساخته نمی‌شود
        return stake

    @action(detail=False, methods=['get'], url_path='summary', permission_classes=[AllowAny])
    def summary(self, request):
        total_users = User.objects.filter(is_active=True).count()
        total_staked = Miner.objects.aggregate(total=Sum('staked_amount'))['total'] or 0
        online_miners = UserMiner.objects.filter(is_online=True).count()
        total_rewards_paid = Reward.objects.aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            "total_users": total_users,
            "total_staked": total_staked,
            "online_miners": online_miners,
            "total_rewards_paid": total_rewards_paid
        })

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        stake = self.get_object()
        reward_cycle = RewardCycle.objects.filter(stake=stake).first()

        if reward_cycle and not reward_cycle.completed:
            raise ValidationError("This stake has not completed its 30-day reward cycle.")

        miner = stake.miner
        userminer = UserMiner.objects.filter(user=request.user, miner=miner).first()

        if not userminer:
            raise ValidationError("UserMiner not found.")

        # کاهش مقدار استیک
        userminer.staked_amount -= stake.amount
        userminer.save()

        miner.staked_amount -= stake.amount
        miner.save()

        stake.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)






def generate_earnings_graph(user, miner, max_days=60):
    base_date = timezone.now().date()
    start_date = base_date - timedelta(days=max_days - 1)

    # جمع درآمد روزانه واقعی از جدول Reward
    rewards = (
        Reward.objects.filter(user=user, miner=miner, created_at__date__gte=start_date)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(total=Sum("amount"))
        .order_by("date")
    )

    earnings_by_date = {item["date"]: float(item["total"]) for item in rewards}

    earnings_graph = {"7": [], "30": [], "60": []}

    for i in range(max_days):
        date = start_date + timedelta(days=i)
        earning = round(earnings_by_date.get(date, 0.0), 8)

        if i >= max_days - 7:
            earnings_graph["7"].append({"date": date.isoformat(), "earning": earning})
        if i >= max_days - 30:
            earnings_graph["30"].append({"date": date.isoformat(), "earning": earning})
        earnings_graph["60"].append({"date": date.isoformat(), "earning": earning})

    return earnings_graph



class StakedMinerDashboardGetView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        stake = UserMiner.objects.filter(user=user).select_related("miner", "token").first()

        if not stake:
            return Response({"detail": "No staked miner found for this user."}, status=404)

        miner = stake.miner
        total_power = miner.power if miner.is_online else 0
        total_staked = stake.staked_amount

        miners_data = [{
            "id": miner.id,
            "token": stake.miner.token.id if stake.miner.token else None,
            "name": miner.name,
            "staked_amount": str(stake.staked_amount),
            "power": miner.power,
            "is_online": miner.is_online,
            "created_at": miner.created_at.isoformat() + "Z",
            "user_id": user.id
        }]

        # گراف پاداش
        earnings_graph = generate_earnings_graph(user, miner)

        return Response({
            "miner_power": total_power,
            "daily_earning": 0, 
            "staked_tokens": total_staked,
            "total_miners": 1,
            "active_miners": 1 if miner.is_online else 0,
            "miners": miners_data,
            "earnings_graph": earnings_graph
        })



import bisect
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response




class StakedMinerDashboardPostView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_image_url(self, miner, request):
       
        try:
            # اگر فیلد image وجود داشت (مثلاً ImageField)
            img = getattr(miner, "image", None)
            if img and hasattr(img, "url"):
                return request.build_absolute_uri(img.url)
        except Exception:
            pass

        # اگر پلن تصویر داشت (optional)
        try:
            plan_img = getattr(miner.plan, "image", None)
            if plan_img and hasattr(plan_img, "url"):
                return request.build_absolute_uri(plan_img.url)
        except Exception:
            pass

        # fallback: می‌توانید آدرس استاتیک دلخواه برگردانید یا خالی بگذارید
        return ""


    def _get_miner_for_level(self, level, token=None):
        """
        تلاش برای گرفتن Miner مربوط به level. ابتدا سعی می‌کنیم miner
        که آن level دارد و token هم سازگار باشد برگردانیم. در غیر اینصورت
        miner بدون فیلتر token برمی‌گردد (اگر موجود باشد).
        """
        qs = Miner.objects.filter(plan__level=level)
        if token is not None:
            qst = qs.filter(tokens=token)
            if qst.exists():
                return qst.first()
        return qs.first()

    def _build_three_levels(self, current_level):
      
        levels = list(Plan.objects.order_by('level').values_list('level', flat=True).distinct())
        if not levels:
            return []

        # محل قرارگیری current_level در لیست (insertion point)
        idx = bisect.bisect_left(levels, current_level)

        prev_idx = max(0, idx - 1)
        cur_idx = min(idx, len(levels) - 1)
        next_idx = min(idx + 1, len(levels) - 1)

       
        chosen = [levels[prev_idx], levels[cur_idx], levels[next_idx]]
        return chosen


    def post(self, request):
        data = request.data
        user = request.user
        user_id = data.get('user_id')
        miner_id = data.get('miner_id')

        if user_id and int(user_id) != user.id and not user.is_staff:
            return Response({"detail": "Permission denied."}, status=403)

        if not user_id or not miner_id:
            return Response({"detail": "user_id and miner_id are required."}, status=400)

        target_user_id = int(user_id)

        # گرفتن userminer های مربوط به کاربر و این ماینر
        stakes = UserMiner.objects.filter(user_id=target_user_id, miner_id=miner_id).select_related("miner", "token")
        if not stakes.exists():
            return Response({"detail": "No staked miner found for this user and miner."}, status=404)

        # اگر چند رکورد داشتیم، از اولین استفاده می‌کنیم به‌عنوان مرجع
        userminer = stakes[0]
        current_miner = userminer.miner
        current_plan = current_miner.plan
        current_level = getattr(current_plan, "level", None)
        token = userminer.token or (current_miner.tokens.first() if current_miner.tokens.exists() else None)

        # محاسبه‌ی آمار کلی (مثل قبلاً)
        total_power = 0
        total_staked = 0
        miners_data = []

        for stake in stakes:
            miner = stake.miner
   
            total_power += miner.power
            total_staked += stake.staked_amount

            miners_data.append({
                "id": miner.id,
                "tokens": [t.id for t in miner.tokens.all()],
                "name": miner.name,
                "staked_amount": str(stake.staked_amount),
                "power": miner.power,
                "is_online": stake.is_online,   # وضعیت آنلاین را از UserMiner بگیریم
                "created_at": miner.created_at.isoformat() + "Z",
                "user_id": target_user_id
            })


        miner_suggestions = []
        if current_level is not None:
            levels_to_show = self._build_three_levels(current_level)  # سه level (ممکنه تکراری)
            for lvl in levels_to_show:
                m = self._get_miner_for_level(lvl, token=token)
                if not m:
                    # اگر miner ای برای آن level و token پیدا نشد، تلاش می‌کنیم بدون token
                    m = self._get_miner_for_level(lvl, token=None)
                if m:
                    miner_suggestions.append({
                        "id": m.id,
                        "name": m.name,
                        "image": self._get_image_url(m, request),
                        "active": (m.id == current_miner.id),
                        "plan_level": m.plan.level if m.plan else None,
                    })
                else:
                    # filler در صورتی که واقعا miners کم باشه (میتونید frontend handle کنه)
                    miner_suggestions.append({
                        "id": None,
                        "name": None,
                        "image": "",
                        "active": False,
                        "plan_level": lvl
                    })
        else:
            # اگر current_level تعریف نشده بود، ارسال سه ماینر اول از لیست
            top_miners = Miner.objects.all()[:3]
            for m in top_miners:
                miner_suggestions.append({
                    "id": m.id,
                    "name": m.name,
                    "image": self._get_image_url(m, request),
                    "active": (m.id == current_miner.id),
                    "plan_level": m.plan.level if m.plan else None,
                })
            # پر کردن تا سه‌تایی در صورت نیاز
            while len(miner_suggestions) < 3:
                miner_suggestions.append({"id": None, "name": None, "image": "", "active": False, "plan_level": None})

        # گراف و محاسبات درآمد
        earnings_graph = generate_earnings_graph(user=user, miner=current_miner)
        last_daily_earning = earnings_graph["7"][-1]["earning"] if earnings_graph["7"] else 0

        return Response({
            "miner_power": total_power,
            "daily_earning": last_daily_earning,
            "staked_tokens": total_staked,
            "total_miners": len(miners_data),
            "active_miners": sum(1 for m in miners_data if m['is_online']),
            "miners": miners_data,
            "earnings_graph": earnings_graph,
            "image": build_absolute_image_url(request, getattr(m.plan, 'image', None)),
            "miner_suggestions": miner_suggestions 
        })