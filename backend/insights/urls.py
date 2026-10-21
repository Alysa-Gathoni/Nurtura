"""Administrator API for the app, under /api/admin/ (#122)."""

from django.urls import path

from activities import api as activities_api
from feedback import admin_api as feedback_api

from . import views

urlpatterns = [
    path("overview/", views.AdminOverviewView.as_view(), name="admin-api-overview"),
    path(
        "search-index/",
        views.AdminSearchIndexView.as_view(),
        name="admin-api-search-index",
    ),
    path(
        "activities/",
        activities_api.AdminActivityListView.as_view(),
        name="admin-api-activities",
    ),
    path(
        "activities/<int:pk>/",
        activities_api.AdminActivityDetailView.as_view(),
        name="admin-api-activity",
    ),
    path(
        "activities/<int:pk>/status/",
        activities_api.AdminActivityStatusView.as_view(),
        name="admin-api-activity-status",
    ),
    path(
        "choices/", activities_api.AdminChoicesView.as_view(), name="admin-api-choices"
    ),
    path(
        "feedback/",
        feedback_api.AdminFeedbackListView.as_view(),
        name="admin-api-feedback",
    ),
]
