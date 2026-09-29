from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ChildProfile, DevelopmentalMilestone, User


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


@admin.register(ChildProfile)
class ChildProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "caregiver", "date_of_birth", "gender"]
    search_fields = ["name", "caregiver__username"]
    inlines = [DevelopmentalMilestoneInline]


@admin.register(DevelopmentalMilestone)
class DevelopmentalMilestoneAdmin(admin.ModelAdmin):
    list_display = ["child", "domain", "status", "observation_date"]
    list_filter = ["domain", "status"]
