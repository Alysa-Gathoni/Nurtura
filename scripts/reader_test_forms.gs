/**
 * Nurtura explanation reader test: create the two Google Forms (#80).
 *
 * Creates, in your own Google Drive:
 *   "Nurtura wording check (A)" - cards in order 1 to 10
 *   "Nurtura wording check (B)" - the same cards, in reverse order
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
 *   3. Run createReaderTestForms() and approve the Forms permission.
 *   4. The execution log shows each form's edit and respondent links.
 *
 * The card text below is copied verbatim from docs/explanation_reader_test_cards.md.
 * Its text is identical to the 10 explanations at tag sprint6-explanations-v1, and a
 * repository test (recommendations/test_reader_test_scripts.py) fails if they
 * ever differ. Don't edit the card text here: regenerate it instead.
 * There's no answer key, case label or internal ID in this file.
 */

const CONTACT = 'FILL IN';

const CONSENT =
  "Nurtura is a student project that suggests early-childhood activities to " +
  "caregivers. I'm checking whether its explanations are easy to understand. " +
  "You'll see 10 made-up children and the activity the app suggested for each. " +
  "For every one, please say in your own words why you think it was suggested, " +
  "and whether anything worried or confused you. It takes about 10 to 15 minutes. " +
  "There are no right or wrong answers: I'm testing the wording, not you. This " +
  "form is anonymous. I don't collect your name or email, so please don't type " +
  "any personal details. Taking part is voluntary and you can stop at any time by " +
  "closing the page. Answers are used only in my project report. If you continue, " +
  "you agree to take part. Questions: {CONTACT}.";

const SCREENING = [
  'Do you look after a child under 5 (as a parent, relative or carer)?',
  'Had you seen or heard about this project before today?',
];

const CONFIRMATION = 'Thank you. You can close this page.';

// <cards> (generated from docs/explanation_reader_test_cards.md; do not edit by hand)
const CARDS = [
  {
    "number": 1,
    "child": "You're expecting: your baby is due in about 4 months. You asked for support with: social and emotional development.",
    "activity": "Sharing Hopes and Worries About the Baby",
    "explanation": "You said you'd like support with social and emotional development. It's an activity for parents during pregnancy. Its aim is to support your emotional wellbeing, which shapes your baby's early surroundings."
  },
  {
    "number": 2,
    "child": "Your child is 2½ months old. Milestones you recorded: “Holds head up when on tummy”: Not yet.",
    "activity": "Tummy Time",
    "explanation": "You recorded “Holds head up when on tummy” as not yet; most children do this by 2 months. It's designed for children aged 0–3 months, your child's age group. Its aim is to help your baby build the neck, shoulder and upper-body strength needed for rolling, sitting and crawling."
  },
  {
    "number": 3,
    "child": "Your child is 2½ months old. Milestones you recorded: “Smiles when you talk to or smile at them”: Not yet.",
    "activity": "Face-to-Face Cooing Exchange",
    "explanation": "You recorded “Smiles when you talk to or smile at them” as not yet; most children do this by 2 months. It's designed for children aged 0–3 months, your child's age group. Its aim is to help you and your baby feel close and take turns with each other."
  },
  {
    "number": 4,
    "child": "Your child is 4½ months old. You asked for support with: sensory development. Your child enjoys: music, rattles.",
    "activity": "Sound-Making Exploration",
    "explanation": "You said you'd like support with sensory development and that your child enjoys music, which points us towards activities for the senses. It's designed for children aged 3–6 months, your child's age group. Its aim is to help your baby's listening skills grow through lots of different sounds."
  },
  {
    "number": 5,
    "child": "Your child is 7 months old. Milestones you recorded: “Laughs”: Achieved; “Rolls from tummy to back”: Achieved.",
    "activity": "Texture Exploration",
    "explanation": "You haven't asked for help with a particular area, so this is a general activity for your child's age. It's designed for children aged 6–12 months, your child's age group. Its aim is to help your baby explore different textures by touch."
  },
  {
    "number": 6,
    "child": "Your child is 15½ months old. Milestones you recorded: “Takes a few steps on their own”: Not yet; “Shows you affection (hugs, cuddles, or kisses you)”: Not yet.",
    "activity": "Balancing While Holding Hands",
    "explanation": "You recorded “Takes a few steps on their own” as not yet; most children do this by 15 months. It's designed for children aged 12–18 months, your child's age group. Its aim is to help your child build balance and confidence in walking."
  },
  {
    "number": 7,
    "child": "Your child is 20 months old. Milestones you recorded: “Plays with toys in a simple way, like pushing a toy car”: Not yet.",
    "activity": "Buttons and Knobs Exploration Toy",
    "explanation": "You recorded “Plays with toys in a simple way, like pushing a toy car” as not yet; most children do this by 18 months. It's designed for children aged 18–24 months, your child's age group. Its aim is to help your child see how actions make things happen and solve small problems with their fingers."
  },
  {
    "number": 8,
    "child": "Your child is 20 months old. You asked for support with: sensory development. Your child enjoys: textures.",
    "activity": "Water Play with Containers",
    "explanation": "You said you'd like support with sensory development and that your child enjoys textures, which points us towards activities for the senses; this activity uses textures. It's written for slightly younger children (12–18 months), so your child may find it easy; adapt it to suit them. Its aim is to help your child explore through their senses by pouring and feeling different textures."
  },
  {
    "number": 9,
    "child": "Your child is 16 months old. Milestones you recorded: “Waves ‘bye-bye’”: Not yet; “Tries to say three or more words besides ‘mama’ or ‘dada’”: Not yet.",
    "activity": "Naming Everyday Objects",
    "explanation": "You recorded “Waves ‘bye-bye’” as not yet; most children do this by 12 months. “Tries to say three or more words besides ‘mama’ or ‘dada’” often comes next; most children do this by 18 months. It's designed for children aged 12–18 months, your child's age group. Its aim is to help your child understand and say more words by linking words to real objects."
  },
  {
    "number": 10,
    "child": "Your child is 13 months old. Milestones you recorded: “Standing with assistance”: Not yet.",
    "activity": "Balancing While Holding Hands",
    "explanation": "You recorded “Standing with assistance” as not yet; almost all children do this by about 12 months. It's designed for children aged 12–18 months, your child's age group. Its aim is to help your child build balance and confidence in walking."
  }
];
// </cards>

