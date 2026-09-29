import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from activities.choices import Domain

from .models import ChildProfile, DevelopmentalMilestone


class UserModelTests(TestCase):
    def test_custom_user_model_is_active(self):
        User = get_user_model()
        self.assertEqual(User._meta.label, "profiles.User")
        user = User.objects.create_user(username="caregiver", password="x-test-pass")
        self.assertTrue(user.check_password("x-test-pass"))


class ChildProfileTests(TestCase):
    def setUp(self):
        self.caregiver = get_user_model().objects.create_user(
            username="caregiver", password="x-test-pass"
        )

    def make_child(self, **kwargs):
        fields = {
            "caregiver": self.caregiver,
            "name": "Amani",
            "date_of_birth": datetime.date(2025, 6, 1),
        }
        fields.update(kwargs)
        return ChildProfile.objects.create(**fields)

    def test_defaults(self):
        child = self.make_child()
        self.assertEqual(child.gender, ChildProfile.Gender.UNSPECIFIED)
        self.assertEqual(child.interests, [])
        self.assertEqual(child.preferences, {})
        self.assertEqual(str(child), "Amani")

    def test_json_fields_round_trip(self):
        child = self.make_child(
            interests=["music", "animals"], preferences={"difficulty": "Beginner"}
        )
        child.refresh_from_db()
        self.assertEqual(child.interests, ["music", "animals"])
        self.assertEqual(child.preferences, {"difficulty": "Beginner"})

    def test_caregiver_can_manage_many_children(self):
        self.make_child(name="Amani")
        self.make_child(name="Baraka")
        self.assertEqual(self.caregiver.children.count(), 2)

    def test_deleting_caregiver_deletes_children(self):
        self.make_child()
        self.caregiver.delete()
        self.assertEqual(ChildProfile.objects.count(), 0)

    def test_invalid_gender_rejected(self):
        child = self.make_child(gender="other-value")
        with self.assertRaises(ValidationError):
            child.full_clean()


class DevelopmentalMilestoneTests(TestCase):
    def setUp(self):
        caregiver = get_user_model().objects.create_user(
            username="caregiver", password="x-test-pass"
        )
        self.child = ChildProfile.objects.create(
            caregiver=caregiver, name="Amani", date_of_birth=datetime.date(2025, 6, 1)
        )

    def test_record_milestone_saves_and_links_to_child(self):
        milestone = self.child.record_milestone(
            domain=Domain.LANGUAGE,
            description="Says first words",
            status=DevelopmentalMilestone.Status.EMERGING,
            observation_date=datetime.date(2026, 5, 1),
        )
        self.assertEqual(self.child.milestones.get(), milestone)
        self.assertEqual(milestone.observation_date, datetime.date(2026, 5, 1))

    def test_record_milestone_defaults_to_today(self):
        milestone = self.child.record_milestone(
            domain=Domain.MOTOR,
            description="Rolls over",
            status=DevelopmentalMilestone.Status.ACHIEVED,
        )
        self.assertEqual(milestone.observation_date, timezone.localdate())

    def test_record_milestone_rejects_invalid_values(self):
        with self.assertRaises(ValidationError):
            self.child.record_milestone(
                domain="Visual", description="Tracks objects", status="achieved"
            )
        with self.assertRaises(ValidationError):
            self.child.record_milestone(
                domain=Domain.MOTOR, description="Sits unaided", status="done"
            )
        self.assertEqual(self.child.milestones.count(), 0)

    def test_milestones_ordered_newest_first(self):
        for day in (1, 15, 8):
            self.child.record_milestone(
                domain=Domain.MOTOR,
                description=f"Observation {day}",
                status=DevelopmentalMilestone.Status.EMERGING,
                observation_date=datetime.date(2026, 5, day),
            )
        days = [m.observation_date.day for m in self.child.milestones.all()]
        self.assertEqual(days, [15, 8, 1])
