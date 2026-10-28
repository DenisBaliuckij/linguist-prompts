# Prompts: Armenian · lemmatization

Run the four prompts in order. Each prompt is self-contained: start a new chat
for each stage and attach only the files listed under its inputs.

## 1. Building the Eastern Armenian morphological ontology

**Purpose:** build a verifiable language-specific ontology from which a lemmatizer can take its rules, lemma conventions and lexical exceptions.

```text
You are a specialist in Armenian linguistics and a linguistic data engineer.
Build one JSON file, `OntoArmenian.json`, for Modern Eastern Armenian
(ISO 639-3: hye, ISO 639-1: hy, standard written language of the Republic of
Armenia, reformed orthography). Work only with the attached sources. Do not
add facts from memory and do not invent rules, examples or references.

Input A: a general ontology of human language grammar (GOLD OntoLing).
Input B: the attached grammars, dictionaries, paradigm tables and
descriptions of Eastern Armenian: {{list of attached sources}}.
Input C (optional): the annotation guidelines of the gold corpus that will be
used for evaluation (for example, the UD Armenian documentation). Use it only
for lemma conventions, never as a source of test items.

Task: keep the sections of Input A that are compatible with Armenian, but
fill them only with facts from Input B and Input C. Do not produce a reduced
demonstration ontology: transfer every fact and paradigm in Input B that is
relevant for lemmatization. The main goal of the file is to support a
working rule-based lemmatizer with the broadest coverage the sources allow.
The Morphology module must contain:

- parts of speech and the citation (dictionary) form of each one;
- noun declension: number (-եր after monosyllabic stems, -ներ after
  polysyllabic stems, and the exceptions listed in the sources), the cases
  (nominative/accusative, genitive/dative, ablative, instrumental, locative),
  the definite article -ը / -ն, the possessive suffixes -ս and -դ, and the
  order in which these suffixes combine;
- declension classes other than the -ի class (for example -ու, -ան, -ոջ,
  -ց, internal vowel change such as մայր -> մոր, the -ություն -> -ության /
  -ությամբ type), with the stem alternations each class causes;
- stem alternations that make stripping a suffix insufficient: reduction of
  ի and ու in the last syllable (գիրք -> գրքի), the glide յ after vowel-final
  stems, ա/ո-final names, and any case where the lemma cannot be restored by
  a rule alone;
- verb conjugation: the -ել and -ալ classes, the -նել / -չել / -անալ /
  -ենալ subclasses, the infinitive, the participles and converbs (-ում,
  -ել, -ած, -ելու / -ալու, -ող, -ելիս, the connegative), the aorist stems
  (-եց-, -աց-, -ավ), subjunctive, conditional (կ- prefix), imperative,
  the negative prefix չ-, the passive -վ- and the causative -ացն- / -եցն-;
- adjective degree (-ագույն, ամենա-) and substantivized adjectives;
- the personal, demonstrative, reflexive, relative and interrogative
  pronoun paradigms as full "form -> lemma" tables;
- irregular and suppletive paradigms (for example the verbs of being,
  coming, giving, eating, doing, putting, carrying) as full
  "form -> lemma" tables or as references to a machine-readable lexicon;
- orthographic facts that affect matching: the ligature և, the digraph ու,
  capitalization of proper names, and the in-word emphasis, exclamation
  and question marks ՛ ՜ ՞ which must be removed before lookup;
- every lemma convention of the target corpus (Input C) that differs from
  a plain dictionary form, for example which lemma auxiliary forms take,
  whether passive and causative forms are lemmatized to the base verb,
  how pronoun and proper-noun lemmas are written;
- every condition under which a surface form is ambiguous and one rule is
  not enough.

For every rule record: an id, the input pattern, the output lemma or the
operation, the conditions (part of speech and morphological features,
written with the exact feature names of the target corpus, e.g. UD writes
possessive suffixes as `Person[psor]`, not `Poss`), at least one example
"form -> lemma" that is attested in Input B, the source, and a status:
`rule`, `lexicon_required` or `ambiguous`. If a rule has several possible
outputs (for example -ում -> -ել or -ալ) and Input B contains a
machine-readable lexicon, count in that lexicon how often each output is
correct and record the counts; if one output covers at least 60% of at
least 10 attested forms, record it as `default_replacement` together with
the counts as evidence. Do not choose defaults from intuition. If a machine-readable dictionary or
paradigm table is part of Input B, do not copy it into the JSON; register
it in `lexicon_files` with its file name, format, columns, licence and
the lemma convention it follows. Do not fill unknown data with plausible
guesses: leave it out and add a record to `gaps` with the reason.

In `meta` give: title, version, language, ISO codes, every source that was
actually used, the date and the scope. Before answering, check that the
JSON is valid, that every example really follows its rule (and, when a
paradigm table is available, that the example has the grammatical tags the
rule claims) and that every fact has a source. Remove rules whose
examples cannot be found and list rules without an attested example under
`verification`.

Return only valid UTF-8 JSON, with no Markdown and no comments.
```