function createReaderTestForms() {
  if (CONTACT.indexOf('FILL IN') !== -1 || !CONTACT.trim()) {
    throw new Error(
      'CONTACT still says FILL IN. Set CONTACT at the top of the script to how ' +
        'respondents can reach you (for example a university email), then run again.'
    );
  }
  const a = buildForm_('Nurtura wording check (A)', CARDS);
  const b = buildForm_('Nurtura wording check (B)', CARDS.slice().reverse());
  [a, b].forEach(function (form) {
    Logger.log('%s\n  edit: %s\n  respond: %s', form.getTitle(), form.getEditUrl(),
      form.getPublishedUrl());
  });
}

function buildForm_(title, cards) {
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

  // Page 1: consent and two screening questions.
  form.setDescription(CONSENT.replace('{CONTACT}', CONTACT));
  SCREENING.forEach(function (question) {
    form.addMultipleChoiceItem()
      .setTitle(question)
      .setChoiceValues(['Yes', 'No'])
      .setRequired(true);
  });

  // One page per card, titled with the card's original number.
  cards.forEach(function (card) {
    const k = card.number;
    const prefix = 'C' + (k < 10 ? '0' + k : String(k));
    form.addPageBreakItem()
      .setTitle('Card ' + k + ' of 10')
      .setHelpText(
        'Your child: ' + card.child + '\n\n' +
        'Suggested activity: ' + card.activity + '\n\n' +
        card.explanation
      );
    form.addParagraphTextItem()
      .setTitle(prefix + ' Q1: In your own words, why was this activity suggested for this child?')
      .setRequired(true);
    form.addMultipleChoiceItem()
      .setTitle(prefix + ' Q2: Did any sentence worry or confuse you?')
      .setChoiceValues(['No', 'Yes (tell us below)'])
      .setRequired(true);
    form.addParagraphTextItem()
      .setTitle(prefix + ' Q3: If yes, which sentence, and why?')
      .setRequired(false);
  });
  return form;
}
