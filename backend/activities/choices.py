"""Controlled vocabularies shared across apps.

Stored values match the canonical spellings in data/README.md, so cleaned CSV
rows can be loaded without translation.
"""

from django.db import models


class Domain(models.TextChoices):
    COGNITIVE = "Cognitive", "Cognitive"
    LANGUAGE = "Language", "Language"
    MOTOR = "Motor", "Motor"
    SENSORY = "Sensory", "Sensory"
    SOCIO_EMOTIONAL = "Socio-Emotional", "Socio-Emotional"


class AgeRange(models.TextChoices):
    PRENATAL = "Prenatal", "Prenatal"
    MONTHS_0_3 = "0-3 months", "0-3 months"
    MONTHS_3_6 = "3-6 months", "3-6 months"
    MONTHS_6_12 = "6-12 months", "6-12 months"
    MONTHS_12_18 = "12-18 months", "12-18 months"
    MONTHS_18_24 = "18-24 months", "18-24 months"
    MONTHS_24_36 = "24-36 months", "24-36 months"


class Difficulty(models.TextChoices):
    BEGINNER = "Beginner", "Beginner"
    INTERMEDIATE = "Intermediate", "Intermediate"
    ADVANCED = "Advanced", "Advanced"


class ContentStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    UNDER_REVIEW = "under_review", "Under Review"
    PUBLISHED = "published", "Published"


class Source(models.TextChoices):
    WHO = "WHO", "WHO"
    CDC = "CDC", "CDC"
    UNICEF = "UNICEF", "UNICEF"
    MONTESSORI = "Montessori", "Montessori"
    PATHWAYS = "Pathways.org", "Pathways.org"
