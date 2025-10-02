from django.contrib import admin
from django.urls import path, include

# 🔧 اضافات مورد نیاز
from django.contrib.auth import logout
from django.shortcuts import redirect

# Swagger imports
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions


schema_view = get_schema_view(
    openapi.Info(
        title="Mining API",
        default_version='v1',
        description="Mining backend API with JWT Auth",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# 🧭 تابع logout ریدایرکت
def admin_logout_redirect_view(request):
    logout(request)
    return redirect("https://coinmaining.game/log-out-admin")

urlpatterns = [
    path('admin/logout/', admin_logout_redirect_view, name='custom_admin_logout'),  # ✅ ریدایرکت
    path('admin/', admin.site.urls),  # ⚠️ این مسیر باید بعد از logout بیاد

    # سایر مسیرهای API
    path('api/users/', include('apps.users.urls')),
    path('api/miners/', include('apps.miners.urls')),
    path('api/plans/', include('apps.plans.urls')),
    path('api/stakes/', include('apps.stakes.urls')),
    path('api/wallets/', include('apps.wallets.urls')),
    path('api/about_us/', include('apps.about_us.urls')),
    path("user/admin", include("apps.users.urls")),
    path('api/api/', include('apps.api.urls')),

    # Swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
