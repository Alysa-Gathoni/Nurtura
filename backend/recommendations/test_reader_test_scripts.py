"""Checks on the reader-test form script and scorer (#80).

They live outside backend/ (scripts/, docs/), so these tests read them as files.
"""

import csv
import hashlib
import importlib.util
import io
import json
import re
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

REPO = Path(settings.BASE_DIR).parent
GS = REPO / "scripts" / "reader_test_forms.gs"
CARDS_MD = REPO / "docs" / "explanation_reader_test_cards.md"
FORM_DOC = REPO / "docs" / "explanation_reader_test_form.md"
SCORER = REPO / "scripts" / "score_reader_test.py"

CONSENT = (
    "Nurtura is a student project that suggests early-childhood activities to "
    "caregivers. I'm checking whether its explanations are easy to understand. "
    "You'll see 10 made-up children and the activity the app suggested for each. "
    "For every one, please say in your own words why you think it was suggested, "
    "and whether anything worried or confused you. It takes about 10 to 15 minutes. "
    "There are no right or wrong answers: I'm testing the wording, not you. This "
    "form is anonymous. I don't collect your name or email, so please don't type "
    "any personal details. Taking part is voluntary and you can stop at any time by "
    "closing the page. Answers are used only in my project report. If you continue, "
    "you agree to take part. Questions: {CONTACT}."
)


def cards_from_markdown():
    text = CARDS_MD.read_text(encoding="utf-8")
    blocks = re.split(r"^### Card (\d+)\s*$", text, flags=re.M)[1:]
    cards = []
    for number, body in zip(blocks[0::2], blocks[1::2]):
        cards.append(
            {
                "number": int(number),
                "child": re.search(r"^\*\*Your child:\*\* (.+)$", body, re.M)
                .group(1)
                .strip(),
                "activity": re.search(r"^\*\*Suggested activity:\*\* (.+)$", body, re.M)
                .group(1)
                .strip(),
                "explanation": re.search(r"^> (.+)$", body, re.M).group(1).strip(),
            }
        )
    return cards


def gs_cards(source):
    return json.loads(
        source.split("const CARDS = ", 1)[1].split(";\n// </cards>", 1)[0]
    )


def gs_consent(source):
    block = source.split("const CONSENT =", 1)[1].split(";\n", 1)[0]
    return "".join(json.loads(s) for s in re.findall(r'"(?:[^"\\]|\\.)*"', block))


def load_scorer():
    spec = importlib.util.spec_from_file_location("score_reader_test", SCORER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FormScriptTests(SimpleTestCase):
    def setUp(self):
        self.source = GS.read_text(encoding="utf-8")

    def test_cards_are_verbatim_from_the_cards_file(self):
        self.assertEqual(gs_cards(self.source), cards_from_markdown())
        self.assertEqual(len(gs_cards(self.source)), 10)

    def test_consent_text(self):
        self.assertEqual(gs_consent(self.source), CONSENT)

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
            "'Thank you. You can close this page.'",
            "'Nurtura wording check (A)', CARDS)",
            "'Nurtura wording check (B)', CARDS.slice().reverse())",
        ):
            with self.subTest(call=call):
                self.assertIn(call, self.source)

    def test_no_answer_key_case_labels_or_ids(self):
        text = json.dumps(gs_cards(self.source)) + self.source
        self.assertNotRegex(
            text,
            r"(?i)answer key[^,]|main reason|constructed|\bH\d\d\b|\bC[12]\b|"
            r"Prenatal case|WHO milestone|CDC milestone",
        )


