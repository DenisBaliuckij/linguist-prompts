# Prompts: Persian · lemmatization

Run the four prompts in order. Each prompt is self-contained: start a new chat
for each stage and attach only the files listed under its inputs.

## 1. Building the Persian morphological ontology

**Purpose:** build a verifiable language-specific ontology from which a lemmatizer can take its rules, lemma conventions and lexical exceptions.

```text
You are a specialist in Persian linguistics and a linguistic data engineer.
Build one JSON file, `OntoPersian.json`, for Standard (Iranian) Persian,
written Persian of Iran (ISO 639-3: fas / pes, ISO 639-1: fa). Work only
with the attached sources. Do not add facts from memory and do not invent
rules, examples or references.

Input A: a general ontology of human language grammar (GOLD OntoLing).
Input B: the attached grammars, dictionaries, stem lists and paradigm
tables of Persian: {{list of attached sources}}. A reference grammar, a
list of verbs with past and present stems, a word list or dictionary with
parts of speech, and a list of Arabic broken plurals with their singulars
are strongly recommended.
Input C (optional): the annotation guidelines of the gold corpus that will be
used for evaluation (for example, the README of UD Persian-Seraji). Use it
only for lemma conventions, never as a source of test items.

Task: keep the sections of Input A that are compatible with Persian, but
fill them only with facts from Input B and Input C. Do not produce a reduced
demonstration ontology: transfer every fact and paradigm in Input B that is
relevant for lemmatization. The main goal of the file is to support a
working rule-based lemmatizer with the broadest coverage the sources allow.
The Morphology module must contain:

- parts of speech and the citation (dictionary) form of each one;
- noun plurals: -ها (and -های, -هایی), -ان with its variants -گان (stems in
  -ه) and -یان (stems in a vowel), the Arabic plurals -ات, -ین, -ون, and the
  broken plurals as full "plural -> singular" tables when the sources give
  them;
- ezafe (-ی after a vowel, ‌ای / ۀ / هٔ after -ه), indefinite -ی, and how to
  tell them from a lemma that itself ends in -ی;
- comparative -تر and superlative -ترین, including suppletive forms;
- the verb: past stem and present stem of every verb in the sources (as a
  "past#present" table or a reference to a stem list), the prefixes می‌,
  نمی‌, ب, ن, the personal endings of the present and the past, the past
  participle in -ه and the perfect forms with attached endings (رفته‌اند),
  the infinitive in -ن, compound verbs and preverbs (فرو، فرا، بر، در);
- the copula and auxiliaries (است، هست، نیست، بود، باید، خواه، توان) and
  their lemmas;
- the personal and demonstrative pronouns and the pronominal clitics
  (-م -ت -ش -مان -تان -شان) and which lemma they take;
- orthographic facts that affect matching: ZWNJ (U+200C) and spaces inside
  words (می‌شود / میشود / می شود), Arabic ي and ك against Persian ی and ک,
  harakat and shadda, hamza (مسأله, رأی, مسئله), ۀ;
- every lemma convention of the target corpus (Input C) that differs from
  a plain dictionary form: for example, whether verbs are cited by the
  infinitive, by the past stem or by "past#present", how compound verbs
  and preverbs are written in the lemma, which lemma clitics take;
- every condition under which a surface form is ambiguous and one rule is
  not enough (for example کند: present of کردن or past of کندن).

For every rule record: an id, the input pattern, the output lemma or the
operation, the conditions (part of speech and morphological features,
written with the exact feature names of the target corpus, for example UD
`Number`, `Tense`, `Mood`, `Polarity`, `VerbForm`), at least one example
"form -> lemma" that is attested in Input B, the source, and a status:
`rule`, `lexicon_required` or `ambiguous`. If a rule has several possible
outputs and Input B contains a machine-readable lexicon, count in that
lexicon how often each output is correct and record the counts; if one
output covers at least 60% of at least 10 attested forms, record it as
`default_replacement` together with the counts as evidence. Do not choose
defaults from intuition. If a machine-readable dictionary, stem list or
paradigm table is part of Input B, do not copy it into the JSON; register it
in `lexicon_files` with its file name, format, columns, licence and the
lemma convention it follows. Do not fill unknown data with plausible
guesses: leave it out and add a record to `gaps` with the reason.

In `meta` give: title, version, language, ISO codes, every source that was
actually used, the date and the scope. Before answering, check that the
JSON is valid, that every example really follows its rule (when paradigm
tables are available, check the verbal rules on them and record how many
attested forms they cover) and that every fact has a source. Remove rules
whose examples cannot be found and list rules without an attested example
under `verification`.

Return only valid UTF-8 JSON, with no Markdown and no comments.
```

