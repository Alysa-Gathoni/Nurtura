from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin

from .models import ChildProfile, DevelopmentalMilestone, ReferenceMilestone, User


@admin.register(User)
class NurturaUserAdmin(UserAdmin):
    list_display = ["username", "email", "role", "is_active", "is_superuser"]
    list_filter = ["role", "is_active", "is_superuser"]
    # is_staff is derived from role in User.save(), so it isn't editable here.
    fieldsets = [
        (None, {"fields": ["username", "password"]}),
        ("Personal info", {"fields": ["first_name", "last_name", "email"]}),
        ("Role", {"fields": ["role"]}),
        (
            "Permissions",
            {"fields": ["is_active", "is_superuser", "groups", "user_permissions"]},
        ),
        ("Important dates", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["username", "email", "role", "password1", "password2"],
            },
        ),
    ]


class DevelopmentalMilestoneInline(admin.TabularInline):
    model = DevelopmentalMilestone
    extra = 0
    autocomplete_fields = ["reference"]


@admin.register(ChildProfile)
class ChildProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "caregiver", "date_of_birth", "gender"]
    search_fields = ["name", "caregiver__username"]
    inlines = [DevelopmentalMilestoneInline]


@admin.register(DevelopmentalMilestone)
class DevelopmentalMilestoneAdmin(admin.ModelAdmin):
    list_display = ["child", "domain", "status", "observation_date", "reference"]
    list_filter = ["domain", "status"]
    autocomplete_fields = ["reference"]


@admin.register(ReferenceMilestone)
class ReferenceMilestoneAdmin(admin.ModelAdmin):
    list_display = [
        "milestone_key",
        "expected_age_months",
        "domain",
        "description",
        "source",
        "verified",
    ]
    list_filter = ["verified", "source", "domain", "expected_age_months"]
    search_fields = ["milestone_key", "description"]
    actions = ["mark_verified", "mark_unverified"]

    # Administrators maintain the guideline catalogue by role.
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

    @admin.action(description="Mark selected milestones as verified against source")
    def mark_verified(self, request, queryset):
        count = queryset.update(verified=True)
        self.message_user(
            request, f"{count} milestone(s) marked verified.", messages.SUCCESS
        )

    @admin.action(description="Mark selected milestones as unverified")
    def mark_unverified(self, request, queryset):
        count = queryset.update(verified=False)
        self.message_user(
            request, f"{count} milestone(s) marked unverified.", messages.SUCCESS
        )
