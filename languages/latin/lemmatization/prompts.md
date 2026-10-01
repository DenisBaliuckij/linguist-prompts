# Prompts: Latin · lemmatization

Run the four prompts in order. Each prompt is self-contained: start a new chat
for each stage and attach only the files listed under its inputs.

## 1. Building the Latin morphological ontology

**Purpose:** build a verifiable language-specific ontology from which a lemmatizer can take its rules, lemma conventions and lexical exceptions.

```text
You are a Latinist and a linguistic data engineer. Build one JSON file,
`OntoLatin.json`, for Classical and Late Latin (ISO 639-3: lat, ISO 639-1:
la). Work only with the attached sources. Do not add facts from memory and
do not invent rules, examples or references.

Input A: a general ontology of human language grammar (GOLD OntoLing).
Input B: the attached grammars, dictionaries and paradigm tables of Latin:
{{list of attached sources}}. A reference grammar (for example Allen and
Greenough's New Latin Grammar) and a machine-readable morphological
dictionary with principal parts (for example the DICTLINE and INFLECTS files
of Whitaker's Words) are strongly recommended.
Input C (optional): the annotation guidelines of the gold corpus that will be
used for evaluation (for example, the UD Latin documentation and the README
of the chosen treebank). Use it only for lemma conventions, never as a source
of test items.

Task: keep the sections of Input A that are compatible with Latin, but fill
them only with facts from Input B and Input C. Do not produce a reduced
demonstration ontology: transfer every fact and paradigm in Input B that is
relevant for lemmatization. The main goal of the file is to support a
working rule-based lemmatizer with the broadest coverage the sources allow.
The Morphology module must contain:

- parts of speech and the citation (dictionary) form of each one;
- the five noun declensions with their variants (i-stems, Greek nouns,
  neuters), all case endings by number and gender, and which endings are
  shared by several cells (-ae, -is, -i, -um, -e);
- the 3rd declension problem: the nominative is not predictable from the
  oblique stem (regis -> rex, corporis -> corpus, itineris -> iter), so these
  rules need the lexicon;
- adjectives of the 1st/2nd and 3rd declensions, comparison (-ior,
  -issimus, -limus, -rimus) and suppletive comparison (melior -> bonus);
- the four conjugations and mixed -io verbs; the present, perfect and
  supine systems; principal parts; deponent and semi-deponent verbs;
  irregular verbs (sum, possum, eo, fero, volo, nolo, malo, fio, edo) and
  syncopated perfects (amasti, audierunt);
- all non-finite forms (infinitives, participles, gerund, gerundive,
  supine) and which lemma they take;
- the personal, reflexive, possessive, demonstrative, relative,
  interrogative and indefinite pronoun paradigms as full "form -> lemma"
  tables;
- orthographic facts that affect matching: macrons and breves (remove them
  before lookup), i/j and u/v, assimilated prefixes (adp- / app-, inp- /
  imp-), the enclitics -que, -ne, -ve and whether the target corpus splits
  them, capitalization of proper names;
- every lemma convention of the target corpus (Input C) that differs from a
  plain dictionary form: participles, gerunds, gerundives and supines under
  the verb or as separate lemmas, deponents in -or, the AUX lemma, lemmas of
  comparatives and adverbs, spelling of the lemma (v or u, j or i);
- every condition under which a surface form is ambiguous and one rule is
  not enough.

For every rule record: an id, the input pattern, the output lemma or the
operation, the conditions (part of speech and morphological features,
written with the exact feature names of the target corpus, for example UD
`Case`, `Number`, `Gender`, `VerbForm`), at least one example
"form -> lemma" that is attested in Input B, the source, and a status:
`rule`, `lexicon_required` or `ambiguous`. If a rule has several possible
outputs (for example -orum -> -us or -um) and Input B contains a
machine-readable lexicon, count in that lexicon how often each output is
correct and record the counts; if one output covers at least 60% of at
least 10 attested forms, record it as `default_replacement` together with
the counts as evidence. Do not choose defaults from intuition. If a
machine-readable dictionary or paradigm table is part of Input B, do not
copy it into the JSON; register it in `lexicon_files` with its file name,
format, columns, licence, how a citation form is built from it, and the
lemma convention it follows (for example, whether it lists participles as
separate lemmas). Do not fill unknown data with plausible guesses: leave it
out and add a record to `gaps` with the reason.

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
use-cases for lemmatization of Latin: `development` and `holdout`.

Use only sources that are already annotated, where the lemma is given by the
source and is not predicted by you. Use one UD Latin treebank whose README
states that lemmas are manual or converted from manual annotation, for
example UD Latin-PROIEL (Vulgate, Caesar, Cicero, Palladius). Do not mix
treebanks in one experiment: UD Latin treebanks follow different lemma
conventions. State the period and genres of the texts. If you use another
source, state explicitly where its lemmas come from and its licence.

Algorithm:
1. Record the source: name, URL, version or commit, licence and the
   statement about the annotation type.
2. Read only syntactic words (lines whose ID is an integer). Skip
   multiword-token range lines (`3-4`) and empty nodes (`3.1`), and skip
   PUNCT, SYM, NUM and X.
3. Keep only non-trivial cases, where FORM differs from LEMMA after
   lower-casing with str.lower(). Keep the original capitalization of both
   FORM and LEMMA. Store sent_id and token_id so that every pair can be
   checked in the original corpus.
4. Take `development` only from the treebank's train split and `holdout`
   only from its test split, so that no sentence is in both sets. Select
   sentences with a fixed random seed, take at most three cases per
   sentence, and record the seed.
5. `development` must have at least 1000 cases; `holdout` at least 300.
   The holdout set must never be shown while the ontology, the lexicon or
   the code is written.
6. In each set count the cases by UPOS and by the main morphological
   features (Case, Number, Gender, VerbForm, Tense, Voice). If the
   distribution is uneven, do not hide it.

Return two valid UTF-8 YAML files, `latin-development.yaml` and
`latin-holdout.yaml`, each with this structure:

language:
  name: Latin
  iso639_3: lat
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
suspicious (placeholder lemmas such as `greek.expression`, alternatives such
as `hiem(p)s`), keep it as is and add the field `annotation_note`. After
writing the files, check that the YAML parses, all cases are non-trivial,
IDs are unique and no sentence appears in both sets.
```

