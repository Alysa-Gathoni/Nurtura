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
]
