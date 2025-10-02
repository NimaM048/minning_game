# apps/users/urls.py
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views
from .views import *

urlpatterns = [
    path("auth/email/", SendEmailCodeView.as_view()),
    path("auth/verify-code/", VerifyCodeView.as_view()),
    path("auth/set-username/", SetUsernameView.as_view()),
    path("auth/pass_login/", EmailPasswordLoginView.as_view()),
    path('request-password-reset/', RequestPasswordResetView.as_view(), name='request_password_reset'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path("auth/google/", GoogleLoginView.as_view()),
    path("me/", MeView.as_view()),
    path('me/referral-code/', views.MyReferralCodeView.as_view()),
    path('me/referrals/', views.MyReferralsListView.as_view()),
    path('referral-power-bonus/', ReferralPowerBonusView.as_view(), name='referral-power-bonus'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # path('update-profile/', views.UpdateProfileView.as_view()),
]