## 2. Preparing gold use-cases

**Purpose:** obtain two independent sets of gold "word form -> lemma" pairs for building and testing the lemmatizer.

```text
You are a linguistic data curator. Prepare two disjoint sets of gold
use-cases for lemmatization of Standard Persian: `development` and
`holdout`.

Use only sources that are already annotated, where the lemma is given by the
source and is not predicted by you. Prefer UD Persian-Seraji in CoNLL-U
format: its README states "Lemmas: manual native". UD Persian-PerDT has
lemmas "converted with corrections" and may be used for a second experiment,
but never mix the two treebanks in one experiment. If you use another
source, state explicitly where its lemmas come from and its licence.

Algorithm:
1. Record the source: name, URL, version or commit, licence and the
   statement about the annotation type.
2. Read only syntactic words (lines whose ID is an integer). Skip
   multiword-token range lines (`3-4`) and empty nodes (`3.1`), and skip
   PUNCT, SYM, NUM and X.
3. Keep only non-trivial cases, where FORM differs from LEMMA after
   lower-casing with str.lower(). Keep FORM and LEMMA exactly as written,
   including ZWNJ. Store sent_id and token_id so that every pair can be
   checked in the original corpus.
4. Take `development` only from the treebank's train split and `holdout`
   only from its test split, so that no sentence is in both sets. Select
   sentences with a fixed random seed, take at most three cases per
   sentence, and record the seed.
5. `development` must have at least 1000 cases; `holdout` at least 300.
   The holdout set must never be shown while the ontology, the lexicon or
   the code is written.
6. In each set count the cases by UPOS and by the main morphological
   features (Number, Tense, Mood, Polarity, VerbForm). If the distribution
   is uneven, do not hide it.

Return two valid UTF-8 YAML files, `persian-development.yaml` and
`persian-holdout.yaml`, each with this structure:

language:
  name: Persian
  iso639_3: fas
source:
  name: ...
  url: ...
  version: ...
  license: ...
  annotation_type: ...
split: development | holdout
selection: ...
counts: ...
cases:
  - sentence_id: ...
    token_id: ...
    form: ...
    lemma: ...
    upos: ...
    features: ...

Do not correct, normalize or rewrite gold lemmas. If an annotation looks
suspicious (for example a lemma still in "past#present" form), keep it as
is and add the field `annotation_note`. After writing the files, check that
the YAML parses, all cases are non-trivial, IDs are unique and no sentence
appears in both sets.
```

## 3. Building a rule-based lemmatizer

**Purpose:** generate a local Python lemmatizer from the ontology and the development set, without using the holdout set.

