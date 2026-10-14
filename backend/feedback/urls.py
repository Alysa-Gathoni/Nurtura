from django.urls import path

from . import views

urlpatterns = [
    path(
        "recommendations/<int:recommendation_id>/completion/",
        views.RecommendationCompletionView.as_view(),
        name="recommendation-completion",
    ),
]
