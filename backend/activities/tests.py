from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from .choices import AgeRange, Difficulty, Domain, Source
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
