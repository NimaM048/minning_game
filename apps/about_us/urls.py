# apps/core/urls.py

from django.urls import path
from .views import ContactInfoView

urlpatterns = [
    path("contact-info/", ContactInfoView.as_view(), name="contact-info"),
]
