from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.plans.utils import build_absolute_image_url

from .models import Miner, UserMiner
from .serializers import MinerSerializer
from apps.plans.models import Plan
from apps.token_app.models import Token


class MinerViewSet(viewsets.ModelViewSet):
    queryset = Miner.objects.all()
    serializer_class = MinerSerializer

    def perform_create(self, serializer):
        plan = serializer.validated_data.get('plan')
        power = plan.power if plan else 0
        serializer.save(power=power)

    def perform_update(self, serializer):
        plan = serializer.validated_data.get('plan')
        power = plan.power if plan else serializer.instance.power
        serializer.save(power=power)

    @action(detail=False, methods=['get'], url_path='me', permission_classes=[IsAuthenticated])
    def my_miners(self, request):
        user = request.user
        user_miners = UserMiner.objects.filter(user=user).select_related('miner', 'token')
        data = []

        for um in user_miners:
            miner = um.miner
            data.append({
                "id": miner.id,
                "tokens": [t.id for t in miner.tokens.all()],
                "name": miner.name,
                "staked_amount": str(um.staked_amount),
                "power": miner.power,  # ← قدرت ماینر
                "user_power": getattr(um, "power", miner.power),  # ← اگر قدرت اختصاصی برای یوزر تعریف شده
                "is_online": um.is_online,
                "created_at": miner.created_at.isoformat() + "Z",
                'image': build_absolute_image_url(request, getattr(miner.plan, 'image', None)),
            })

        return Response(data)


class MinerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, miner_id):
        user = request.user
        try:
            if user.is_staff:
                miner = Miner.objects.get(id=miner_id)
            else:
                userminer = UserMiner.objects.get(user=user, miner_id=miner_id)
                miner = userminer.miner
        except Miner.DoesNotExist:
            raise PermissionDenied("You do not have permission to access this miner.")
        except UserMiner.DoesNotExist:
            raise PermissionDenied("You do not have permission to access this miner.")

        serializer = MinerSerializer(miner, context={'request': request})
        return Response(serializer.data, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_miner_by_amount(request):
    
    try:
        amount = float(request.data.get("amount"))
        token_id = int(request.data.get("token"))  # 👈 اصلاح‌شده: token به جای token_id
    except (TypeError, ValueError):
        return Response({"detail": "Invalid amount or token"}, status=400)

    if amount <= 0:
        return Response({"detail": "Amount must be greater than 0"}, status=400)

    try:
        token = Token.objects.get(id=token_id)
    except Token.DoesNotExist:
        return Response({"detail": "Token not found"}, status=404)

    # پیدا کردن پلن مناسب بر اساس مقدار و توکن
    plan = Plan.objects.filter(price__lte=amount, tokens=token).order_by('-price').first()
    if not plan:
        return Response({"detail": "No suitable plan found"}, status=404)

    # پیدا کردن ماینر مربوط به پلن و توکن
    miner = Miner.objects.filter(plan=plan, tokens=token).first()
    if not miner:
        return Response({"detail": "No miner found for selected plan and token."}, status=404)

    # ساخت خروجی
    data = {
        "id": miner.id,
        "tokens": [t.id for t in miner.tokens.all()],
        "name": miner.name,
        "staked_amount": str(miner.staked_amount),
        "power": miner.power,
        "is_online": miner.is_online,
        "created_at": miner.created_at.isoformat() + "Z",
        'image': build_absolute_image_url(request, getattr(miner.plan, 'image', None)),
    }

    return Response(data)
