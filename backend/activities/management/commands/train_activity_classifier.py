"""Train and evaluate the activity classifier (#181).

Usage (from backend/):
    python manage.py train_activity_classifier [--markdown] [--flags PATH]
        [--no-save]

Reports, for area and for age band, 5-fold stratified cross-validation
accuracy and macro-F1 against a majority-class baseline, per-class
precision, recall and F1, and the confusion matrix. Then trains on every
Published activity and saves the classifier to settings.ACTIVITY_CLASSIFIER_PATH.

Activities whose out-of-fold prediction disagrees with their label with at
least classifier.FLAG_CONFIDENCE probability are written to --flags
(default data/review/classifier_flags.csv) for a person to check.
"""

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from activities import classifier

DEFAULT_FLAGS = (
    Path(settings.BASE_DIR).parent / "data" / "review" / "classifier_flags.csv"
)
FIELD_NAMES = {"developmental_domain": "Area", "age_range": "Age band"}
SHORT = {
    "Cognitive": "Cog",
    "Language": "Lang",
    "Motor": "Motor",
    "Sensory": "Sens",
    "Socio-Emotional": "S-E",
}


class Command(BaseCommand):
    help = "Train and cross-validate the activity area and age-band classifier."

    def add_arguments(self, parser):
        parser.add_argument("--markdown", action="store_true")
        parser.add_argument("--flags", type=Path, default=DEFAULT_FLAGS)
        parser.add_argument(
            "--no-save", action="store_true", help="Evaluate only; save nothing."
        )

    def handle(self, *args, **options):
        self.markdown = options["markdown"]
        activities, _ = classifier.training_data()
        if len(activities) < classifier.FOLDS * 2:
            raise CommandError(
                "Too few Published, embedded activities to train on. Run "
                "embed_activities first."
            )
        models, reports, flags, count = classifier.train()

        self._heading("Data")
        self._line(
            f"{count} Published activities, each a 384-number SBERT embedding "
            f"(name, goal and description). {classifier.FOLDS}-fold stratified "
            f"cross-validation (seed {classifier.SEED}); logistic regression "
            "with balanced class weights, its regularisation strength chosen "
            "by an inner cross-validation on each training fold."
        )
        for field, report in reports.items():
            self._report(FIELD_NAMES[field], report)

        self._heading("Flagged for review")
        self._line(
            f"{len(flags)} labels where the out-of-fold prediction disagreed with "
            f"at least {classifier.FLAG_CONFIDENCE:.0%} probability."
        )
        if not options["no_save"]:
            self._write_flags(options["flags"], flags)
            path = classifier.save(models, reports, count)
            self._line(f"Saved the classifier to {path}")

    def _report(self, name, r):
        self._heading(f"{name}: {len(r['classes'])} classes")
        self._table(
            ["Measure", "Classifier", f"Baseline (always {r['baseline_class']})"],
            [
                ["Accuracy", f"{r['accuracy']:.3f}", f"{r['baseline_accuracy']:.3f}"],
                ["Macro-F1", f"{r['macro_f1']:.3f}", "-"],
                *(
                    [["Within one band", f"{r['within_one']:.3f}", "-"]]
                    if name == "Age band"
                    else []
                ),
            ],
        )
        self._line("")
        self._table(
            ["Class", "Precision", "Recall", "F1", "Activities"],
            [
                [
                    c["class"],
                    f"{c['precision']:.3f}",
                    f"{c['recall']:.3f}",
                    f"{c['f1']:.3f}",
                    str(c["support"]),
                ]
                for c in r["per_class"]
            ],
        )
        self._line("")
        self._line("Confusion matrix (rows: label, columns: prediction):")
        self._line("")
        short = [SHORT.get(c, c) for c in r["classes"]]
        self._table(
            ["", *short],
            [[short[i], *map(str, row)] for i, row in enumerate(r["confusion"])],
        )

    def _write_flags(self, path, flags):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "activity_id",
                    "activity_name",
                    "field",
                    "label",
                    "predicted",
                    "confidence",
                    "reviewer_decision",
                ]
            )
            for flag in flags:
                writer.writerow(
                    [
                        flag.activity.activity_id,
                        flag.activity.activity_name,
                        flag.field,
                        flag.label,
                        flag.predicted,
                        f"{flag.confidence:.2f}",
                        "",
                    ]
                )
        self._line(f"Wrote {len(flags)} flag(s) to {path}")

    # Output helpers (as in evaluate_alpha_grid)

    def _heading(self, text):
        self.stdout.write(f"\n## {text}" if self.markdown else f"\n== {text}")

    def _line(self, text):
        self.stdout.write(text)

    def _table(self, header, rows):
        if self.markdown:
            self.stdout.write("| " + " | ".join(header) + " |")
            self.stdout.write("|" + "---|" * len(header))
            for row in rows:
                self.stdout.write("| " + " | ".join(row) + " |")
        else:
            widths = [max(len(str(x)) for x in col) for col in zip(header, *rows)]
            for row in [header, *rows]:
                self.stdout.write(
                    "  ".join(str(x).ljust(w) for x, w in zip(row, widths))
                )
