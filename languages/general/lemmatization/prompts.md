# Prompt 3: Build the lemmatizer and its rules

## Role

You are a computational linguist and a Python engineer, a specialist in the morphology of `{{LANGUAGE}}` (`{{LANGUAGE_NATIVE}}`, ISO 639-3: `{{ISO3}}`, ISO 639-1: `{{ISO1}}`), and a contributor to the `lingua-rules` repository.

## Model requirements

This is the **agent version** of the prompt (the model runs code itself). A chat version without code execution exists separately: there the model only writes the files, and a person runs lint, tests and CV with the repository scripts and pastes the report back.

Context window ≥ 128k, ability to run code, ability to produce long structured outputs. If the output is too long for a single message, split the deliverable into parts — each part must be a complete artifact (a full file or a full report section), never a truncated or "demonstration" version.

## Task

Build **two artifacts** for `{{LANGUAGE}}`, both derived from the same ontology:

- **Artifact A — `lingua-rules` ASP rules** for inflection, in the Clingo/ASP format of the `lingua-rules` repository. These files contain **generation rules only** (lemma → form), tested by `lingua-rules lint` and golden-file tests.
- **Artifact B — a Python lemmatizer** that reads the ontology directly and implements analysis (form → lemma) in Python. It does **not** read the `.lp` files and does **not** query Clingo.

The two artifacts are **two separate systems that both derive from the ontology**. They must agree on the same suffix inventory, the same irregular-form list, the same word classes (`noun_class`, `verb_class`, `adj_class`), and the same feature keys (canonical order). Discrepancies are bugs: classify them as `rule mismatch` or `lemma-convention mismatch`. If `.lp` and the ontology disagree, **the ontology is the source of truth for analysis**.

## Inputs

Use only:

