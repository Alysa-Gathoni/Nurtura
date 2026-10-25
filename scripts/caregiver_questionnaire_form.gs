/**
 * Nurtura caregiver evaluation: create the questionnaire Google Form (#132).
 *
 * Creates, in your own Google Drive:
 *   "Nurtura app questionnaire" - participant number, the 10 SUS items,
 *   the 6 satisfaction items and 2 open questions.
 *
 * Services: Forms only (FormApp). No network calls, no spreadsheets, no other
 * services. Logger is used only to print the links when it finishes.
 *
 * OAuth scope needed (Apps Script asks for it on the first run):
 *   https://www.googleapis.com/auth/forms
 * To pin it, set this in the project's appsscript.json:
 *   "oauthScopes": ["https://www.googleapis.com/auth/forms"]
 *
 * How to use:
 *   1. Go to https://script.google.com, create a new project and paste this file in.
 *   2. Replace CONTACT below with how respondents can reach you.
 *   3. Run createCaregiverQuestionnaire() and approve the Forms permission.
 *   4. The execution log shows the form's edit and respondent links.
 *
 * The question text below is the same as docs/caregiver_evaluation_form.md, and a
 * repository test (recommendations/test_caregiver_evaluation_scripts.py) fails if
 * they ever differ. scripts/score_caregiver_questionnaire.py reads the responses
 * by the SUSnn / Sn / On prefixes, so keep them.
 */

const CONTACT = 'FILL IN';

const INTRO =
  "Thank you for trying Nurtura. Please answer these questions on your own, " +
  "about the app you have just used. It takes about 5 minutes. There are no " +
  "right or wrong answers: I'm testing the app, not you. This form is anonymous. " +
  "It doesn't collect your name or email, so please don't type any personal " +
  "details. You can skip the open questions, and you can stop at any time by " +
  "closing the page. Questions: {CONTACT}.";

const CONFIRMATION = 'Thank you for taking part. You can close this page.';

// <questions> (kept identical to docs/caregiver_evaluation_form.md by a test)
const QUESTIONS = {
  "participant": "Participant number (the researcher will tell you, for example P03)",
  "participant_help": "Type P and then two digits, for example P03.",
  "scale_low": "Strongly disagree",
  "scale_high": "Strongly agree",
  "sus_page": "Using the app",
  "sus": [
    "SUS01: I think that I would like to use this app frequently.",
    "SUS02: I found the app unnecessarily complex.",
    "SUS03: I thought the app was easy to use.",
    "SUS04: I think that I would need the support of a technical person to be able to use this app.",
    "SUS05: I found the various functions in this app were well integrated.",
    "SUS06: I thought there was too much inconsistency in this app.",
    "SUS07: I would imagine that most people would learn to use this app very quickly.",
    "SUS08: I found the app very awkward to use.",
    "SUS09: I felt very confident using the app.",
    "SUS10: I needed to learn a lot of things before I could get going with this app."
  ],
  "satisfaction_page": "The suggestions",
  "satisfaction": [
    "S1: I trust the activities the app suggested for my child.",
    "S2: The suggested activities would be useful for my child.",
    "S3: The \"Why this?\" explanations helped me understand why each activity was suggested.",
    "S4: I could do the suggested activities at home with things I already have.",
    "S5: I would keep using this app with my child.",
    "S6: I would recommend this app to another parent or carer."
  ],
  "open_page": "In your own words",
  "open": [
    "O1: What did you like most about the app?",
    "O2: What would you change?"
  ]
};
// </questions>

function createCaregiverQuestionnaire() {
  if (CONTACT.indexOf('FILL IN') !== -1 || !CONTACT.trim()) {
    throw new Error(
      'CONTACT still says FILL IN. Set CONTACT at the top of the script to how ' +
        'respondents can reach you (for example a university email), then run again.'
    );
  }
  const form = buildForm_('Nurtura app questionnaire');
  Logger.log('%s\n  edit: %s\n  respond: %s', form.getTitle(), form.getEditUrl(),
    form.getPublishedUrl());
}

function buildForm_(title) {
  const form = FormApp.create(title);

  // Settings.
  if (typeof form.setEmailCollectionType === 'function') {
    form.setEmailCollectionType(FormApp.EmailCollectionType.DO_NOT_COLLECT);
  } else {
    form.setCollectEmail(false);
  }
  try {
    form.setRequireLogin(false); // only applies to Google Workspace accounts
  } catch (e) {
    Logger.log('setRequireLogin not available for this account (%s); sign-in is not required.', e);
  }
  form.setLimitOneResponsePerUser(false);
  form.setAllowResponseEdits(false);
  form.setShowLinkToRespondAgain(false);
  form.setProgressBar(true);
  form.setConfirmationMessage(CONFIRMATION);

  // Page 1: introduction and the participant number.
  form.setDescription(INTRO.replace('{CONTACT}', CONTACT));
  form.addTextItem()
    .setTitle(QUESTIONS.participant)
    .setRequired(true)
    .setValidation(
      FormApp.createTextValidation()
        .setHelpText(QUESTIONS.participant_help)
        .requireTextMatchesPattern('P[0-9]{2}')
        .build()
    );

  // Pages 2 and 3: every statement on a required 1-5 scale.
  [[QUESTIONS.sus_page, QUESTIONS.sus],
    [QUESTIONS.satisfaction_page, QUESTIONS.satisfaction]].forEach(function (page) {
    form.addPageBreakItem().setTitle(page[0]);
    page[1].forEach(function (statement) {
      form.addScaleItem()
        .setTitle(statement)
        .setBounds(1, 5)
        .setLabels(QUESTIONS.scale_low, QUESTIONS.scale_high)
        .setRequired(true);
    });
  });

  // Page 4: two optional open questions.
  form.addPageBreakItem().setTitle(QUESTIONS.open_page);
  QUESTIONS.open.forEach(function (question) {
    form.addParagraphTextItem().setTitle(question).setRequired(false);
  });
  return form;
}
