You are a Python engineer and a specialist in Russian morphology.
Write one file, `russian_lemmatizer.py`, with the class
`RussianLemmatizer` (a small helper module for reading a dictionary
format is allowed). Use only:

- `OntoRUSSIAN.json`;
- the files listed in its `lexicon_files`;
- `russian-development.yaml`;
- the Python 3.11+ standard library (plus PyYAML for reading YAML).

Never read `russian-holdout.yaml`: it is reserved for independent
evaluation.

Required API:

```python
class RussianLemmatizer:
    def __init__(self, ontology_path="OntoRUSSIAN.json",
                 dev_path="russian-development.yaml") -> None: ...
    def lemmatize(self, form: str, upos: str, features: str = "_") -> dict[str, str]: ...
    def lemmatize_sentence(self, tokens: list[dict]) -> list[dict]: ...
```

Requirements:
1. Load the rules, rule statuses, lemma conventions, and lexical exceptions
   from the ontology; do not write an independent, incompatible list of
   rules in the code. Build the lexicon from the ontology, its
   `lexicon_files`, and the development set, keyed by (normalized form,
   UPOS).
2. Normalize before lookup: Unicode NFC, plus the language-specific
   normalizations declared in the ontology (diacritics, case, script
   variants, joiners, spaces inside words). Output the lemma in the
   spelling of the corpus when the development set contains it, otherwise
   in the lexicon spelling; PROPN lemmas keep the initial capital; other
   lexicon lemmas keep the case they have in the lexicon; rule outputs are
   lower case.
3. Apply in this order: exact entries of the development set, analysis with
   the morphological dictionary (stem + ending + class -> citation form),
   exact entries of the paradigm tables, ending rules confirmed by a known
   lemma, rules with status `rule`, then `default_replacement`.
4. When the dictionary gives several analyses, rank them by agreement with
   the target-corpus features, by UPOS, then by the frequency codes of the
   dictionary, then by how often the lemma occurs in the development set.
   Report the rejected lemmas in `reason`.
5. Follow the lemma conventions of the ontology: non-finite forms under the
   verb when the corpus does so, deponents and passives under the
   convention's lemma, AUX only with the lemmas the convention allows, and
   pronominal clitics attached to the lemma the convention prescribes. If
   the paradigm tables list forms as separate lemmas but the corpus does
   not, skip those entries.
6. If no lexicon and no unambiguous rule can decide, use the rule's
   `default_replacement` and set `confidence="default"`; otherwise return
   the form unchanged in `lemma`, set `confidence="ambiguous"`, and explain
   why in `reason`. Do not invent a lemma.
7. Support at least NOUN, PROPN, VERB, AUX, PRON, DET, ADJ, and the
   indeclinable classes (ADV, ADP, CCONJ, SCONJ) through the dictionary.
   In `lemmatize_sentence` keep the original token, the lemma, the applied
   rule, and the confidence: `exact`, `rule`, `lexicon`, `default`, or
   `ambiguous`.
8. Add `evaluate(cases_path)` with exact-match accuracy and a breakdown by
   UPOS; it must write a CSV with form, expected, actual, UPOS, status, and
   the reason for each error.
9. List the known limitations in the module docstring. Do not claim full
   lemmatization of Russian.

Every result of `lemmatize` must have exactly the fields `lemma`, `rule`,
`confidence`, and `reason`. For example:

```json
{"lemma": "example_lemma", "rule": "example_rule", "confidence": "lexicon", "reason": "other analyses: rejected"}
```

or, when nothing can decide:

```json
{"lemma": "form", "rule": "", "confidence": "ambiguous", "reason": "no lexicon analysis and no unambiguous rule"}
```

Because the development set is also part of the lexicon, scoring the
lemmatizer on it directly gives a meaningless 100%. Before answering, run
a 5-fold cross-validation on the development set with folds split by
sentence (build the lexicon and the learned conventions without the fold,
score the fold), and report accuracy and the number of errors by category.
Fix errors only by changing general rules, the ranking, or the ontology,
never by adding single test words to code. Return only the content of the
Python file(s), with no Markdown.