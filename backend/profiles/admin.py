from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ChildProfile, DevelopmentalMilestone, User

admin.site.register(User, UserAdmin)


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
