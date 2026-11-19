## Промпт 4. Независимая оценка арабского лемматизатора

**Назначение:** получить проверку фиксированной версии и отчёт об ошибках.

````text
You are an NLP evaluation engineer. You have:

- `arabic_lemmatizer.py`;
- `OntoArabic.json` and the files in its `lexicon_files`;
- `arabic-development.yaml`;
- `arabic-holdout.yaml`.

Before the run, record SHA-256 hashes of the lemmatizer, the ontology and
both YAML files, and check them again before scoring. You must not change
any of them after you have seen any result. For every case run:

result = ArabicLemmatizer().lemmatize(form, upos, features)
actual = result["lemma"]
passed = actual == lemma

Compare lemmas exactly, as Unicode strings in NFC; also report a second,
case-insensitive accuracy, but do not replace the exact one with it.

Create two files:

1. `arabic-evaluation-results.csv` with every case, without exception:
   sentence_id, token_id, form, expected, actual, upos, features, status,
   rule, confidence, reason.
2. `arabic-evaluation-report.md` with these sections:
   - source and version of the holdout set;
   - number of cases, correct answers, errors, exact-match accuracy and
     case-insensitive accuracy;
   - accuracy and number of cases by UPOS;
   - accuracy by form type where the features allow it (case, number,
     definiteness, verb form, voice);
   - how many cases were answered by the lexicon, by a rule, or returned as
     ambiguous, and the accuracy of each group;
   - at least the first 20 errors with ID, form, expected and actual lemma;
   - error groups: missing lexicon entry, wrong stem, wrong homograph
     analysis, buffer-vowel handling, composite pattern, lemma-convention
     mismatch, ranking error, rule mismatch, annotation error, other;
   - an ablation: the same lemmatizer built without the development set
     (ontology and lexicon files only), to show how much the result depends
     on corpus-derived lexicon;
   - limitations of the test and concrete next improvements.

Do not delete failed cases, do not correct the gold annotation and do not
round results in a way that hides errors. If the code does not run, that is
also a result: give the traceback and set accuracy to `not computed`.

## Chat mode (added for this run)

You cannot run code or open files in this chat. Write one self-contained script
`evaluate_arabic.py` (Python 3.12 standard library + PyYAML) that does everything
above when the person runs it from the folder that holds these files, and writes both
files. Facts about the files:

- Both YAML files have a top-level `meta` mapping and a `cases` list; each case has
  `sentence_id`, `token_id`, `form`, `lemma`, `upos`, `feats` (a UD feature string or `_`).
- The constructor is `ArabicLemmatizer(ontology_path="OntoArabic.json",
  dev_path="arabic-development.yaml", ...)`; other parameters have defaults. For the
  ablation, write a development file with `cases: []` and pass it as `dev_path`.
- `lemmatize(form, upos, features)` returns a dict with `lemma` and usually `rule`,
  `confidence` and `reason`; use `reason` to tell lexicon answers from rule answers.

Return only the script, wrapped as `=== FILE: evaluate_arabic.py ===` … `=== END FILE ===`.
````

## Промпт 5. Доработка по отчёту

**Назначение:** исправить общие правила по результатам проверки. Сохранён полный запрос, включая отчёт конкретного прогона.

````text
**Prompt 5** (iterations): reads the Prompt 4 report, classifies errors, fixes `.lp` + ontology, re-runs Prompt 3, re-evaluates. Until convergence.

## Chat mode (added for this run)

You cannot run code here; the person ran the Prompt 4 evaluation of your current files on the
holdout set. Its report is below. Do Prompt 5 now: classify the errors, form a hypothesis per
class, fix general rules in `arabic-computational-model.json` and
`arabic_lemmatizer.py` (and the ontology only where it is wrong), and return the full
corrected files in the same `=== FILE: name ===` … `=== END FILE ===` format. The person will
re-evaluate them. Do not add entries for individual holdout words.

