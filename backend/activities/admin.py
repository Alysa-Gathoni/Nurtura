from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .choices import ContentStatus
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
        "content_status",
    ]
    list_filter = [
        "content_status",
        "developmental_domain",
        "age_range",
        "difficulty_level",
        "source",
    ]
    search_fields = ["activity_id", "activity_name", "description"]
    # Status changes only through the workflow actions below.
    readonly_fields = ["content_status"]
    actions = ["submit_for_review", "publish", "return_to_draft"]

    def _transition(self, request, queryset, new_status):
        moved, skipped = 0, []
        for activity in queryset:
            try:
                activity.transition_to(new_status)
            except ValidationError as exc:
                skipped.append(exc.messages[0])
                continue
            self.log_change(
                request,
                activity,
                f"Status changed to {ContentStatus(new_status).label}.",
            )
            moved += 1
        if moved:
            self.message_user(
                request,
                f"{moved} activit{'y' if moved == 1 else 'ies'} moved to "
                f"{ContentStatus(new_status).label}.",
                messages.SUCCESS,
            )
        for reason in skipped:
            self.message_user(request, f"Skipped: {reason}", messages.WARNING)

    @admin.action(description="Submit selected activities for review")
    def submit_for_review(self, request, queryset):
        self._transition(request, queryset, ContentStatus.UNDER_REVIEW)

    @admin.action(description="Publish selected activities (must be Under Review)")
    def publish(self, request, queryset):
        self._transition(request, queryset, ContentStatus.PUBLISHED)

    @admin.action(description="Return selected activities to Draft")
    def return_to_draft(self, request, queryset):
        self._transition(request, queryset, ContentStatus.DRAFT)
