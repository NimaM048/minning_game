# plan/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from .models import Plan
from .serializers import PlanSerializer
from apps.token_app.models import Token  

class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer


    def destroy(self, request, *args, **kwargs):
        plan = self.get_object()
        plan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resolve_plan_by_amount(request):
    try:
        amount = float(request.data.get("amount"))
        token_symbol = request.data.get("token")
    except (TypeError, ValueError):
        return Response({"detail": "Invalid amount or token"}, status=400)

    if amount <= 0:
        return Response({"detail": "Amount must be greater than 0"}, status=400)

    if not token_symbol:
        return Response({"detail": "Token is required"}, status=400)

    token = Token.objects.filter(symbol__iexact=token_symbol).first()
    if not token:
        return Response({"detail": "Invalid token"}, status=400)

    matched_plan = Plan.objects.filter(tokens=token, price__lte=amount).order_by('-price').first()

    if not matched_plan:
        return Response({"detail": "No suitable plan found"}, status=404)

    return Response(PlanSerializer(matched_plan, context={'request': request}).data)
