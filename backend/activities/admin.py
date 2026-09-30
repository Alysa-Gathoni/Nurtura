from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from .choices import ContentStatus
from .models import DevelopmentalActivity


class HasSourceUrlFilter(admin.SimpleListFilter):
    title = "source link"
    parameter_name = "has_source_url"

    def lookups(self, request, model_admin):
        return [("yes", "Has link"), ("no", "No link")]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(source_url="")
        if self.value() == "no":
            return queryset.filter(source_url="")
        return queryset


@admin.register(DevelopmentalActivity)
class DevelopmentalActivityAdmin(admin.ModelAdmin):
    list_display = [
        "activity_id",
        "activity_name",
        "developmental_domain",
        "age_range",
        "difficulty_level",
        "source",
        "source_link",
        "content_status",
    ]
    list_filter = [
        "content_status",
        "source",
        HasSourceUrlFilter,
        "developmental_domain",
        "age_range",
        "difficulty_level",
    ]
    search_fields = ["activity_id", "activity_name", "description"]
    # Status changes only through the workflow actions below.
    readonly_fields = ["content_status"]
    actions = ["submit_for_review", "publish", "return_to_draft"]

    @admin.display(description="Source link", ordering="source_url")
    def source_link(self, obj):
        if not obj.source_url:
            return "-"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">open</a>', obj.source_url
        )

    # Administrators manage the activity repository (FR-13) by role, without
    # needing individual Django model permissions.
    def _is_administrator(self, request):
        user = request.user
        return user.is_active and (user.is_superuser or user.is_administrator)

    def has_module_permission(self, request):
        return self._is_administrator(request)

    def has_view_permission(self, request, obj=None):
        return self._is_administrator(request)

    def has_add_permission(self, request):
        return self._is_administrator(request)

    def has_change_permission(self, request, obj=None):
        return self._is_administrator(request)

    def has_delete_permission(self, request, obj=None):
        return self._is_administrator(request)

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
