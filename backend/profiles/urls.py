from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("children", views.ChildProfileViewSet, basename="child")
router.register(
    "reference-milestones",
    views.ReferenceMilestoneViewSet,
    basename="reference-milestone",
)

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/login/verify/", views.VerifyLoginView.as_view(), name="login-verify"),
    path("auth/login/resend/", views.ResendCodeView.as_view(), name="login-resend"),
    path(
        "auth/password-reset/",
        views.PasswordResetView.as_view(),
        name="password-reset",
    ),
    path(
        "auth/password-reset/resend/",
        views.PasswordResetResendView.as_view(),
        name="password-reset-resend",
    ),
    path(
        "auth/password-reset/verify/",
        views.PasswordResetVerifyView.as_view(),
        name="password-reset-verify",
    ),
    path(
        "auth/password-reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("auth/google/", views.GoogleSignInView.as_view(), name="google-sign-in"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/me/", views.MeView.as_view(), name="me"),
    path("auth/password/", views.ChangePasswordView.as_view(), name="change-password"),
    path(
        "auth/privacy-consent/",
        views.PrivacyConsentView.as_view(),
        name="privacy-consent",
    ),
    path("privacy-notice/", views.PrivacyNoticeView.as_view(), name="privacy-notice"),
    path("", include(router.urls)),
]
