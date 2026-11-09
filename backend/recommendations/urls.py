from django.urls import path

from . import views

urlpatterns = [
    path(
        "children/<int:child_id>/candidates/",
        views.ChildCandidatesView.as_view(),
        name="child-candidates",
    ),
    path(
        "children/<int:child_id>/recommendations/",
        views.ChildRecommendationsView.as_view(),
        name="child-recommendations",
    ),
    path(
        "children/<int:child_id>/activities/",
        views.ChildActivitiesView.as_view(),
        name="child-activities",
    ),
    path(
        "children/<int:child_id>/activities/<str:activity_id>/try/",
        views.TryActivityView.as_view(),
        name="child-activity-try",
    ),
    path(
        "children/<int:child_id>/saved/<str:activity_id>/",
        views.SavedActivityView.as_view(),
        name="child-saved-activity",
    ),
    path(
        "recommendations/<int:recommendation_id>/options/",
        views.RecommendationOptionsView.as_view(),
        name="recommendation-options",
    ),
]
