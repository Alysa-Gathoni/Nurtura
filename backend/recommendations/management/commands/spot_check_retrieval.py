"""Print retrieval results for sample profiles, for checking by hand (#31).

Usage (from backend/):
    python manage.py spot_check_retrieval [--limit 5] [--markdown]
                                          [--preview-unpublished] [--alpha A]

For each sample child (one per domain, a mixed case and an expecting parent)
this shows the query, the profile's top domain and the top retrieved
activities, marking whether each is in the domain the sample should retrieve.
Everything runs in a transaction that is rolled back: the sample children are
never saved.

With --alpha, the weighted ranking (rule priority, similarity and age, #35)
is shown instead of plain similarity, with each score's components.

Only Published, embedded activities are retrieved, as in the app.
--preview-unpublished temporarily publishes and embeds every activity (also
rolled back) to preview results before content review; such output must not
be used as the Definition of done evidence.
"""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from activities.choices import ContentStatus
from activities.models import DevelopmentalActivity
from recommendations.models import ActivityEmbedding
from recommendations.ranking import rank
from recommendations.retrieval import retrieve
from recommendations.samples import SAMPLE_PROFILES, create_child

SPOT_CHECK_USERNAME = "spot-check@nurtura.invalid"


class Command(BaseCommand):
    help = "Show retrieval results for sample profiles, for checking by hand."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=5)
        parser.add_argument(
            "--markdown",
            action="store_true",
            help="Output Markdown tables, e.g. for the project report.",
        )
        parser.add_argument(
            "--alpha",
            type=float,
            default=None,
            help="Show the weighted ranking at this alpha (0-1) instead of "
            "plain similarity.",
        )
        parser.add_argument(
            "--preview-unpublished",
            action="store_true",
            help="Temporarily publish and embed every activity (rolled back).",
        )

    def handle(self, *args, **options):
        self.markdown = options["markdown"]
        with transaction.atomic():
            if options["preview_unpublished"]:
                DevelopmentalActivity.objects.update(
                    content_status=ContentStatus.PUBLISHED
                )
                call_command("embed_activities", stdout=StringIO())
            self._run(
                options["limit"], options["preview_unpublished"], options["alpha"]
            )
            transaction.set_rollback(True)

    def _run(self, limit, preview, alpha=None):
        published = DevelopmentalActivity.objects.published()
        embedded = ActivityEmbedding.objects.filter(
            activity__content_status=ContentStatus.PUBLISHED
        ).count()
        if preview:
            self._line(
                "**PREVIEW: every activity temporarily published and embedded "
                "(rolled back). Not Definition of done evidence.**"
                if self.markdown
                else "PREVIEW: every activity temporarily published and embedded "
                "(rolled back). Not Definition of done evidence."
            )
        if not published.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No Published activities, so nothing can be retrieved. "
                    "Publish activities in the admin, or use "
                    "--preview-unpublished to preview."
                )
            )
            return
        if embedded < published.count():
            self.stdout.write(
                self.style.WARNING(
                    f"{published.count() - embedded} Published activities have no "
                    "embedding; run `python manage.py embed_activities` first."
                )
            )

        caregiver = get_user_model().objects.create_user(username=SPOT_CHECK_USERNAME)
        matches = total = 0
        for sample in SAMPLE_PROFILES:
            child = create_child(sample, caregiver)
            if alpha is None:
                result = retrieve(child, limit=limit)
                items = [(c.activity, f"{c.similarity:.3f}") for c in result.candidates]
            else:
                result = rank(child, alpha=alpha, limit=limit)
                items = [
                    (
                        r.activity,
                        f"{r.score:.3f} (sim {r.similarity_norm:.2f}, "
                        f"priority {r.priority:.2f}, age x{r.age_weight:g})",
                    )
                    for r in result.ranked
                ]
            ranked_domains = result.evaluation.ranked_domains()
            self._header(sample, ranked_domains[0], result.query)
            rows = []
            for position, (activity, score) in enumerate(items, start=1):
                match = activity.developmental_domain in sample.expected_domains
                matches += match
                total += 1
                rows.append(
                    (
                        position,
                        score,
                        f"{activity.activity_id} {activity.activity_name}",
                        activity.developmental_domain,
                        activity.age_range,
                        "yes" if match else "no",
                    )
                )
            self._table(
                rows, "Similarity" if alpha is None else f"Score (alpha {alpha:g})"
            )

        share = matches / total if total else 0
        self._line("")
        self._line(
            f"Domain match: {matches}/{total} retrieved activities ({share:.0%}) are "
            "in the sample's expected domain(s). Judge relevance by hand as well: "
            "a different domain can still suit the child."
        )

    def _line(self, text):
        self.stdout.write(text)

    def _header(self, sample, top_domain, query):
        expected = " + ".join(sample.expected_domains)
        if self.markdown:
            self._line(f"\n### {sample.name}")
            self._line(
                f"*{sample.note}.* Expected: **{expected}**; profile top domain: **{top_domain}**\n"
            )
            self._line(f"> Query: {query}\n")
        else:
            self._line(f"\n== {sample.name}: {sample.note}")
            self._line(f"   expected: {expected} | profile top domain: {top_domain}")
            self._line(f"   query: {query}")

    def _table(self, rows, score_label="Similarity"):
        if not rows:
            self._line(
                "   (no candidates)" if not self.markdown else "_No candidates._"
            )
            return
        if self.markdown:
            self._line(
                f"| # | {score_label} | Activity | Domain | Age range | Expected domain? |"
            )
            self._line("|---|---|---|---|---|---|")
            for row in rows:
                self._line("| " + " | ".join(str(c) for c in row) + " |")
        else:
            for position, score, name, domain, age, match in rows:
                mark = "+" if match == "yes" else "-"
                self._line(f"   {position}. {score}  {mark} {name} [{domain}, {age}]")
