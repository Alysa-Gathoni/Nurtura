from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from .choices import AgeRange, ContentStatus, Difficulty, Domain, Source
from .models import DevelopmentalActivity


def activity_fields(**overrides):
    fields = {
        "activity_id": "ACT001",
        "activity_name": "Tummy Time",
        "developmental_domain": Domain.MOTOR,
        "age_range": AgeRange.MONTHS_0_3,
        "developmental_goal": "Build neck strength",
        "materials": "Blanket",
        "difficulty_level": Difficulty.BEGINNER,
        "description": "Supervised time on the tummy.",
        "cultural_relevance": "Can be done on a kanga.",
        "source": Source.PATHWAYS,
    }
    fields.update(overrides)
    return fields


class DevelopmentalActivityTests(TestCase):
    def test_create_and_str(self):
        activity = DevelopmentalActivity.objects.create(**activity_fields())
        activity.full_clean()
        self.assertEqual(str(activity), "ACT001: Tummy Time")

    def test_activity_id_must_be_unique(self):
        DevelopmentalActivity.objects.create(**activity_fields())
        with self.assertRaises(IntegrityError):
            DevelopmentalActivity.objects.create(
                **activity_fields(activity_name="Rolling Practice")
            )

    def test_name_unique_per_domain_case_insensitive(self):
        DevelopmentalActivity.objects.create(**activity_fields())
        with self.assertRaises(IntegrityError):
            DevelopmentalActivity.objects.create(
                **activity_fields(activity_id="ACT002", activity_name="tummy time")
            )

    def test_same_name_allowed_in_different_domain(self):
        DevelopmentalActivity.objects.create(**activity_fields())
        DevelopmentalActivity.objects.create(
            **activity_fields(activity_id="ACT002", developmental_domain=Domain.SENSORY)
        )
        self.assertEqual(DevelopmentalActivity.objects.count(), 2)

    def test_controlled_vocabularies_enforced(self):
        for field, bad_value in [
            ("developmental_domain", "Visual"),
            ("age_range", "36-48 months"),
            ("difficulty_level", "Expert"),
            ("source", "Wikipedia"),
        ]:
            with self.subTest(field=field):
                activity = DevelopmentalActivity(
                    **activity_fields(**{field: bad_value})
                )
                with self.assertRaises(ValidationError) as ctx:
                    activity.full_clean()
                self.assertIn(field, ctx.exception.message_dict)

    def test_vocabularies_match_data_readme(self):
        self.assertEqual(
            Domain.values,
            ["Cognitive", "Language", "Motor", "Sensory", "Socio-Emotional"],
        )
        self.assertEqual(
            AgeRange.values,
            [
                "Prenatal",
                "0-3 months",
                "3-6 months",
                "6-12 months",
                "12-18 months",
                "18-24 months",
                "24-36 months",
            ],
        )
        self.assertEqual(Difficulty.values, ["Beginner", "Intermediate", "Advanced"])
        self.assertEqual(
            Source.values, ["WHO", "CDC", "UNICEF", "Montessori", "Pathways.org"]
        )