class FormDocTests(SimpleTestCase):
    def test_hand_build_doc_matches_the_script(self):
        doc = FORM_DOC.read_text(encoding="utf-8")
        self.assertIn(CONSENT, doc)
        self.assertIn("Thank you. You can close this page.", doc)
        for card in cards_from_markdown():
            k = card["number"]
            with self.subTest(card=k):
                self.assertIn(f"Card {k} of 10", doc)
                self.assertIn(f"Your child: {card['child']}", doc)
                self.assertIn(f"Suggested activity: {card['activity']}", doc)
                self.assertIn(card["explanation"], doc)
                self.assertIn(
                    f"C{k:02d} Q1: In your own words, why was this activity "
                    "suggested for this child?",
                    doc,
                )
        self.assertIn("at least **80%**", doc)
        self.assertIn("**10 valid respondents**", doc)


class ScorerTests(SimpleTestCase):
    def setUp(self):
        self.scorer = load_scorer()
        self.key = self.scorer.load_answer_key()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def write(self, name, respondents):
        columns = ["Timestamp", self.scorer.CARE_QUESTION, self.scorer.SEEN_QUESTION]
        for k in range(1, 11):
            columns += [
                f"C{k:02d} Q1: In your own words, why was this activity suggested for this child?",
                f"C{k:02d} Q2: Did any sentence worry or confuse you?",
                f"C{k:02d} Q3: If yes, which sentence, and why?",
            ]
        path = self.dir / name
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for seen, answers, concern in respondents:
                row = ["2026-10-11 10:00", "Yes", seen]
                for k in range(1, 11):
                    worried = concern.get(k)
                    row += [
                        answers.get(k, ""),
                        "Yes (tell us below)" if worried else "No",
                        worried or "",
                    ]
                writer.writerow(row)
        return path

    def test_answer_key_has_ten_cards_and_each_reason_counts_as_understood(self):
        self.assertEqual(sorted(self.key), list(range(1, 11)))
        for card, reason in self.key.items():
            with self.subTest(card=card):
                self.assertTrue(self.scorer.mark(card, reason), reason)

    def test_scoring_exclusion_pass_rule_and_quotes(self):
        good = {k: self.key[k] for k in range(1, 11)}
        vague = {**good, 3: "no idea", 7: "seems fun"}
        a = self.write(
            "A.csv",
            [("No", good, {}) for _ in range(6)]
            + [("Yes", good, {})]  # excluded: had seen the project
            + [("No", vague, {2: "The 2 months part worried me."})],
        )
        b = self.write("B.csv", [("No", good, {}) for _ in range(4)])
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (a, b)}

        result = self.scorer.score(self.scorer.load_responses([a, b]), self.key)
        self.assertEqual(len(result["valid"]), 11)
        self.assertEqual(len(result["excluded"]), 1)
        self.assertEqual(result["cards"][1]["understood"], 11)
        self.assertEqual(result["cards"][3]["understood"], 10)  # 10/11 = 91% passes
        self.assertTrue(result["cards"][3]["passes"])
        self.assertEqual(result["cards_passing"], 10)
        self.assertTrue(result["test_passes"])
        quotes = result["cards"][2]["concerns"]
        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0][2], "The 2 months part worried me.")

        out = io.StringIO()
        self.scorer.report(result, out=out)
        self.assertIn("excluded: A.csv row 8", out.getvalue())
        self.assertIn("Review every answer above", out.getvalue())
        after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (a, b)}
        self.assertEqual(before, after)  # never edits the exports

    def test_too_few_respondents_or_cards_fails(self):
        good = {k: self.key[k] for k in range(1, 11)}
        few = self.write("few.csv", [("No", good, {}) for _ in range(9)])
        result = self.scorer.score(self.scorer.load_responses([few]), self.key)
        self.assertEqual(result["cards_passing"], 10)
        self.assertFalse(result["test_passes"])  # 9 valid respondents < 10

        bad = {**good, 1: "?", 2: "?", 3: "?"}
        many = self.write("many.csv", [("No", bad, {}) for _ in range(12)])
        result = self.scorer.score(self.scorer.load_responses([many]), self.key)
        self.assertEqual(result["cards_passing"], 7)
        self.assertFalse(result["test_passes"])  # 7 cards < 8
