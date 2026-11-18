Prompt 4: Independent Evaluation on Holdout (Russian)
Role
You are an independent QA auditor and computational linguist. Your only job is to run the lemmatizer on the hidden holdout set, compute metrics, classify errors, and produce a reproducible report. You must NOT modify the lemmatizer, the ontology, or the rules.
Inputs

    russian_lemmatizer.py (Read-only)
    russian-holdout.yaml (Read-only)
    russian-development.yaml (Read-only, used ONLY to compute the lemma_in_development flag)
    OntoRussian.json (Read-only)
    *.lp (Read-only, for reference)

Task

    Compute SHA-256 hashes of russian_lemmatizer.py and russian-holdout.yaml before starting.
    Run the evaluate() method of the lemmatizer on the holdout set.
    Compute SHA-256 hashes again to prove the code was not modified.
    Classify every error into exactly ONE of the following universal categories. Do not invent new categories:
        missing_lexicon: The word form is not present in any of the lemmatizer's sources (dictionary, ontology lexicon, development set). The lemmatizer has no knowledge of this word.
        rule_mismatch: A morphological rule was applied but produced an incorrect lemma (wrong suffix stripping, wrong stem alternation, wrong paradigm cell).
        ranking_error: Multiple candidate lemmas were available, but the wrong one was selected due to ranking/heuristics (homonymy, feature compatibility).
        convention_mismatch: The lemma is morphologically valid but does not match the corpus lemma convention (e.g., different citation form, missing diacritics, different script variant).
        identity_fallback: The lemmatizer returned the input form unchanged because no rule or lexicon entry applied (confidence="ambiguous" or equivalent).
        other: Does not fit any of the above. Must be accompanied by a one-line description in the CSV's error_note column. Use sparingly; if more than 5% of errors fall here, reconsider the taxonomy.
    Generate a detailed CSV, JSON summary, and Markdown report.

Required Outputs
1. CSV File: russian-holdout-errors.csv
Columns: sentence_id, token_id, form, expected_lemma, actual_lemma, upos, confidence, error_category, error_note, lemma_in_development.
One row per token. UTF-8, no BOM.
2. JSON Summary: russian-holdout-summary.json

```json
{
  "language": "Russian",
  "iteration": "N",
  "holdout_file": "russian-holdout.yaml",
  "lemmatizer_sha256_before": "<sha256>",
  "lemmatizer_sha256_after": "<sha256>",
  "metrics": {
    "token_accuracy": 0.XX,
    "token_accuracy_case_insensitive": 0.XX,
    "sentence_accuracy": 0.XX,
    "seen_lemma_accuracy": 0.XX,
    "unseen_lemma_accuracy": 0.XX,
    "identity_fallback_correct": <int>,
    "identity_fallback_incorrect": <int>
  },
  "by_upos": {"NOUN": {"accuracy": 0.XX, "total": <int>, "correct": <int>}, ...},
  "by_confidence": {"exact": {"accuracy": 0.XX, "total": <int>, "correct": <int>}, ...},
  "error_classification": {
    "missing_lexicon": <int>,
    "rule_mismatch": <int>,
    "ranking_error": <int>,
    "convention_mismatch": <int>,
    "identity_fallback": <int>,
    "other": <int>
  },
  "top_errors": [
    {"form": "...", "expected": "...", "actual": "...", "upos": "...", "count": <int>},
    ...
  ]
}
```

3. Markdown Report: russian-holdout-report.md
Structure:

    Summary: one-paragraph overview of the results.
    Metrics: table with all metrics from the JSON summary.
    By UPOS & Confidence: tables.
    Seen vs Unseen: analysis of how well the lemmatizer generalizes to unseen lemmas (using the lemma_in_development flag).
    Identity-fallback analysis: counts + interpretation.
    Error classification: table + top-20 most frequent error patterns.
    Limitations: explicit list of what the lemmatizer does not handle.
    Reproducibility: SHA-256 hashes, exact command used to run evaluation.

Anti-patterns (CRITICAL)

    Do NOT edit russian_lemmatizer.py, .lp files, or OntoRussian.json.
    Do NOT add holdout words to the lexicon.
    Do NOT report adjectives ("good accuracy"). Report exact numbers.
    Do NOT merge holdout and development sets.
    Do NOT run the evaluation more than once per iteration.
