"""Tests for the retrieval spot-check samples and command (#31)."""

import unittest
from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from activities.choices import AgeRange, ContentStatus, Domain
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from profiles.models import ChildProfile, ReferenceMilestone
from profiles.rules import build_profile

from . import embeddings
from .models import ActivityEmbedding
from .retrieval import retrieve
from .samples import SAMPLE_PROFILES, create_child
from .test_embeddings import FakeEncoder

User = get_user_model()

# One clearly worded activity per domain, plus a prenatal one.
DOMAIN_ACTIVITIES = [
    dict(
        activity_id="ACT-0951",
        activity_name="Talk and Read Together",
        developmental_domain=Domain.LANGUAGE,
        age_range=AgeRange.MONTHS_6_12,
        developmental_goal="Build first words, babbling and listening",
        description="Talk, sing songs and read picture books together, naming "
        "things and answering your baby's babbling and first words.",
    ),
    dict(
        activity_id="ACT-0952",
        activity_name="Crawl and Walk Practice",
        developmental_domain=Domain.MOTOR,
        age_range=AgeRange.MONTHS_12_18,
        developmental_goal="Build strength for crawling, standing and walking",
        description="Encourage tummy time, crawling and pulling up to stand, "
        "then hold hands for first steps and balance.",
    ),
    dict(
        activity_id="ACT-0953",
        activity_name="Find the Hidden Toy",
        developmental_domain=Domain.COGNITIVE,
        age_range=AgeRange.MONTHS_6_12,
        developmental_goal="Understand that hidden objects still exist",
        description="Hide a toy under a cloth or cup and let your baby search "
        "for it; later, sort shapes and try simple puzzles.",
    ),
    dict(
        activity_id="ACT-0954",
        activity_name="Name and Smile Games",
        developmental_domain=Domain.SOCIO_EMOTIONAL,
        age_range=AgeRange.MONTHS_6_12,
        developmental_goal="Build bonding, attention to people and feelings",
        description="Call your baby's name, smile and copy their expressions, "
        "and play with family members while naming feelings.",
    ),
    dict(
        activity_id="ACT-0955",
        activity_name="Textures and Water Play",
        developmental_domain=Domain.SENSORY,
        age_range=AgeRange.MONTHS_6_12,
        developmental_goal="Explore the senses through touch, sound and water",
        description="Let your baby touch different textures, splash in shallow "
        "water and listen to calming sounds and music.",
    ),
    dict(
        activity_id="ACT-0956",
        activity_name="Gentle Belly Touch",
        developmental_domain=Domain.SENSORY,
        age_range=AgeRange.PRENATAL,
        developmental_goal="Calm sensory bonding before birth",
        description="During pregnancy, gently massage the belly and play calming "
        "music for your baby.",
    ),
]


def create_activities(status=ContentStatus.PUBLISHED):
    for fields in DOMAIN_ACTIVITIES:
        DevelopmentalActivity.objects.create(
            **activity_fields(content_status=status, **fields)
        )


class SpotCheckTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_milestones", stdout=StringIO())

    def setUp(self):
        embeddings.set_encoder(FakeEncoder())
        self.addCleanup(embeddings.set_encoder, None)

    def spot_check(self, *args):
        out = StringIO()
        call_command("spot_check_retrieval", *args, stdout=out, stderr=StringIO())
        return out.getvalue()


class SampleProfileTests(SpotCheckTestCase):
    def test_samples_use_real_catalogue_milestones(self):
        for sample in SAMPLE_PROFILES:
            for key in sample.not_yet:
                with self.subTest(sample=sample.name, key=key):
                    self.assertTrue(
                        ReferenceMilestone.objects.filter(milestone_key=key).exists()
                    )

    def test_each_sample_profile_puts_an_expected_domain_on_top(self):
        caregiver = User.objects.create_user(username="caregiver")
        for sample in SAMPLE_PROFILES:
            with self.subTest(sample=sample.name):
                child = create_child(sample, caregiver)
                evaluation = build_profile(child)
                self.assertIn(evaluation.ranked_domains()[0], sample.expected_domains)
                if sample.age_months >= 0:
                    self.assertEqual(int(evaluation.age_months), int(sample.age_months))
                else:
                    self.assertLess(evaluation.age_months, 0)


class SpotCheckCommandTests(SpotCheckTestCase):
    def test_nothing_published_explains_what_to_do(self):
        output = self.spot_check()
        self.assertIn("No Published activities", output)
        self.assertIn("--preview-unpublished", output)

    def test_reports_every_sample_and_saves_nothing(self):
        create_activities()
        call_command("embed_activities", stdout=StringIO())
        output = self.spot_check("--limit", "3")

        for sample in SAMPLE_PROFILES:
            self.assertIn(f"== {sample.name}", output)
        self.assertIn("Domain match:", output)
        self.assertNotIn("PREVIEW", output)
        self.assertFalse(User.objects.exists())
        self.assertFalse(ChildProfile.objects.exists())

    def test_markdown_output(self):
        create_activities()
        call_command("embed_activities", stdout=StringIO())
        output = self.spot_check("--markdown")
        self.assertIn("### Language delay", output)
        self.assertIn("| # | Similarity | Activity | Domain | Age range |", output)

    def test_warns_when_published_activities_are_not_embedded(self):
        create_activities()
        output = self.spot_check()
        self.assertIn("have no embedding", output)

    def test_preview_leaves_content_unchanged(self):
        create_activities(status=ContentStatus.DRAFT)
        output = self.spot_check("--preview-unpublished")

        self.assertIn("PREVIEW", output)
        self.assertIn("ACT-095", output)
        self.assertFalse(DevelopmentalActivity.objects.published().exists())
        self.assertFalse(ActivityEmbedding.objects.exists())
        self.assertFalse(User.objects.exists())


@unittest.skipUnless(
    settings.SBERT_MODEL_PATH.exists(),
    "SBERT model not downloaded (run setup_sbert.py); skipped in CI",
)
class RealModelSpotCheckTests(SpotCheckTestCase):
    """Sprint 4 Definition of done, automated: with one clearly worded activity
    per domain, each sample's top retrieval is in its expected domain."""

    def setUp(self):
        super().setUp()
        embeddings.set_encoder(None)  # the real all-MiniLM-L6-v2 model
        create_activities()
        call_command("embed_activities", stdout=StringIO())

    def test_each_sample_retrieves_its_domain_first(self):
        caregiver = User.objects.create_user(username="caregiver")
        for sample in SAMPLE_PROFILES:
            with self.subTest(sample=sample.name):
                child = create_child(sample, caregiver)
                top = retrieve(child, limit=1).candidates[0].activity
                self.assertIn(top.developmental_domain, sample.expected_domains)