class ContentStatusTests(TestCase):
    def setUp(self):
        self.activity = DevelopmentalActivity.objects.create(**activity_fields())

    def test_new_activities_default_to_draft(self):
        self.assertEqual(self.activity.content_status, ContentStatus.DRAFT)

    def test_full_workflow_to_published_and_back(self):
        for status in (
            ContentStatus.UNDER_REVIEW,
            ContentStatus.PUBLISHED,
            ContentStatus.DRAFT,
        ):
            self.activity.transition_to(status)
            self.activity.refresh_from_db()
            self.assertEqual(self.activity.content_status, status)

    def test_review_can_be_sent_back_to_draft(self):
        self.activity.transition_to(ContentStatus.UNDER_REVIEW)
        self.activity.transition_to(ContentStatus.DRAFT)
        self.assertEqual(self.activity.content_status, ContentStatus.DRAFT)

    def test_invalid_transitions_rejected(self):
        invalid = [
            (ContentStatus.DRAFT, ContentStatus.PUBLISHED),
            (ContentStatus.DRAFT, ContentStatus.DRAFT),
            (ContentStatus.PUBLISHED, ContentStatus.UNDER_REVIEW),
        ]
        for current, target in invalid:
            with self.subTest(current=current, target=target):
                DevelopmentalActivity.objects.filter(pk=self.activity.pk).update(
                    content_status=current
                )
                self.activity.refresh_from_db()
                with self.assertRaises(ValidationError):
                    self.activity.transition_to(target)
                self.activity.refresh_from_db()
                self.assertEqual(self.activity.content_status, current)

    def test_published_queryset(self):
        DevelopmentalActivity.objects.create(
            **activity_fields(
                activity_id="ACT002",
                activity_name="Peekaboo",
                content_status=ContentStatus.PUBLISHED,
            )
        )
        DevelopmentalActivity.objects.create(
            **activity_fields(
                activity_id="ACT003",
                activity_name="Stacking Blocks",
                content_status=ContentStatus.UNDER_REVIEW,
            )
        )
        published = DevelopmentalActivity.objects.published()
        self.assertEqual([a.activity_id for a in published], ["ACT002"])


class ActivityAdminWorkflowTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username="admin", password="x-test-pass"
        )
        self.client.force_login(self.admin_user)
        self.changelist = reverse("admin:activities_developmentalactivity_changelist")

    def run_action(self, action, *activities):
        return self.client.post(
            self.changelist,
            {"action": action, "_selected_action": [a.pk for a in activities]},
            follow=True,
        )

    def test_create_via_admin_then_publish(self):
        data = activity_fields()
        response = self.client.post(
            reverse("admin:activities_developmentalactivity_add"), data
        )
        self.assertEqual(response.status_code, 302)
        activity = DevelopmentalActivity.objects.get(activity_id="ACT001")
        self.assertEqual(activity.content_status, ContentStatus.DRAFT)

        self.run_action("submit_for_review", activity)
        response = self.run_action("publish", activity)
        activity.refresh_from_db()
        self.assertEqual(activity.content_status, ContentStatus.PUBLISHED)
        self.assertContains(response, "1 activity moved to Published.")
        self.assertEqual(LogEntry.objects.filter(object_id=str(activity.pk)).count(), 3)

    def test_publish_skips_drafts_with_warning(self):
        draft = DevelopmentalActivity.objects.create(**activity_fields())
        in_review = DevelopmentalActivity.objects.create(
            **activity_fields(
                activity_id="ACT002",
                activity_name="Peekaboo",
                content_status=ContentStatus.UNDER_REVIEW,
            )
        )
        response = self.run_action("publish", draft, in_review)
        draft.refresh_from_db()
        in_review.refresh_from_db()
        self.assertEqual(draft.content_status, ContentStatus.DRAFT)
        self.assertEqual(in_review.content_status, ContentStatus.PUBLISHED)
        self.assertContains(
            response, "Skipped: Cannot move ACT001 from Draft to Published."
        )

    def test_return_to_draft_unpublishes(self):
        activity = DevelopmentalActivity.objects.create(
            **activity_fields(content_status=ContentStatus.PUBLISHED)
        )
        self.run_action("return_to_draft", activity)
        activity.refresh_from_db()
        self.assertEqual(activity.content_status, ContentStatus.DRAFT)

    def test_status_not_editable_in_change_form(self):
        activity = DevelopmentalActivity.objects.create(**activity_fields())
        data = activity_fields(content_status=ContentStatus.PUBLISHED)
        response = self.client.post(
            reverse(
                "admin:activities_developmentalactivity_change", args=[activity.pk]
            ),
            data,
        )
        self.assertEqual(response.status_code, 302)
        activity.refresh_from_db()
        self.assertEqual(activity.content_status, ContentStatus.DRAFT)
