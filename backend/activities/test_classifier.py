"""Tests for the activity classifier (#181)."""

import csv
import tempfile
from unittest import mock
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from recommendations import embeddings
from recommendations.test_embeddings import FakeEncoder

from . import classifier
from .choices import AgeRange, ContentStatus, Domain
from .models import DevelopmentalActivity
from .tests import activity_fields

User = get_user_model()

DOMAIN_WORDS = {
    Domain.COGNITIVE: "puzzle sorting hiding finding thinking",
    Domain.LANGUAGE: "talking words babbling naming reading",
    Domain.MOTOR: "crawling walking balance reaching kicking",
    Domain.SENSORY: "textures sounds touch water sand",
    Domain.SOCIO_EMOTIONAL: "feelings hugging smiling sharing comfort",
}
AGE_WORDS = {
    AgeRange.PRENATAL: "pregnancy bump unborn",
    AgeRange.MONTHS_0_3: "newborn tiny",
    AgeRange.MONTHS_3_6: "rolling infant",
    AgeRange.MONTHS_6_12: "sitting older baby",
    AgeRange.MONTHS_12_18: "first steps toddler",
    AgeRange.MONTHS_18_24: "running young toddler",
    AgeRange.MONTHS_24_36: "preschooler pretend",
}
DOMAINS = list(DOMAIN_WORDS)
AGES = list(AGE_WORDS)


class ClassifierTestCase(TestCase):
    def setUp(self):
        embeddings.set_encoder(FakeEncoder())
        self.addCleanup(embeddings.set_encoder, None)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.model_path = Path(tmp.name) / "classifier.joblib"
        self.flags_path = Path(tmp.name) / "flags.csv"
        patcher = override_settings(ACTIVITY_CLASSIFIER_PATH=self.model_path)
        patcher.enable()
        self.addCleanup(patcher.disable)
        classifier._loaded = None

    def make_catalogue(self, mislabel=False):
        # 35 activities: each area 7 times, each age band 5 times.
        for i in range(35):
            domain, age = DOMAINS[i % 5], AGES[i % 7]
            DevelopmentalActivity.objects.create(
                **activity_fields(
                    activity_id=f"ACT-{i:04d}",
                    activity_name=f"Activity {i}",
                    developmental_goal="Play together",
                    # Age words twice: each area/age pair occurs once, so the
                    # age signal must be able to outweigh the area words.
                    description=(
                        f"{DOMAIN_WORDS[domain]} {AGE_WORDS[age]} {AGE_WORDS[age]}"
                    ),
                    developmental_domain=domain,
                    age_range=age,
                    content_status=ContentStatus.PUBLISHED,
                )
            )
        if mislabel:
            # Reads as Language, labelled Motor.
            DevelopmentalActivity.objects.filter(activity_id="ACT-0001").update(
                developmental_domain=Domain.MOTOR
            )
        call_command("embed_activities", stdout=StringIO())

    def train(self, *args):
        out = StringIO()
        call_command(
            "train_activity_classifier",
            "--flags",
            str(self.flags_path),
            *args,
            stdout=out,
        )
        return out.getvalue()


class TrainCommandTests(ClassifierTestCase):
    def test_reports_cross_validation_and_saves(self):
        self.make_catalogue()
        output = self.train()
        for text in (
            "35 Published activities",
            "5-fold stratified",
            "Area: 5 classes",
            "Age band: 7 classes",
            "Accuracy",
            "Macro-F1",
            "Baseline",
            "Confusion matrix",
        ):
            self.assertIn(text, output)
        self.assertTrue(self.model_path.exists())
        bundle = classifier.load()
        self.assertEqual(bundle["activities"], 35)
        self.assertEqual(bundle["embedding_model"], "fake-encoder")

    def test_separable_data_beats_the_baseline(self):
        self.make_catalogue()
        _, reports, _, _ = classifier.train()
        for report in reports.values():
            self.assertGreater(report["accuracy"], report["baseline_accuracy"])
            self.assertEqual(
                sum(map(sum, report["confusion"])), 35
            )  # every activity predicted once, out of fold

    def test_a_confident_disagreement_is_flagged(self):
        self.make_catalogue(mislabel=True)
        # 35 examples give softer probabilities than the real catalogue.
        with mock.patch.object(classifier, "FLAG_CONFIDENCE", 0.3):
            self.train()
        with open(self.flags_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        flagged = {(r["activity_id"], r["field"]) for r in rows}
        self.assertIn(("ACT-0001", "developmental_domain"), flagged)
        row = next(r for r in rows if r["activity_id"] == "ACT-0001")
        self.assertEqual((row["label"], row["predicted"]), ("Motor", "Language"))
        self.assertEqual(row["reviewer_decision"], "")

    def test_no_save_writes_nothing(self):
        self.make_catalogue()
        self.train("--no-save")
        self.assertFalse(self.model_path.exists())
        self.assertFalse(self.flags_path.exists())


class SuggestAPITests(ClassifierTestCase, APITestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user(
            username="admin@example.com", role=User.Role.ADMINISTRATOR
        )
        self.client.force_authenticate(self.admin)
        self.url = reverse("admin-api-activity-suggest")
        self.text = {
            "activity_name": "Naming game",
            "developmental_goal": "talking words naming",
            "description": "talking words babbling naming reading newborn tiny",
        }

    def test_503_until_trained(self):
        response = self.client.post(self.url, self.text, format="json")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("train_activity_classifier", response.json()["detail"])

    def test_suggests_the_top_three_with_probabilities(self):
        self.make_catalogue()
        self.train()
        response = self.client.post(self.url, self.text, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(set(body), {"developmental_domain", "age_range"})
        domains = body["developmental_domain"]
        self.assertEqual(len(domains), 3)
        self.assertEqual(domains[0]["value"], "Language")
        self.assertEqual(body["age_range"][0]["value"], "0-3 months")
        probabilities = [d["probability"] for d in domains]
        self.assertEqual(probabilities, sorted(probabilities, reverse=True))

    def test_needs_some_text(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_administrators_only(self):
        caregiver = User.objects.create_user(username="carer@example.com")
        self.client.force_authenticate(caregiver)
        response = self.client.post(self.url, self.text, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