## Prompt 4 report

# Arabic Lemmatizer Evaluation Report

## 1. Source and version of the holdout set

- File: `arabic-holdout.yaml`
- `meta` block:
    - `language`: Arabic
    - `iso639_3`: ara
    - `source`: UD_Arabic-PADT
    - `seed`: 20261111
    - `split`: by sentence
    - `excluded_upos`: ['PUNCT', 'SYM']
    - `set`: holdout

- Holdout SHA-256: `c31f6aa34def07ae51951dbc73645d446bfb60e3065ec34ed227cf3ba9e7029c`
- Lemmatizer SHA-256: `6db09e7b9c48dfce26437436da709a17e80121a52f4144c63f467a58a88a7f1c`
- Ontology SHA-256: `5bb3e138e18e4e0a58891d8b98744a41c1e4242ca036d1890d231623d2cb7479`
- Development SHA-256: `0a915b2453967cc26ad3961e8b4a8e32077a2c7d2a46305f03c2fea0f3360357`

## 2. Totals

- Number of cases: 327
- Correct answers (exact): 168
- Errors: 159
- Exact-match accuracy: 51.38%
- Case-insensitive accuracy: 51.38%

## 3. Accuracy by UPOS

| UPOS | cases | correct | accuracy |
|------|-------|---------|----------|
| ADJ | 45 | 15 | 33.33% |
| ADP | 49 | 44 | 89.80% |
| AUX | 2 | 1 | 50.00% |
| CCONJ | 21 | 20 | 95.24% |
| DET | 8 | 8 | 100.00% |
| NOUN | 123 | 30 | 24.39% |
| NUM | 7 | 6 | 85.71% |
| PART | 1 | 1 | 100.00% |
| PRON | 11 | 11 | 100.00% |
| SCONJ | 8 | 7 | 87.50% |
| VERB | 35 | 9 | 25.71% |
| X | 17 | 16 | 94.12% |

## 4. Accuracy by form type

### Case

| value | cases | correct | accuracy |
|-------|-------|---------|----------|
| Acc | 39 | 14 | 35.90% |
| Gen | 119 | 36 | 30.25% |
| Nom | 33 | 15 | 45.45% |

### Number

| value | cases | correct | accuracy |
|-------|-------|---------|----------|
| Dual | 2 | 1 | 50.00% |
| Plur | 42 | 5 | 11.90% |
| Sing | 179 | 66 | 36.87% |

### Definiteness

| value | cases | correct | accuracy |
|-------|-------|---------|----------|
| Cons | 47 | 9 | 19.15% |
| Def | 88 | 29 | 32.95% |
| Ind | 35 | 8 | 22.86% |

### Verb form

| value | cases | correct | accuracy |
|-------|-------|---------|----------|
| Fin | 14 | 2 | 14.29% |

### Voice

| value | cases | correct | accuracy |
|-------|-------|---------|----------|
| Act | 31 | 9 | 29.03% |
| Pass | 5 | 0 | 0.00% |

## 5. Answer-source breakdown

| source | cases | correct | accuracy |
|--------|-------|---------|----------|
| lexicon | 9 | 6 | 66.67% |
| rule | 227 | 158 | 69.60% |
| ambiguous | 91 | 4 | 4.40% |

_Classification: 'ambiguous' when `reason`/`rule` mentions ambiguity; 'lexicon' when `reason` mentions lexicon/dictionary lookup; 'rule' when a rule name is present in `rule`/`reason`; 'error' for raised exceptions; 'other' when no signal is present._

## 6. First 20 errors

