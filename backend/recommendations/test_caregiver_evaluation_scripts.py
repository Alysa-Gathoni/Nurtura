"""Checks on the caregiver questionnaire form script and scorer (#132).

They live outside backend/ (scripts/, docs/), so these tests read them as files.
"""

import csv
import importlib.util
import io
import json
import re
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

REPO = Path(settings.BASE_DIR).parent
GS = REPO / "scripts" / "caregiver_questionnaire_form.gs"
FORM_DOC = REPO / "docs" / "caregiver_evaluation_form.md"
SCORER = REPO / "scripts" / "score_caregiver_questionnaire.py"

INTRO = (
    "Thank you for trying Nurtura. Please answer these questions on your own, "
    "about the app you have just used. It takes about 5 minutes. There are no "
    "right or wrong answers: I'm testing the app, not you. This form is anonymous. "
    "It doesn't collect your name or email, so please don't type any personal "
    "details. You can skip the open questions, and you can stop at any time by "
    "closing the page. Questions: {CONTACT}."
)

# Brooke (1996), with "app" for "system" and "awkward" for "cumbersome".
SUS_ITEMS = [
    "I think that I would like to use this app frequently.",
    "I found the app unnecessarily complex.",
    "I thought the app was easy to use.",
    "I think that I would need the support of a technical person to be able to use this app.",
    "I found the various functions in this app were well integrated.",
    "I thought there was too much inconsistency in this app.",
    "I would imagine that most people would learn to use this app very quickly.",
    "I found the app very awkward to use.",
    "I felt very confident using the app.",
    "I needed to learn a lot of things before I could get going with this app.",
]


def gs_questions(source):
    return json.loads(
        source.split("const QUESTIONS = ", 1)[1].split(";\n// </questions>", 1)[0]
    )


def gs_intro(source):
    block = source.split("const INTRO =", 1)[1].split(";\n", 1)[0]
    return "".join(json.loads(s) for s in re.findall(r'"(?:[^"\\]|\\.)*"', block))