- `Onto{{LANGUAGE}}.json` — the ontology (from Prompt 1). **Read-only: never edit it.** Before writing any rule, transcribe everything the ontology states about inflection into a separate machine-readable file **`{{language}}-computational-model.json`**: full paradigm tables (one cell per feature bundle, with stem change and ending), declension/conjugation classes and how to recognise them from the lemma, closed-class full-form tables (pronouns, determiners, auxiliaries, copula, suppletive and irregular forms — every form the ontology lists), morphophonological rules (fleeting vowels, mutations, harmony, buffer segments), ending rules with their status, `default_replacement`, `lemma_conventions`, `composite_patterns`, `normalization` and `lexicon_files`. Each entry carries a `source` field with the ontology path it was transcribed from. If the ontology already has a machine-readable section (for example `lemmatization_interface`), start from it. Where the ontology is silent but a closed-class table or paradigm is standard grammar knowledge for `{{LANGUAGE}}`, you may add it with `"source": "model knowledge"`; never derive entries of this file from the development set (that is Step 0's job, in the conventions file). Both artifacts read this file. Record gaps and errors of the ontology in the report under "ontology defects".
- `{{language}}-development.yaml` — the development set (from Prompt 2).
- Lexicon files listed in the ontology or provided in the working directory.
- The `lingua-rules` repository: `README.md`, `README.ru.md` (sections on rule files, datasets, templates and golden-file tests), and the example files `rules/en/nouns.lp`, `rules/en/features.yaml`, `rules/en/lang.yaml`.

**Never read `{{language}}-holdout.yaml`** — it is reserved for Prompt 4.

## Environment and preconditions

- Python 3.11+, `clingo` ≥ 5.6, `PyYAML` ≥ 6.0, `lingua-rules` installed in editable mode.
- Verify first: `python -c "import clingo, yaml; print(clingo.__version__, yaml.__version__)"`. If any import fails, stop and report the exact error.
- Check before writing any code: the ontology exists and is valid JSON; the development set exists and is valid YAML with a `cases:` list (an empty list is allowed: log a warning and continue — the lemmatizer must then work from the ontology and lexicon files alone); the `lingua-rules` CLI is importable; `clingo` is importable.
- Write your rules to a new directory `rules/{{lang}}_gen/` (language code `{{lang}}_gen` for the CLI) and fixtures to `tests/{{lang}}_gen/`. **Never modify or delete any other directory under `rules/` or `tests/`**, including an existing `rules/{{lang}}_gen/`. If `rules/{{lang}}_gen/` exists but is not writable, stop and report the exact error.
- If any other precondition fails, stop and report the exact error. Do not write placeholder code.

## Outputs

### Artifact A — `lingua-rules`

```
rules/{{lang}}_gen/
  lang.yaml
  features.yaml
  <category>.lp   # one file per category
```

#### `lang.yaml`

Declare every category you write. Do not produce only `nouns.lp`. Example (for Russian; adapt the category list to `{{LANGUAGE}}`):

```yaml
name: Russian
iso639_3: rus
categories:
  - nouns
  - verbs
  - adjectives
  - pronouns
  - numerals
  - participles
  - gerunds
```

#### `features.yaml`

Declare **every** dimension and every value used in any `.lp` file. `lingua-rules lint` will fail on an undeclared dimension or value. Example (for Russian; adapt to the features that `{{LANGUAGE}}` actually has, as declared in the ontology):

```yaml
dimensions:
  case:      [nom, gen, dat, acc, ins, loc]
  number:    [sing, plur]
  gender:    [masc, fem, neut]
  animacy:   [anim, inan]
  aspect:    [imp, perf]
  tense:     [pres, past, fut]
  mood:      [ind, imp, sub]
  person:    [first, second, third]
  verbform:  [fin, inf, part, conv]
  voice:     [act, pass]
  degree:    [pos, cmp, sup]
  variant:   [short, long]
```

Do not include a dimension or value that `{{LANGUAGE}}` lacks according to the ontology.

**Value format:** every dimension name and value must be a lowercase ASCII identifier matching `[a-z][a-z0-9_]*` (no digits at the start, no `1`/`2`/`3` — use `first`/`second`/`third`). Quote any value YAML could read as a boolean or number (`"yes"`, `"no"`, `"on"`, `"off"`).

#### `.lp` files

Generation rules only, in the `lingua-rules` formalism. Two patterns you will use constantly:

**A rule that applies to any lemma not flagged irregular:**

```prolog
form(Lemma, "number=plural", @suffix(Lemma, "s")) :-
    input_lemma(Lemma),
    not irregular(Lemma).

irregular("child").
form("child", "number=plural", "children").
```

**A rule that applies only to a specific inflection class** (this is the pattern for fusional languages with many declension/conjugation classes; `noun_class/2` and `verb_class/2` are the mechanism):

```prolog
noun_class("школа", f_a).
form(L, "case=gen;number=sing", @strip_suffix_add(L, 1, "ы")) :-
    noun_class(L, f_a),
    not irregular(L).
```

Use the same shape for `verb_class/2` and `adj_class/2`. The class identifiers (`f_a`, `m_hard`, …) are yours to choose, but they must be declared consistently and must match the declension/conjugation classes in the ontology.

Other requirements:

- **Canonical order of feature keys**: sort dimensions by name and join with `;` (`number=plural;tense=past`).
- `irregular("x")` disables every rule with `not irregular(Lemma)` — for such lemmas, list every form explicitly.
- Helpers: `@suffix`, `@prefix`, `@strip_suffix_add`.
- `lingua-rules lint {{lang}}_gen` must pass without errors. This is a hard prerequisite before golden-file tests.
- **Do not** add reverse rules, `form_is/1`, `candidate_lemma/3`, or any analysis predicate. Analysis lives in Python (Artifact B).

### Artifact B — Python lemmatizer

File: `{{language}}_lemmatizer.py`, class `{{Language}}Lemmatizer` with:

```python
def __init__(self, ontology_path="Onto{{LANGUAGE}}.json",
             dev_path="{{language}}-development.yaml",
             rules_dir="rules/{{lang}}_gen") -> None: ...
def lemmatize(self, form: str, upos: str, features: str = "_") -> dict[str, str]: ...
def lemmatize_sentence(self, tokens: list[dict]) -> list[dict]: ...
def evaluate(self, cases_path: str) -> dict: ...
```

- **`__init__` failure modes**: if `rules_dir` is empty or has no `.lp` files, raise `FileNotFoundError` with a clear message; do not silently create an empty lemmatizer. If the ontology fails to load, raise. If the development set is missing or has an empty `cases:` list, log a warning and continue without it (the lemmatizer must still work).
- **How it works**: load `{{language}}-computational-model.json`, `{{language}}-lemma-conventions.json`, the development set (if any), and the files in `lexicon_files`; build a lexicon keyed by `(normalized_form, upos) → lemma`; train the **edit-script model** (see "Edit-script model" below) on the development set and the lexicon; find the lemma in the order given under "Application order"; rank candidates; fall back to the edit-script model → `confidence="default"`, and only when nothing has support → `ambiguous`.
- **The Python lemmatizer reads the ontology, not the `.lp` files, and does not query Clingo.** The development set is the primary source of lemma knowledge: when a form is in it, its lemma comes from there; otherwise, analysis falls back to the ontology rules. Accuracy on the development set therefore measures **coverage**, not rule quality. Rule quality is measured on the holdout (Prompt 4), which the lemmatizer never sees.
- **`features` parsing**: UD FEATS are pipe-separated (`Case=Nom|Number=Sing`). If `"_"` or `""` — treat as no features. Split on `"|"`, not on `","`. Split each part on `"="` once; skip parts without `"="`. Store as `dict[str, str]`. Do not raise on unknown feature names.
- **Lexicon sources**, in trust order: (1) the lexicon files; (2) lexical entries inside the ontology; (3) `{{language}}-development.yaml`. If `lexicon_files` is empty, log a warning and continue.
- **Result format** — exactly four fields: `lemma`, `rule`, `confidence`, `reason`.
- **`reason` must never be empty**: `exact` → `"exact match in development set"`; `lexicon` → `"lexicon analysis: <source>, other candidates: <list or 'none'>"`; `rule` → `"rule <id>: <short description>"`; `default` → `"default replacement: <rule id>, counts: <n>/<m>"`; `ambiguous` → `"no lexicon analysis and no unambiguous rule"`.
- **`lemmatize_sentence`**: do **not** mutate input token dicts. Copy each input dict, add `lemma`, `rule`, `confidence`, `reason`, return in the same order.
- **Composite forms**: recognised before per-token analysis. The shapes depend on `{{LANGUAGE}}`. **The following are examples for Russian, not universals** — for other languages, take the composite patterns from the ontology and use only those that `{{LANGUAGE}}` actually has:
  - Russian example: future imperfective (`буду` + infinitive), perfect/resultative (short passive participle + forms of `быть`), conditional/subjunctive (past form + `бы`), modal (`должен`/`нужно`/`надо` + infinitive).
  - For `{{LANGUAGE}}`, replace these with the composite patterns declared in `Onto{{LANGUAGE}}.json`. If the ontology declares none, do not invent any.
  - For every composite pattern: set the composite `rule` id on every participating token; set the main-verb lemma to the infinitive (or whatever the lemma convention prescribes); record the pattern in `reason` of the auxiliary token.
- **UPOS coverage**: at least `NOUN`, `PROPN`, `VERB`, `AUX`, `PRON`, `DET`, `ADJ`, plus indeclinable classes. Do not silently drop unknown UPOS.

## Application order

1. Exact entries of the development set: first `(form, UPOS, FEATS)`, then `(form, UPOS)`; take the most frequent lemma.
2. Morphological dictionary (lexicon files), with its lemmas converted to the corpus convention (see "Lexicon conversion"). If several lemmas match, rank by: feature compatibility with the token's FEATS → frequency of the lemma in the development set → frequency in the lexicon.
3. Exact entries of the paradigm tables, closed-class tables and irregular forms of the computational model.
4. Ending rules of the computational model (paradigm cells inverted: strip the cell's ending, undo its stem change, add the citation ending of the class) whose output is a known lemma (development set, converted lexicon, irregular) of a compatible UPOS.
5. Ending rules with status `rule`, and inverted paradigm cells whose class is recognisable from the form; rank them by specificity (longest ending, most features matched) and by how often each was correct on the training data.
6. `default_replacement`.
7. The **edit-script model** (below) — the last resort for forms that nothing above covers.
8. Return the form unchanged with `ambiguous` only when the edit-script model has no candidate with support ≥ 2, or when its best candidate is the identity.

Linguistic rules come before the statistical fallback: the edit-script model must never override a rule from steps 3–6 that applies to the form.

## Edit-script model

The edit-script model covers, from data, what the computational model does not. Build it from every `(form, lemma, UPOS)` pair available for training: the development set plus the converted lexicon.

- **Edit script** of a pair = `(strip_prefix, add_prefix, strip_suffix, add_suffix, casing)`, computed from the longest common substring of the lower-cased form and lemma; `casing` records how the lemma's capitalisation relates to the form's (kept / lowered / first letter upper). This also captures initial mutations, preverbs, prefixes and infixes adjacent to the stem edge.
- **Index**: for each UPOS and each form suffix of length 0…8 (and each form prefix of length 0…3 for prefixing or mutating languages, if the development set shows prefix changes), count the edit scripts observed. Optionally condition on one or two FEATS values (e.g. `VerbForm`, `Number`) when this improves cross-validation (b).
- **Prediction**: use the longest suffix (and prefix) context whose counts have support ≥ 2; pick the most frequent script that is applicable to the form (its `strip_*` strings match). If the result is a known lemma, prefer it over a more frequent script whose result is unknown. Report `"default replacement: edit script <script>, counts: <n>/<m>"`.
- The model is **derived data, not a hardcoded rule list**: it is computed at `__init__` from the development set and the lexicon files and must also work (from the lexicon alone) when the development set is empty.

## Lexicon conversion

In Step 0, compare the lexicon's lemma with the development-set lemma for every development form that the lexicon also contains (same UPOS). If they agree in < 90 % of these overlaps for a UPOS (e.g. the lexicon lists verbs under the 1sg present but the corpus under the masdar or infinitive; or diacritics differ), learn a lexicon-lemma → corpus-lemma edit script per UPOS from these overlaps, record it in `{{language}}-lemma-conventions.json`, and apply it to every lexicon lemma. If the conversion is imperfect, do not discard it: a partly right lemma source is often better than none. Decide by cross-validation (b) between (i) the converted lexicon as a lemma source at step 2, (ii) the converted lexicon as a candidate source ranked after the rules of steps 3–5, and (iii) the lexicon used only as a list of known forms; keep the option with the best (b) and report all three numbers. Apply the same rule to every other threshold or design choice you are unsure about: compare the options on (b) instead of fixing a cut-off in advance.

## Normalization and lemma spelling

Before lookup: Unicode NFC, plus the language-specific normalizations declared in the ontology. Do not apply normalizations the ontology does not declare. Lemma output: from the development set in corpus spelling when present; otherwise converted lexicon spelling. Capitalisation of lemmas follows what the development set shows per UPOS (Step 0 records it; e.g. whether `PROPN` lemmas keep the initial capital, whether sentence-initial capitals are lowered, whether mutated initials of proper names are restored); never lower-case by default.

## Lemma conventions

Apply `lemma_conventions` from the computational model, overridden by `{{language}}-lemma-conventions.json` learned from the development set (Step 0) where they disagree. Otherwise follow the ontology: non-finite forms under the verb when the corpus does so, deponents and passives under the convention's lemma, `AUX` only with the lemmas the convention allows, pronominal clitics under the lemma the convention prescribes. If paradigm tables list forms as separate lemmas but the corpus does not, skip those entries.

## Evaluation

`evaluate(cases_path)`:

- Exact-match accuracy; breakdown by UPOS.
- CSV `{{language}}-evaluation-results.csv` in the CWD (overwrite if it exists), with columns `form`, `expected`, `actual`, `UPOS`, `status`, `reason`. Return its absolute path under `csv_path`.
- `cases_path` is a YAML file in the `{{language}}-development.yaml` format.
- Use `sentence_id` + `token_id` to reconstruct sentences; report **token-level** and **sentence-level** accuracy.
- `by_confidence`: a dict mapping each confidence value to `{accuracy, total, correct}`.
- Return at least: `accuracy`, `accuracy_case_insensitive`, `sentence_accuracy`, `by_upos`, `by_confidence`, `errors`, `csv_path`.

## Execution and testing (CRITICAL — run before answering)

0. **Learn the corpus lemma conventions first, before writing any rule.** For every UPOS in the development set, compare the gold lemmas with the citation forms the ontology prescribes (`lemma_conventions`, paradigm citation cells, irregular lemmas): e.g. which form is the verb lemma (infinitive, masdar, bare stem, finite form), whether lemmas carry diacritics, which script variant they use, how pronouns, clitics, auxiliaries, proper nouns and comparatives are lemmatized. Record lemma capitalisation per UPOS, and run the lexicon comparison described under "Lexicon conversion". Write `{{language}}-lemma-conventions.json` with one entry per convention: `upos`, `ontology_says`, `corpus_does`, `counts` (n agreeing / n total), `examples`. Both artifacts must use this file. Report every convention where the corpus disagrees with the ontology.
1. **Write** all artifacts to disk. If `rules/{{lang}}_gen/` does not exist, create it first.
2. **Lint**: `python -m lingua_rules.cli.main lint {{lang}}_gen`. Fix `.lp` and re-run until it passes. Do not proceed to Step 3 while lint fails.
3. **Golden-file tests** — this tests **GENERATION** (lemma → form), not the lemmatizer. Build fixtures with this exact rule: take **every** development case whose UPOS belongs to a category in `lang.yaml` and whose lemma has a class fact or an `irregular` entry in your `.lp` files; map its UD features to your feature keys; skip it otherwise. Count skipped cases by reason, using exactly these reasons: `no_category`, `no_class`, `unmapped_features`, `conflicting_duplicate`. Report the counts and the pass rate over the fixtures built. Then run `python -m lingua_rules.cli.main test {{lang}}_gen`. Fix general rules only; do not add individual test words.
4. **5-fold cross-validation of the lemmatizer** — this tests **ANALYSIS** (form → lemma) and is the only step that measures whether the lemmatizer works. Split by `sentence_id` (all tokens of a sentence in the same fold); for each fold, build the lexicon, the learned conventions, the lexicon conversion and the edit-script model **from the training folds only** and score the fold (anything learned from the full development set leaks into CV). Report per-fold accuracy, mean accuracy, and errors by category. Report three numbers for every CV run: (a) accuracy on all tokens; (b) accuracy on tokens whose (form, UPOS) does not occur in the training folds; (c) **rules-only** accuracy, with the development-set lookup switched off (the lemmatizer built with an empty development set). Do not report a Step 3 number as if it were the lemmatizer's accuracy.
5. **Iterations (up to 3)**: classify errors (missing lexicon entry, wrong stem, wrong homograph analysis, buffer-vowel handling, composite pattern, lemma-convention mismatch, ranking error, rule mismatch, other), form a hypothesis per category, fix general rules, re-run lint → test → CV. **The ontology is read-only.** When fixing `rule mismatch` or `lemma-convention mismatch`, fix the shared source both artifacts read (`{{language}}-lemma-conventions.json` or one shared rule table derived from the ontology), then regenerate `.lp` and re-run Python analysis. Do not fix `.lp` and Python independently. Use (b) and (c) — not (a) — to judge whether a change improves the rules.
6. **Report** with numbers, not adjectives: files written (with byte sizes), exact lint command and output, golden-file pass/fail counts and names of failures, CV mean and per-fold accuracies (a), (b), (c) and error counts by category, the learned lemma conventions, ontology defects, what changed between iterations (before/after), and known limitations. Do not write "everything passed" without numbers; do not omit failed tests; if a step could not run, give the exact error and set the corresponding value to `not computed`.

## Anti-patterns

- Do not read `{{language}}-holdout.yaml`.
- Do not write an independent rule list in Python: generation rules live in `.lp`, analysis is derived from the ontology, and the Python lemmatizer reads neither a hardcoded list nor the `.lp` files.
- Do not add test words to the code.
- Do not tune to the development set — CV is split by `sentence_id`.
- Do not return the form unchanged by default. When nothing in steps 1–6 applies, output the best-supported edit script with `confidence="default"` and its counts; return the form with `ambiguous` only under the conditions in "Application order", step 8.
- Do not use the selection criteria written in the development set's header (for example `FORM != LEMMA`) as linguistic evidence: they describe how the sample was drawn, not the language.
- Do not claim full lemmatization — list the limitations in the docstring.
- Do not violate canonical feature-key order.
- Do not forget the all-or-nothing rule for `irregular(...)`.
- Do not query Clingo for `lemma/3` — the `.lp` files contain generation rules only.
- Do not truncate `.lp` files; split into parts if needed.
- Do not wrap code in Markdown.

## Known limitations

In the module docstring: which sources are covered (which dictionaries, how many lemmas), which categories are handled and which not, behaviour under `ambiguous`, behaviour under composite detection, which ontology rules are declared but not implemented, and an explicit note if the development file's sources are flagged as unused, corrupted, or heuristic.

## Output format

Return the contents of every `.lp` file, `lang.yaml`, `features.yaml`, `{{language}}_lemmatizer.py`, and a report on the runs. No Markdown around the code. If the deliverable is too long for one message, split it into consecutive parts and continue in the next message; never truncate.

## Connection to Prompts 4 and 5

- **Prompt 4** (evaluation): reads `{{language}}_lemmatizer.py` + `{{language}}-holdout.yaml`, runs `evaluate`, writes CSV + MD report. SHA-256 hashes before/after.
- **Prompt 5** (iterations): reads the Prompt 4 report, classifies errors, fixes `.lp` + ontology, re-runs Prompt 3, re-evaluates. Until convergence.

## Language-specific block: `{{LANGUAGE}}`

Fill in only what the ontology and the grammars attest. Do not invent facts to match the templates below. All examples in this block are **illustrations for Russian**; for other languages, take the corresponding facts from the ontology.

- **Homonymy facts.** List every ending and prefix of `{{LANGUAGE}}` that has two or more readings. For each reading, give one attested example in the ontology and one rule in `.lp`. Do not state a priority in `.lp` — let the lexicon decide.
  - Russian illustration: `-а` = fem. nom. sg. / neut. plur. / masc. gen. sg.; `не-` = negation prefix / lexicalized initial (`неделя`, `нельзя`, `некоторый`).
- **Buffer / epenthetic vowels.** State as facts the epenthetic vowels `{{LANGUAGE}}` inserts between stems and suffixes. Give at least three different attested examples per case; encode each as a rule, not as a procedural check.
  - Russian illustration: `-о-` in `сон` → `сна`, `-е-` in some verb stems.
- **Inflection classes.** Encode the declension and conjugation classes declared in the ontology as `noun_class/2`, `verb_class/2`, `adj_class/2` facts. The class names must match those in the ontology.
- **Irregular forms.** Load the irregular list from the ontology into `irregular(...)` facts in the corresponding `.lp` file and list every form explicitly. Do not leave an irregular lemma only under `not irregular(Lemma)`.
- **Suppletive comparatives and other suppletion.** Record as lexicon entries under `irregular(...)`, not as suffixation rules.
- **Aspectual / TAM pairs.** Record as lexicon data (`aspect_pair(Imp, Perf).` etc.), used only for analysis-side lemma selection.
- **Participles, gerunds, and other non-finite forms.** Encode as categories in `features.yaml` and as rules in the corresponding `.lp` files. Follow the ontology's lemma conventions (under the verb vs. separate lemmas).
- **Composite forms.** Encode as composite patterns in the Python lemmatizer, using the ontology's declarations; `lemmatize_sentence` recognises them before per-token analysis. If the ontology declares none for `{{LANGUAGE}}`, do not invent any.
- **Canonical feature-key order.** Always sort dimensions alphabetically and join with `;`. `features.yaml` must declare every dimension and value used, or `lint` will fail.
- **Typology reminder.** Read the ontology's `meta` and typology fields. If `{{LANGUAGE}}` is isolating, focus on syntax and the exception lexicon and set morphological stripping to `null` where the ontology says so. If it is polysynthetic, focus on verbal morphology and complex FST state routing. If it is fusional, focus on stem alternations and paradigm lookup tables. Do not force features the language lacks — use the ontology's `null` / `not_applicable` values instead.

## Final instruction

When you are given the name of a language, first state its morphological and phonological typology in one short paragraph, then produce the full contents of every `.lp` file, of `lang.yaml` and `features.yaml`, of `{{language}}_lemmatizer.py`, and a report on the runs. Without Markdown around the code. If the deliverable is too long for one message, split it into consecutive parts and continue in the next message; never truncate.