| # | sentence_id | token_id | form | expected | actual |
|---|-------------|----------|------|----------|--------|
| 1 | alhayat.20011225.0099:p1u1 | 2 | المصرية | مِصرِيّ | مصرية |
| 2 | alhayat.20011225.0099:p1u1 | 3 | تتجه | اِتَّجَه | تتجه |
| 3 | alhayat.20011225.0099:p1u1 | 5 | التراجع | تَرَاجُع | تراجع |
| 4 | alhayat.20011225.0099:p1u1 | 7 | مطالبة | مُطَالَبَة | مطالبة |
| 5 | alhayat.20011225.0099:p1u1 | 8 | المصارف | مَصرِف | مصارف |
| 6 | alhayat.20011225.0099:p1u1 | 10 | خفض | خَفض | خفض |
| 7 | alhayat.20011225.0099:p1u1 | 11 | الفائدة | فَائِدَة | فايدة |
| 8 | alhayat.20011225.0099:p1u1 | 13 | الودائع | وَدِيعَة | ودايع |
| 9 | ummah.20040715.0039:p1u1 | 1 | إسرائيل | إِسرَائِيل | إسرائيل |
| 10 | ummah.20040715.0039:p1u1 | 3 | شراء | شِرَاء | شراء |
| 11 | ummah.20040715.0039:p1u1 | 5 | الطبيعي | طَبِيعِيّ | طبيعي |
| 12 | alhayat.20010911.0008:p19u1 | 5 | التخطيط | تَخطِيط | تخطيط |
| 13 | alhayat.20010911.0008:p19u1 | 6 | المبكر | مُبَكِّر | مبكر |
| 14 | alhayat.20010911.0008:p19u1 | 8 | جانب | جَانِب | جانب |
| 15 | alhayat.20010911.0008:p19u1 | 9 | المنـــظمات | مُنَظَّمَة | منظمات |
| 16 | alhayat.20010911.0008:p19u1 | 11 | المراكز | مَركَز | مراكز |
| 17 | alhayat.20010911.0008:p19u1 | 17 | انفتاح | اِنفِتَاح | انفتاح |
| 18 | alhayat.20010911.0008:p19u1 | 20 | المنظمات | مُنَظَّمَة | منظمات |
| 19 | alhayat.20010911.0008:p19u1 | 23 | التجمعات | تَجَمُّع | تجمعات |
| 20 | alhayat.20010911.0008:p19u1 | 24 | الإقلـــيمية | إِقلِيمِيّ | اقليمية |

## 7. Error groups

| group | count |
|-------|-------|
| missing lexicon entry | 0 |
| wrong stem | 0 |
| wrong homograph analysis | 1 |
| buffer-vowel handling | 0 |
| composite pattern | 0 |
| lemma-convention mismatch | 0 |
| ranking error | 0 |
| rule mismatch | 158 |
| annotation error | 0 |
| other | 0 |

_Groups are assigned heuristically from the lemmatizer's `reason`/`rule` text and from shape comparison of expected vs actual lemma._

## 8. Ablation: lemmatizer built without the development set

An empty development file `_ablation_dev_empty.yaml` (`cases: []`) was passed as `dev_path`; the ontology and lexicon files were unchanged.

- Full-system exact accuracy: 51.38% (168/327)
- Ablated exact accuracy: 21.71% (71/327)
- Delta (full - ablated): 29.66%

_This measures how much the corpus-derived development lexicon contributes on top of the ontology/lexicon files._

## 9. Limitations of the test and next improvements

- Single holdout file: results depend on the composition of this split; no confidence intervals are reported.
- Error groups are heuristic and derived from lemmatizer metadata, not from manual inspection.
- The ablation only removes the development set; other corpus-derived resources (if any) remain.
- Case-insensitive accuracy is informational only and must not replace the exact-match metric.

Concrete next improvements:

- Add per-UPOS and per-feature gold coverage to balance the holdout.
- Manually review the first 50 errors and refine the error-group labels.
- Extend the ablation to disable rule subsystems and lexicon subsets.
- Add regression tests to prevent reintroducing the top error groups.

## Hash verification

All source hashes unchanged (before scoring).

All source hashes unchanged (after scoring).
````
