from django.urls import path

from . import views

urlpatterns = [
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
]