## 2. Preparing gold use-cases

**Purpose:** obtain two independent sets of gold "word form -> lemma" pairs for building and testing the lemmatizer.

```text
You are a linguistic data curator. Prepare two disjoint sets of gold
use-cases for lemmatization of Modern Eastern Armenian: `development` and
`holdout`.

Use only sources that are already annotated, where the lemma is given by the
source and is not predicted by you. Prefer UD Armenian-ArmTDP in CoNLL-U
format: it has FORM, LEMMA, UPOS and FEATS, and its README states that
lemmas, UPOS and features are annotated manually. Do not use Western
Armenian treebanks: it is a different standard language. If you use another
source, state explicitly where its lemmas come from and its licence.

Algorithm:
1. Record the source: name, URL, version or commit, licence and the
   statement about the annotation type.
2. Read only syntactic words (lines whose ID is an integer). Skip
   multiword-token range lines (`3-4`) and empty nodes (`3.1`), and skip
   PUNCT, SYM, NUM and X.
3. Keep only non-trivial cases, where FORM differs from LEMMA after
   lower-casing (use str.lower(), not casefold(): case folding turns the
   ligature և into եւ). Keep the original capitalization of both FORM and LEMMA.
   Store sent_id and token_id so that every pair can be checked in the
   original corpus.
4. Take `development` only from the treebank's train split and `holdout`
   only from its test split, so that no sentence is in both sets. Select
   sentences with a fixed random seed, take at most three cases per
   sentence, and record the seed.
5. `development` must have at least 1000 cases; `holdout` at least 300.
   The holdout set must never be shown while the ontology, the lexicon or
   the code is written.
6. In each set count the cases by UPOS and by the main morphological
   features (Case, Number, Definite, VerbForm, Aspect, Voice). If the
   distribution is uneven, do not hide it.

Return two valid UTF-8 YAML files, `armenian-development.yaml` and
`armenian-holdout.yaml`, each with this structure:

language:
  name: Eastern Armenian
  iso639_3: hye
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
suspicious, keep it as is and add the field `annotation_note`. After writing
the files, check that the YAML parses, all cases are non-trivial, IDs are
unique and no sentence appears in both sets.
```

## 3. Building a rule-based lemmatizer

**Purpose:** generate a local Python lemmatizer from the ontology and the development set, without using the holdout set.