## 3. Building a rule-based lemmatizer

**Purpose:** generate a local Python lemmatizer from the ontology and the development set, without using the holdout set.

```text
You are a Python engineer and a Latinist. Write one file,
`latin_lemmatizer.py`, with the class `LatinLemmatizer` (a small helper
module for reading a dictionary format is allowed). Use only:

- `OntoLatin.json`;
- the files listed in its `lexicon_files`;
- `latin-development.yaml`;
- the Python 3.11+ standard library (plus PyYAML for reading YAML).

Never read `latin-holdout.yaml`: it is reserved for independent evaluation.

Required API:

class LatinLemmatizer:
    def __init__(self, ontology_path="OntoLatin.json",
                 dev_path="latin-development.yaml") -> None: ...
    def lemmatize(self, form: str, upos: str, features: str = "_") -> dict[str, str]: ...
    def lemmatize_sentence(self, tokens: list[dict]) -> list[dict]: ...

Requirements:
1. Load the rules, rule statuses, lemma conventions and lexical exceptions
   from the ontology; do not write an independent, incompatible list of
   rules in the code. Build the lexicon from the ontology, its
   `lexicon_files` and the development set, keyed by (normalized form,
   UPOS).
2. Normalize before lookup: Unicode NFC, remove macrons and breves,
   lower-case, treat j = i and v = u when matching. Output the lemma in the
   spelling of the lexicon entry (without macrons, with i for j); PROPN
   lemmas keep the initial capital; other lexicon lemmas keep the case they
   have in the lexicon (Pharisaeus); rule outputs are lower case.
3. Apply in this order: exact entries of the development set, analysis with
   the morphological dictionary (stem + ending + class -> citation form),
   exact entries of the paradigm tables, then ending rules confirmed by a
   known lemma, then rules with status `rule`, then `default_replacement`.
4. When the dictionary gives several analyses, rank them by agreement with
   the UD features (Case, Number, Gender, VerbForm), by UPOS (an ADJ entry
   for ADJ, a participle for VerbForm=Part), then by the frequency codes of
   the dictionary, then by how often the lemma occurs in the development
   set. Report the rejected lemmas in `reason`.
5. Follow the lemma conventions of the ontology: non-finite forms under the
   verb when the corpus does so, deponents in -or, AUX only with the lemmas
   the convention allows (sum). If the paradigm tables list participles as
   separate lemmas but the corpus does not, skip those entries.
6. If no lexicon and no unambiguous rule can decide, use the rule's
   `default_replacement` and set `confidence="default"`; otherwise return
   the form unchanged in `lemma`, set `confidence="ambiguous"` and explain
   why in `reason`. Do not invent a lemma.
7. Support at least NOUN, PROPN, VERB, AUX, PRON, DET, ADJ and the
   indeclinable classes (ADV, ADP, CCONJ, SCONJ) through the dictionary. In
   `lemmatize_sentence` keep the original token, the lemma, the applied
   rule and the confidence: `exact`, `rule`, `lexicon`, `default` or
   `ambiguous`.
8. Add `evaluate(cases_path)` with exact-match accuracy and a breakdown by
   UPOS; it must write a CSV with form, expected, actual, UPOS, status and
   the reason for each error.
9. List the known limitations in the module docstring. Do not claim full
   lemmatization of Latin.

Every result of `lemmatize` must have exactly the fields `lemma`, `rule`,
`confidence` and `reason`. For example:

{"lemma": "facio", "rule": "whitaker", "confidence": "lexicon", "reason": "other analyses: ['fio']"}

or, when nothing can decide:

{"lemma": "Ptolomaida", "rule": "", "confidence": "ambiguous", "reason": "no lexicon analysis and no unambiguous rule"}

Because the development set is also part of the lexicon, scoring the
lemmatizer on it directly gives a meaningless 100%. Before answering, run a
5-fold cross-validation on the development set with folds split by
sentence (build the lexicon without the fold, score the fold), and report
accuracy and the number of errors by category. Fix errors only by changing
general rules, the ranking or the ontology, never by adding single test
words to code. Return only the content of the Python file(s), with no
Markdown.
```

