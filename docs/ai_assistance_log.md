# AI assistance log

> **Last updated: 2026-10-19.** Code, tests and documentation in this repository were developed with an AI coding agent (Claude Code), working under the author's direction and review. This log records examples where the agent proposed an explanation or a change, how it was checked against the code, data or a real run, and whether it was accepted or rejected. It is a working record for the sprint reviews and for any disclosure the institution requires. The author remains responsible for the code and its conclusions.
>
> **Not AI-generated:** the relevance labels used in the evaluation are the researcher's own judgements ([data/evaluation/README.md](../data/evaluation/README.md)), and so are the choice of α and the rule used to choose it, both fixed before labelling ([sprint5_alpha_results.md](sprint5_alpha_results.md)).

## Rule followed

An agent's explanation is treated as a hypothesis until it's checked. Each check uses something outside the agent: the code, a test, a log, a measurement, or a source document. Rejected suggestions are kept here alongside accepted ones.

## Examples

| # | What the agent suggested | How it was checked | Evidence | Outcome |
|---|---|---|---|---|
| 1 | During the phone test, registration failed with 400. The agent's first guess was that the test password was too similar to the email address. | Ran the registration validator directly on the same data | The validator returned "A user with that username already exists". An earlier, stalled test run had resumed and registered first | **Rejected.** The real cause was a duplicate run. Fixed by stopping stale runs and using a fresh email alias |
| 2 | When writing the project overview, the agent described explanations as "never comparing the child with other children". | Ran the real pipeline for the example child and read the explanation it produced | The explanation says "most children do this by 4 months", which is a statement about typical ages | **Rejected.** Reworded to "built only from what the caregiver told the app, the milestone guidelines and the activity's own details" (#106) |
| 3 | The tester couldn't see the code digits while typing. The agent first suspected the code boxes' colours. | Checked the colours in both themes, then read how Android screenshots work in the `integration_test` package | The colours had good contrast. Capturing screenshots on Android converts the app's surface to an image, which freezes the display | **First explanation rejected, second accepted.** On Android, screenshots now start after the code step (#108) |
| 4 | Two taps in the phone test missed their targets. The agent suggested the on-screen keyboard was covering them. | Read the test log | The log's hit-test warnings named the exact widgets that missed (the Sensory concern chip and the milestone card). Both came straight after typing | **Accepted.** The test closes the keyboard before tapping, and a missed tap now fails at once (#108) |
| 5 | Screenshots hung on Android. The agent proposed that the capture was waiting for a frame the test never drew. | Read the `integration_test` package's source for `takeScreenshot` | The capture asks the app to draw a new frame, and in a test, frames are only drawn when pumped | **Accepted.** The test pumps frames while capturing (#108) |
| 6 | In a narrow (phone-width) screenshot, the admin dashboard looked cut off on the right. That suggested a layout bug. | Measured the page in the browser: the viewport width and every element extending past it | The layout viewport was 489 px with nothing overflowing. The headless browser has a minimum window width, so the 420 px screenshot was cropped | **Rejected as a bug.** No change made (#116) |
| 7 | The agent proposed colours for the dashboard's milestone chart. | Ran a colour-blindness and contrast validator on each palette, in both themes | The first light palette failed (sage read as grey); several dark palettes failed the lightness, chroma and separation checks | **Only validated colours accepted.** Light `#5A8C4C / #CF9B33 / #BC5F55`, dark `#3E9E7C / #BB8418 / #D4566E` (#116) |
| 8 | When writing this sprint's documentation, the agent listed the tests covering invalid input, with what each expects. | Read each cited test's assertions | Four descriptions didn't match exactly (for example, one test is about an unknown domain or status, not a missing milestone) | **Corrected before committing** (#118) |

## Where AI was not used

- **Relevance labels and the choice of α.** These are the researcher's own; see the note at the top.
- **Reader test and caregiver evaluation responses.** These come from real participants and are kept out of the repository.

## Content drafted with AI help, then approved by the author

- **Plain-language aims (#70).** The caregiver-facing "Its aim is to …" wording was drafted with the agent's help. Each draft was then reviewed row by row in `data/review/plain_aims_draft.csv`, and only rows the author marked approved (or rewrote) were loaded ([data/review/README.md](../data/review/README.md)).