```text
You are a Python engineer and a specialist in Persian morphology. Write one
file, `persian_lemmatizer.py`, with the class `PersianLemmatizer`. Use only:

- `OntoPersian.json`;
- the files listed in its `lexicon_files`;
- `persian-development.yaml`;
- the Python 3.11+ standard library (plus PyYAML for reading YAML).

Never read `persian-holdout.yaml`: it is reserved for independent
evaluation.

Required API:

class PersianLemmatizer:
    def __init__(self, ontology_path="OntoPersian.json",
                 dev_path="persian-development.yaml") -> None: ...
    def lemmatize(self, form: str, upos: str, features: str = "_") -> dict[str, str]: ...
    def lemmatize_sentence(self, tokens: list[dict]) -> list[dict]: ...

Requirements:
1. Load the rules, rule statuses, lemma conventions and lexical exceptions
   from the ontology; do not write an independent, incompatible list of
   rules in the code. Build the lexicon from the ontology, its
   `lexicon_files` and the development set.
2. Normalize for lookup only: Unicode NFC, ي -> ی, ك -> ک, ۀ -> ه, remove
   harakat, shadda and hamza above, remove ZWNJ and spaces inside the
   token. Output the lemma in the spelling of the corpus when the
   development set contains it (ZWNJ, hamza), otherwise in the lexicon
   spelling without harakat.
3. Verbs: strip the prefixes (نمی‌, می‌, ن only with Polarity=Neg, ب), then
   the endings (personal endings, perfect endings, participle -ه,
   infinitive -ن), and look the remaining stem up as a past stem or as a
   present stem mapped to its past stem. When both readings are possible,
   use Tense, Mood and VerbForm to choose (present stem for Tense=Pres,
   Mood=Sub or Imp; past stem for Tense=Past or VerbForm=Part), then how
   often each lemma occurs in the development set.
4. Nouns and adjectives: plural rules only with Number=Plur, degree rules
   only with Degree; accept a candidate only if it is a known lemma (word
   list or development set); a regular -ها plural may be stripped without
   the lexicon.
5. Learn the corpus conventions that the sources do not document from the
   development set: run the analysis on every development case; when the
   analysis returns the same output X for at least 3 cases and at least 80%
   of them have the gold lemma Y != X (for example the forms of شدن
   annotated with the lemma کرد), store the mapping X -> Y for that UPOS
   group and apply it after the analysis. Report every learned mapping.
6. If nothing can decide, return the form unchanged in `lemma`, set
   `confidence="ambiguous"` and explain why in `reason`. Do not invent a
   lemma (in particular, do not guess the singular of a broken plural).
7. Support at least NOUN, PROPN, VERB, AUX, PRON, ADJ and DET. In
   `lemmatize_sentence` keep the original token, the lemma, the applied
   rule and the confidence: `exact`, `rule`, `lexicon`, `default` or
   `ambiguous`.
8. Add `evaluate(cases_path)` with exact-match accuracy and a breakdown by
   UPOS; it must write a CSV with form, expected, actual, UPOS, status and
   the reason for each error.
9. List the known limitations in the module docstring. Do not claim full
   lemmatization of Persian.

Every result of `lemmatize` must have exactly the fields `lemma`, `rule`,
`confidence` and `reason`. For example:

{"lemma": "کرد", "rule": "ipfv_mi+pers_ند+present_stem", "confidence": "lexicon", "reason": ""}

or, when nothing can decide:

{"lemma": "مناطق", "rule": "", "confidence": "ambiguous", "reason": "broken plural: singular not in the lexicon"}

Because the development set is also part of the lexicon, scoring the
lemmatizer on it directly gives a meaningless 100%. Before answering, run a
5-fold cross-validation on the development set with folds split by
sentence (build the lexicon and the learned conventions without the fold,
score the fold), and report accuracy and the number of errors by category.
Fix errors only by changing general rules or the ontology, never by adding
single test words to code. Return only the content of the Python file, with
no Markdown.
```

## 4. Independent evaluation of the lemmatizer

**Purpose:** measure the quality of the finished lemmatizer on the hidden set and produce a diagnostic report.

```text
You are an NLP evaluation engineer. You have:

- `persian_lemmatizer.py`;
- `OntoPersian.json` and the files in its `lexicon_files`;
- `persian-development.yaml`;
- `persian-holdout.yaml`.

Before the run, record SHA-256 hashes of the lemmatizer, the ontology and
both YAML files, and check them again before scoring. You must not change
any of them after you have seen any result. For every case run:

result = PersianLemmatizer().lemmatize(form, upos, features)
actual = result["lemma"]
passed = actual == lemma

Compare lemmas exactly, as Unicode strings in NFC (a different ZWNJ or
hamza spelling counts as an error); also report the accuracy after the
lookup normalization of the ontology, but do not replace the exact one
with it.

Create two files:

1. `persian-evaluation-results.csv` with every case, without exception:
   sentence_id, token_id, form, expected, actual, upos, features, status,
   rule, confidence, reason.
2. `persian-evaluation-report.md` with these sections:
   - source and version of the holdout set;
   - number of cases, correct answers, errors and exact-match accuracy;
   - accuracy and number of cases by UPOS;
   - accuracy by form type where the features allow it (number, tense,
     mood, verb form);
   - how many cases were answered by the lexicon, by a rule, by a learned
     convention or returned as ambiguous, and the accuracy of each group;
   - all errors with ID, form, expected and actual lemma;
   - error groups: broken plural, ezafe / indefinite -ی, unknown verb stem,
     present/past stem homography, spelling (ZWNJ, hamza), clitic pronoun,
     corpus lemma convention, annotation error, other;
   - an ablation: the same lemmatizer built without the development set
     (ontology and lexicon files only), to show how much the result depends
     on corpus-derived lexicon;
   - limitations of the test and concrete next improvements.

Do not delete failed cases, do not correct the gold annotation and do not
round results in a way that hides errors. If the code does not run, that is
also a result: give the traceback and set accuracy to `not computed`.
```
