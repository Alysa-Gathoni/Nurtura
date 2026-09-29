from django.contrib import admin

from .models import DevelopmentalActivity


@admin.register(DevelopmentalActivity)
class DevelopmentalActivityAdmin(admin.ModelAdmin):
    list_display = [
        "activity_id",
        "activity_name",
        "developmental_domain",
        "age_range",
        "difficulty_level",
        "source",
    ]
    list_filter = ["developmental_domain", "age_range", "difficulty_level", "source"]
    search_fields = ["activity_id", "activity_name", "description"]
