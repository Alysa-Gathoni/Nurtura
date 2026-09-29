from django.contrib import admin

from .models import CompletedActivity, Feedback


@admin.register(CompletedActivity)
class CompletedActivityAdmin(admin.ModelAdmin):
    list_display = ["recommendation", "status", "completion_date"]
    list_filter = ["status"]


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ["recommendation", "rating", "date_submitted"]
    list_filter = ["rating"]
