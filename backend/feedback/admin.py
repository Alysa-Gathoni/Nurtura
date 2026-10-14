from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import Truncator

from .models import CompletedActivity, Feedback


class ReviewOnlyAdmin(admin.ModelAdmin):
    """Administrators review what caregivers recorded; nobody edits it here.

    Rows are shown against the activity they concern. The child and the
    caregiver aren't shown (data minimisation): the review is about the
    activity, not the family.
    """

    list_select_related = ["recommendation__activity"]

    def _is_administrator(self, request):
        user = request.user
        return user.is_active and (user.is_superuser or user.is_administrator)

    def has_module_permission(self, request):
        return self._is_administrator(request)

    def has_view_permission(self, request, obj=None):
        return self._is_administrator(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(
        description="Activity ID", ordering="recommendation__activity__activity_id"
    )
    def activity_id(self, obj):
        return obj.recommendation.activity.activity_id

    @admin.display(
        description="Activity", ordering="recommendation__activity__activity_name"
    )
    def activity(self, obj):
        activity = obj.recommendation.activity
        url = reverse(
            "admin:activities_developmentalactivity_change", args=[activity.pk]
        )
        return format_html('<a href="{}">{}</a>', url, activity.activity_name)

    @admin.display(
        description="Area", ordering="recommendation__activity__developmental_domain"
    )
    def area(self, obj):
        return obj.recommendation.activity.get_developmental_domain_display()


@admin.register(Feedback)
class FeedbackAdmin(ReviewOnlyAdmin):
    list_display = [
        "date_submitted",
        "activity_id",
        "activity",
        "area",
        "stars",
        "comment_excerpt",
        "completion",
    ]
    list_filter = ["rating", "recommendation__activity__developmental_domain"]
    search_fields = [
        "recommendation__activity__activity_id",
        "recommendation__activity__activity_name",
        "comment",
    ]
    date_hierarchy = "date_submitted"
    list_select_related = ["recommendation__activity", "recommendation__completion"]
    fields = [
        "activity_id",
        "activity",
        "area",
        "rating",
        "comment",
        "completion",
        "date_submitted",
    ]
    readonly_fields = fields

    @admin.display(description="Rating", ordering="rating")
    def stars(self, obj):
        return f"{'★' * obj.rating}{'☆' * (5 - obj.rating)} ({obj.rating}/5)"

    @admin.display(description="Comment")
    def comment_excerpt(self, obj):
        return Truncator(obj.comment).chars(80) or "-"

    @admin.display(description="Done?")
    def completion(self, obj):
        done = getattr(obj.recommendation, "completion", None)
        return done.get_status_display() if done else "Not marked"


@admin.register(CompletedActivity)
class CompletedActivityAdmin(ReviewOnlyAdmin):
    list_display = ["completion_date", "activity_id", "activity", "area", "status"]
    list_filter = ["status", "recommendation__activity__developmental_domain"]
    search_fields = [
        "recommendation__activity__activity_id",
        "recommendation__activity__activity_name",
    ]
    date_hierarchy = "completion_date"
    fields = ["activity_id", "activity", "area", "status", "completion_date"]
    readonly_fields = fields
