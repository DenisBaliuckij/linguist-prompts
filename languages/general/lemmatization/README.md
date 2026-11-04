# General · lemmatization (stage 3, any language)

One language-independent prompt for stage 3 of the lemmatization pipeline: it builds a Python lemmatizer and `lingua-rules` generation rules (Clingo/ASP) for any language from three inputs: an ontology from stage 1 (for example the UOG prompt), a development set of gold use-cases from stage 2 (UD treebank, FORM ≠ LEMMA), and optional lexicon files (for example UniMorph). Fill in the placeholders (`{{LANGUAGE}}`, `{{LANGUAGE_NATIVE}}`, `{{ISO3}}`, `{{ISO1}}`, `{{language}}`, `{{Language}}`, `{{lang}}`) and give the prompt to an agent that can run code; the holdout set stays hidden until evaluation.

The prompt is a revision of Olga Kuk's prompt from PR #23. Changes:
- the ontology is read-only; the agent transcribes it into a separate `{{language}}-computational-model.json`;
- rules go to `rules/{{lang}}_gen/`, other `rules/` and `tests/` directories are never touched;
- the lemmatizer works with an empty development set;
- Step 0 learns the corpus lemma conventions and lemma capitalisation;
- lexicon lemmas are converted to the corpus convention;
- a fixed application order with a statistical edit-script fallback at the end;
- design choices are decided by cross-validation on unseen forms;
- everything learned is rebuilt inside each CV fold (no leak);
- fixed rules for golden fixtures;
- a `features.yaml` example that passes lint.

Measured once per language (October 2026) on 15 languages: fin, tur, bua, jpn, tam, ara, cop, wol, quc, ind, rus, hin, ell, gle, kat. Setup: Claude Opus as an agent with code execution, stage 1 = UOG ontology, UD data with 1000 development and about 300 holdout words per language, plus a second independent holdout (holdout2) that was not used while revising the prompt. Mean exact match, %:

| Prompt | holdout | holdout2 | unseen forms (holdout) | without development set |
|---|---:|---:|---:|---:|
| PR #23 as is | 89.3 | 88.8 | 76.5 | not runnable |
| this prompt | 89.1 | 88.5 | 77.2 | 79.1 |

With the development set the accuracy is the same as #23 within run-to-run noise (about ±3 points on a single language). Without the development set this prompt works and keeps 79.1%; #23 cannot run without it. Weakest languages: Georgian (74.5%; verb lemmas are masdars that the lexicon does not give) and Japanese (81.8%; kanji lemmas for kana forms).
