# plan/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PlanViewSet, resolve_plan_by_amount

router = DefaultRouter()
router.register(r'plans', PlanViewSet, basename='plan')

urlpatterns = [
    path('', include(router.urls)),
    path("resolve/", resolve_plan_by_amount, name="resolve_plan"),
]