def load_scorer():
    spec = importlib.util.spec_from_file_location(
        "score_caregiver_questionnaire", SCORER
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FormScriptTests(SimpleTestCase):
    def setUp(self):
        self.source = GS.read_text(encoding="utf-8")
        self.questions = gs_questions(self.source)

    def test_sus_items_are_the_standard_ten_in_order(self):
        self.assertEqual(
            self.questions["sus"],
            [f"SUS{k:02d}: {text}" for k, text in enumerate(SUS_ITEMS, start=1)],
        )

    def test_satisfaction_and_open_prefixes(self):
        self.assertEqual(
            [q.split(":")[0] for q in self.questions["satisfaction"]],
            ["S1", "S2", "S3", "S4", "S5", "S6"],
        )
        self.assertEqual(
            [q.split(":")[0] for q in self.questions["open"]], ["O1", "O2"]
        )

    def test_intro_text(self):
        self.assertEqual(gs_intro(self.source), INTRO)

    def test_contact_guard(self):
        self.assertIn("const CONTACT = 'FILL IN';", self.source)
        self.assertIn("CONTACT.indexOf('FILL IN') !== -1", self.source)
        self.assertIn("throw new Error(", self.source)

    def test_only_the_forms_service(self):
        self.assertIn(
            "https://www.googleapis.com/auth/forms", self.source.split("*/")[0]
        )
        services = set(re.findall(r"\b([A-Z][A-Za-z]+App)\.", self.source))
        self.assertEqual(services, {"FormApp"})
        self.assertNotRegex(self.source, r"UrlFetch|fetch\(|Spreadsheet|DriveApp|Gmail")

    def test_settings(self):
        for call in (
            "FormApp.EmailCollectionType.DO_NOT_COLLECT",
            "setRequireLogin(false)",
            "setLimitOneResponsePerUser(false)",
            "setAllowResponseEdits(false)",
            "setShowLinkToRespondAgain(false)",
            "setProgressBar(true)",
            "'Thank you for taking part. You can close this page.'",
            "requireTextMatchesPattern('P[0-9]{2}')",
            ".setBounds(1, 5)",
        ):
            with self.subTest(call=call):
                self.assertIn(call, self.source)

    def test_scale_items_required_and_open_items_optional(self):
        scale = self.source.split("form.addScaleItem()", 1)[1].split("});", 1)[0]
        self.assertIn(".setRequired(true)", scale)
        open_items = self.source.split("addParagraphTextItem()", 1)[1].split(";", 1)[0]
        self.assertIn(".setRequired(false)", open_items)


class FormDocTests(SimpleTestCase):
    def test_doc_matches_the_script(self):
        doc = FORM_DOC.read_text(encoding="utf-8")
        questions = gs_questions(GS.read_text(encoding="utf-8"))
        self.assertIn(INTRO, doc)
        self.assertIn("Thank you for taking part. You can close this page.", doc)
        for key in ("participant", "participant_help", "scale_low", "scale_high"):
            with self.subTest(key=key):
                self.assertIn(questions[key], doc)
        for key in ("sus_page", "satisfaction_page", "open_page"):
            with self.subTest(key=key):
                self.assertIn(f": {questions[key]}.**", doc)
        for key in ("sus", "satisfaction", "open"):
            for question in questions[key]:
                with self.subTest(question=question):
                    self.assertIn(f"- {question}\n", doc)


class ScorerTests(SimpleTestCase):
    def setUp(self):
        self.scorer = load_scorer()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.questions = gs_questions(GS.read_text(encoding="utf-8"))

    def write(self, rows):
        """rows: (participant, 10 SUS values, 6 satisfaction values, (O1, O2))."""
        q = self.questions
        columns = [
            "Timestamp",
            q["participant"],
            *q["sus"],
            *q["satisfaction"],
            *q["open"],
        ]
        path = self.dir / "responses.csv"
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for participant, sus, sat, opens in rows:
                writer.writerow(
                    ["2026/11/02 10:00:00", participant, *sus, *sat, *opens]
                )
        return path

    def test_sus_score_formula(self):
        sus_score = self.scorer.sus_score
        self.assertEqual(sus_score([3] * 10), 50.0)
        self.assertEqual(sus_score([5, 1] * 5), 100.0)
        self.assertEqual(sus_score([1, 5] * 5), 0.0)
        # Odd items: response - 1; even items: 5 - response.
        self.assertEqual(sus_score([4, 2, 4, 1, 4, 2, 5, 2, 4, 2]), 80.0)
        self.assertIsNone(sus_score([3] * 9 + [None]))

    def test_scoring_summary_and_warnings(self):
        path = self.write(
            [
                ("p01", [5, 1] * 5, [5, 4, 4, 3, 5, 5], ("Easy to follow", "")),
                ("P02", [3] * 10, [4, 4, 2, 3, 4, 4], ("", "Bigger text")),
                ("P02", [4, 2, 4, 1, 4, 2, 5, 2, 4, 2], [3, 3, 3, 3, 3, 3], ("", "")),
                ("P04", [3] * 9 + [""], [1, 2, 3, 4, 5, 5], ("", "")),
            ]
        )
        result = self.scorer.score(
            self.scorer.load_responses(path), ["P01", "P02", "P03"]
        )
        self.assertEqual(
            [r.participant for r, _ in result["responses"]],
            ["P01", "P02", "P02", "P04"],
        )
        self.assertEqual([s for _, s in result["responses"]], [100.0, 50.0, 80.0, None])
        self.assertEqual(result["complete"], 3)
        self.assertAlmostEqual(result["sus_mean"], 230 / 3)
        self.assertEqual((result["sus_min"], result["sus_max"]), (50.0, 100.0))
        self.assertEqual(result["duplicates"], ["P02"])
        self.assertEqual(result["unexpected"], ["P04"])
        self.assertEqual(result["missing"], ["P03"])
        s3 = result["satisfaction"]["S3"]
        self.assertEqual((s3["n"], s3["median"]), (4, 3))
        self.assertEqual(s3["counts"], {1: 0, 2: 1, 3: 2, 4: 1, 5: 0})

        out = io.StringIO()
        self.scorer.report(result, out=out)
        text = out.getvalue()
        self.assertIn("P04 (row 5): incomplete, left out of the mean", text)
        self.assertIn("Mean 76.7; lowest 50; highest 100 (n = 3)", text)
        self.assertIn("WARNING: P02 appears more than once", text)
        self.assertIn("O1, P01: Easy to follow", text)
        self.assertIn("O2, P02: Bigger text", text)

    def test_missing_columns_are_an_error(self):
        path = self.dir / "bad.csv"
        path.write_text("Timestamp,Participant number\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SUS01-SUS10"):
            self.scorer.load_responses(path)

    def test_out_of_range_values_are_incomplete(self):
        path = self.write([("P01", [3] * 9 + [7], [3] * 6, ("", ""))])
        result = self.scorer.score(self.scorer.load_responses(path))
        self.assertEqual([s for _, s in result["responses"]], [None])
        self.assertIsNone(result["sus_mean"])