```text
You are a Python engineer and a specialist in Armenian morphology. Write one
file, `armenian_lemmatizer.py`, with the class `ArmenianLemmatizer`. Use only:

- `OntoArmenian.json`;
- the files listed in its `lexicon_files`;
- `armenian-development.yaml`;
- the Python 3.11+ standard library (plus PyYAML for reading YAML).

Never read `armenian-holdout.yaml`: it is reserved for independent
evaluation.

Required API:

class ArmenianLemmatizer:
    def __init__(self, ontology_path="OntoArmenian.json",
                 dev_path="armenian-development.yaml") -> None: ...
    def lemmatize(self, form: str, upos: str, features: str = "_") -> dict[str, str]: ...
    def lemmatize_sentence(self, tokens: list[dict]) -> list[dict]: ...

Requirements:
1. Load the rules, rule statuses, lemma conventions and lexical exceptions
   from the ontology; do not write an independent, incompatible list of
   rules in the code. Build the lexicon from all exceptions and paradigms in
   the ontology, from its `lexicon_files` and from the development set,
   keyed by (normalized form, UPOS).
2. Normalize before lookup: Unicode NFC, remove ՛ ՜ ՞, lower-case with
   str.lower() (never casefold(), which turns և into եւ), keep և and ու as
   they are. Return the lemma in lower case, except for PROPN, whose lemma keeps
   the initial capital letter; never lose letters that are known from the
   lexicon or a rule.
3. Apply in this order: exact lexicon entries, then the most specific rules
   (longest suffix chain, strictest feature conditions), then general rules.
   Inside one suffix layer the longest matching `rule` wins (-ներ before
   -եր, -ցրեց before -եց).
4. Apply nominal suffix rules only when the UD features agree with them
   (Case, Number, Definite, Person[psor]); when a feature requires a suffix
   (Case=Abl, Number=Plur, Definite=Def, Polarity=Neg for չ-, Mood=Cnd for
   կ-), the suffix or prefix must be stripped. Strip the suffix chain in the
   order given in the ontology. Do not strip suffixes without evidence.
5. A candidate lemma produced by a rule is accepted when it is in the
   lexicon with the same UPOS. If several candidates remain and the lexicon
   cannot decide, use the rule's `default_replacement` from the ontology if
   it has one and set `confidence="default"`. Otherwise, if a stem
   alternation (vowel reduction, -ել/-ալ class, declension class) cannot be
   resolved, return the form unchanged in `lemma`, set
   `confidence="ambiguous"` and explain why in `reason`; do not invent a
   lemma.
6. Follow the lemma conventions of the ontology: for Voice=Pass return the
   active verb (use the passive -> active pairs of the lexicon files when
   they exist); for AUX return only one of the lemmas the convention allows
   (եմ, լինել, տալ).
7. Support at least NOUN, PROPN, VERB, AUX, PRON, ADJ and DET. In
   `lemmatize_sentence` keep the original token, the lemma, the applied
   rule and the confidence: `exact`, `rule`, `lexicon`, `default` or
   `ambiguous`.
8. Add `evaluate(cases_path)` with exact-match accuracy and a breakdown by
   UPOS; it must write a CSV with form, expected, actual, UPOS, status and
   the reason for each error.
9. List the known limitations in the module docstring. Do not claim full
   lemmatization of Armenian without a full dictionary and full paradigms.

Every result of `lemmatize` must have exactly the fields `lemma`, `rule`,
`confidence` and `reason`. For example:

{"lemma": "գրել", "rule": "aorist_ec_to_el", "confidence": "rule", "reason": ""}

or, when the rule cannot be applied without a lexicon:

{"lemma": "գրքում", "rule": "", "confidence": "ambiguous", "reason": "vowel reduction in the stem: cannot restore the lemma without a lexicon"}

Because the development set is also part of the lexicon, scoring the
lemmatizer on it directly gives a meaningless 100%. Before answering, run a
5-fold cross-validation on the development set with folds split by
sentence (build the lexicon without the fold, score the fold), and report
accuracy and the number of errors by category. Fix errors only by changing
general rules or the ontology, never by adding single test words to code. Return only the content of the Python file, with no Markdown.
```

## 4. Independent evaluation of the lemmatizer

**Purpose:** measure the quality of the finished lemmatizer on the hidden set and produce a diagnostic report.

```text
You are an NLP evaluation engineer. You have:

- `armenian_lemmatizer.py`;
- `OntoArmenian.json` and the files in its `lexicon_files`;
- `armenian-development.yaml`;
- `armenian-holdout.yaml`.

Before the run, record SHA-256 hashes of the lemmatizer, the ontology and
both YAML files, and check them again before scoring. You must not change
any of them after you have seen any result. For every case run:

result = ArmenianLemmatizer().lemmatize(form, upos, features)
actual = result["lemma"]
passed = actual == lemma

Compare lemmas exactly, as Unicode strings in NFC; also report a second,
case-insensitive accuracy, but do not replace the exact one with it.

Create two files:

1. `armenian-evaluation-results.csv` with every case, without exception:
   sentence_id, token_id, form, expected, actual, upos, features, status,
   rule, confidence, reason.
2. `armenian-evaluation-report.md` with these sections:
   - source and version of the holdout set;
   - number of cases, correct answers, errors, exact-match accuracy and
     case-insensitive accuracy;
   - accuracy and number of cases by UPOS;
   - accuracy by form type where the features allow it (case, number,
     definiteness, verb form, voice);
   - how many cases were answered by the lexicon, by a rule, or returned as
     ambiguous, and the accuracy of each group;
   - at least the first 20 errors with ID, form, expected and actual lemma;
   - error groups: missing lexicon entry, stem vowel reduction, wrong verb
     class (-ել / -ալ), suppletive or irregular form, declension class,
     corpus lemma convention (passive, causative, auxiliary), capitalization,
     ambiguity, annotation error, other;
   - an ablation: the same lemmatizer built without the development set
     (ontology and lexicon files only), to show how much the result depends
     on corpus-derived lexicon;
   - limitations of the test and concrete next improvements.

Do not delete failed cases, do not correct the gold annotation and do not
round results in a way that hides errors. If the code does not run, that is
also a result: give the traceback and set accuracy to `not computed`.
```
