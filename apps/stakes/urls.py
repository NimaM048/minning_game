from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StakeViewSet,
    StakedMinerDashboardPostView,
    StakedMinerDashboardGetView,
)

router = DefaultRouter()
router.register(r'stake', StakeViewSet, basename='stake')

urlpatterns = [
    path('', include(router.urls)),
    path('staked-miner-dashboard-post/', StakedMinerDashboardPostView.as_view(), name='staked-miner-dashboard-post'),
    path('staked-miner-dashboard-get/', StakedMinerDashboardGetView.as_view(), name='staked-miner-dashboard-get'),
]
