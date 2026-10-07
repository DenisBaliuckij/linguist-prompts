## Role

You are a Python engineer and a specialist in `{{LANGUAGE}}` morphology.

## Task

Write one file, `{{language}}_lemmatizer.py`, with the class `{{Language}}Lemmatizer` (a small helper module for reading dictionary formats is allowed).

## Allowed data sources

Use only:

- `Onto{{LANGUAGE}}.json`;
- the files listed in its `lexicon_files`;
- `{{language}}-development.yaml`;
- the Python 3.11+ standard library (plus PyYAML for reading YAML).

**Never read `{{language}}-holdout.yaml`:** it is reserved for independent evaluation.

## Required API

```python
class {{Language}}Lemmatizer:
    def __init__(self,
                 ontology_path: str = "Onto{{LANGUAGE}}.json",
                 dev_path: str = "{{language}}-development.yaml") -> None: ...

    def lemmatize(self, form: str, upos: str, features: str = "_") -> dict[str, str]: ...

    def lemmatize_sentence(self, tokens: list[dict]) -> list[dict]: ...

    def evaluate(self, cases_path: str) -> dict: ...
```

Each token in `lemmatize_sentence` is a dict with at least the keys `form`, `upos`, and optionally `features`, `sentence_id`, `token_id`. The output list must preserve the original token dict and add the keys `lemma`, `rule`, `confidence`, `reason`.

## Requirements

### 1. Load rules and lexicon

Load the rules, rule statuses, lemma conventions, and lexical exceptions from the ontology; do not write an independent, incompatible list of rules in the code. Build the lexicon from the ontology, its `lexicon_files`, and the development set, keyed by `(normalized_form, upos)`. A single `(form, upos)` key may map to **multiple lemmas**; store all candidates together with their source and the raw `features` string.

### 2. Normalize before lookup

Normalize before lookup: Unicode NFC, plus the language-specific normalizations declared in the ontology (diacritics, case, script variants, joiners, spaces inside words). **Do not** apply any normalization that the ontology does not declare.

### 3. Lemma spelling in the output

Output the lemma in the spelling of the corpus when the development set contains it, otherwise in the lexicon spelling; `PROPN` lemmas keep the initial capital; other lexicon lemmas keep the case they have in the lexicon; rule outputs are lower case.

### 4. Application order

Apply in this order:

1. Exact entries of the development set.
2. Analysis with the morphological dictionary (stem + ending + class → citation form).
3. Exact entries of the paradigm tables.
4. Ending rules confirmed by a known lemma.
5. Rules with status `rule`.
6. `default_replacement`.

### 5. Ranking multiple analyses

When the dictionary gives several analyses, rank them by agreement with the target-corpus features, by UPOS, then by the frequency codes of the dictionary, then by how often the lemma occurs in the development set. Report the rejected lemmas in `reason`.

### 6. Lemma conventions

Follow the lemma conventions of the ontology: non-finite forms under the verb when the corpus does so, deponents and passives under the convention's lemma, `AUX` only with the lemmas the convention allows, and pronominal clitics attached to the lemma the convention prescribes. If the paradigm tables list forms as separate lemmas but the corpus does not, skip those entries.

### 7. Ambiguity

If no lexicon and no unambiguous rule can decide, use the rule's `default_replacement` and set `confidence="default"`; otherwise return the form unchanged in `lemma`, set `confidence="ambiguous"`, and explain why in `reason`. Do not invent a lemma.

### 8. Supported UPOS

Support at least NOUN, PROPN, VERB, AUX, PRON, DET, ADJ, and the indeclinable classes (ADV, ADP, CCONJ, SCONJ) through the dictionary. In `lemmatize_sentence` keep the original token, the lemma, the applied rule, and the confidence: `exact`, `rule`, `lexicon`, `default`, or `ambiguous`.

### 9. Evaluation

Add `evaluate(cases_path)` with exact-match accuracy and a breakdown by UPOS; it must write a CSV with `form`, `expected`, `actual`, `UPOS`, `status`, and the reason for each error. `cases_path` is a YAML file in the same format as `{{language}}-development.yaml` (with a top-level `cases:` list). Use `sentence_id` + `token_id` to reconstruct sentences for `lemmatize_sentence` scoring, and also report token-level accuracy.

### 10. Known limitations

List the known limitations in the module docstring. Do not claim full lemmatization of `{{LANGUAGE}}`. Explicitly mention anything that the development file's `sources` notes as unused, corrupted, or heuristic.

### 11. Result format

Every result of `lemmatize` must have exactly the fields `lemma`, `rule`, `confidence`, and `reason`. For example:

```json
{"lemma": "{{EXAMPLE_LEMMA}}", "rule": "{{EXAMPLE_RULE}}", "confidence": "lexicon", "reason": "other analyses: {{REJECTED}}"}
```

or, when nothing can decide:

```json
{"lemma": "{{FORM}}", "rule": "", "confidence": "ambiguous", "reason": "no lexicon analysis and no unambiguous rule"}
```

### 12. Cross-validation before answering

Because the development set is also part of the lexicon, scoring the lemmatizer on it directly gives a meaningless 100%. Before answering, run a **5-fold cross-validation** on the development set with folds split by `sentence_id` (build the lexicon and the learned conventions without the fold, score the fold), and report accuracy and the number of errors by category. Fix errors only by changing general rules, the ranking, or the ontology, never by adding single test words to code.

### 13. Output format

Return only the content of the Python file(s), with no Markdown.
