from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MinerViewSet, MinerDetailView, get_miner_by_amount

router = DefaultRouter()
router.register(r'miners', MinerViewSet, basename='miner')

urlpatterns = [
    path('', include(router.urls)),
    path('get-miner-by-amount/', get_miner_by_amount),

    # خلاصه وضعیت مینرها
]
