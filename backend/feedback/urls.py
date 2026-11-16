from django.urls import path

from . import views

urlpatterns = [
    path(
        "children/<int:child_id>/activities-done/",
        views.ActivitiesDoneView.as_view(),
        name="child-activities-done",
    ),
    path(
        "recommendations/<int:recommendation_id>/completion/",
        views.RecommendationCompletionView.as_view(),
        name="recommendation-completion",
    ),
    path(
        "recommendations/<int:recommendation_id>/feedback/",
        views.RecommendationFeedbackView.as_view(),
        name="recommendation-feedback",
    ),
    path(
        "recommendations/<int:recommendation_id>/observable/",
        views.ObservableSkillsView.as_view(),
        name="recommendation-observable",
    ),
]
