"""Weekly plans (#244): each batch records the first day of its plan.

Batches stored before this each start their own plan on the day they were
generated, so a caregiver's current ideas carry on until a week after them.
"""

from django.db import migrations, models
from django.utils import timezone


def fill_plan_start(apps, schema_editor):
    Recommendation = apps.get_model("recommendations", "Recommendation")
    for row in Recommendation.objects.filter(plan_start__isnull=True).only(
        "pk", "date_generated"
    ):
        row.plan_start = timezone.localtime(row.date_generated).date()
        row.save(update_fields=["plan_start"])


class Migration(migrations.Migration):
    dependencies = [
        ("recommendations", "0007_saved_activity"),
    ]

    operations = [
        migrations.AddField(
            model_name="recommendation",
            name="plan_start",
            field=models.DateField(
                blank=True,
                help_text="First day of the weekly plan this batch belongs to.",
                null=True,
            ),
        ),
        migrations.RunPython(fill_plan_start, migrations.RunPython.noop),
    ]