## 4. Independent evaluation of the lemmatizer

**Purpose:** measure the quality of the finished lemmatizer on the hidden set and produce a diagnostic report.

```text
You are an NLP evaluation engineer. You have:

- `latin_lemmatizer.py` (and its helper module, if any);
- `OntoLatin.json` and the files in its `lexicon_files`;
- `latin-development.yaml`;
- `latin-holdout.yaml`.

Before the run, record SHA-256 hashes of the code, the ontology and both
YAML files, and check them again before scoring. You must not change any of
them after you have seen any result. For every case run:

result = LatinLemmatizer().lemmatize(form, upos, features)
actual = result["lemma"]
passed = actual == lemma

Compare lemmas exactly, as Unicode strings in NFC; also report a second,
case-insensitive accuracy, but do not replace the exact one with it.

Create two files:

1. `latin-evaluation-results.csv` with every case, without exception:
   sentence_id, token_id, form, expected, actual, upos, features, status,
   rule, confidence, reason.
2. `latin-evaluation-report.md` with these sections:
   - source and version of the holdout set;
   - number of cases, correct answers, errors, exact-match accuracy and
     case-insensitive accuracy;
   - accuracy and number of cases by UPOS;
   - accuracy by form type where the features allow it (case, number,
     verb form, voice);
   - how many cases were answered by the lexicon, by a rule, by a default
     or returned as ambiguous, and the accuracy of each group;
   - all errors with ID, form, expected and actual lemma;
   - error groups: missing lexicon entry, wrong analysis of a homograph,
     spelling variant between dictionary and corpus (assimilation, ae/e,
     i/j), corpus lemma convention, pronoun paradigm, capitalization,
     annotation (placeholder or alternative lemma), other;
   - an ablation: the same lemmatizer built without the development set
     (ontology and lexicon files only), to show how much the result depends
     on corpus-derived lexicon;
   - limitations of the test and concrete next improvements.

Do not delete failed cases, do not correct the gold annotation and do not
round results in a way that hides errors. If the code does not run, that is
also a result: give the traceback and set accuracy to `not computed`.
```
