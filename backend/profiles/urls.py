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
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/me/", views.MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
