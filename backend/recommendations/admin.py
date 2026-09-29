from django.contrib import admin

from .models import Recommendation


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = [
        "child",
        "activity",
        "similarity_score",
        "ranking_score",
        "date_generated",
    ]
    list_filter = ["activity__developmental_domain"]
    search_fields = ["child__name", "activity__activity_name"]
