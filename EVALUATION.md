# Prompt Evaluation Metrics

This document defines how prompts in this repository are evaluated. It is the
rubric reviewers apply when assessing a prompt in a pull request.

There are two rubrics. The **General Metrics** apply to any `lingua-rules`-style
prompt (prompts that produce logic rules and datasets). The **Universal
Lemmatizer Metrics** apply to prompts that build or drive a cross-lingual
lemmatizer. Each criterion carries a weight; the weights within each rubric sum
to 100%. The "How to measure" checklist under each criterion lists the concrete
questions a reviewer should answer.

Each criterion also lists **Mandatory (blocking)** and **Desirable (improving)**
requirements. A mandatory requirement (`M`-prefixed) is a hard gate: a prompt
that fails any one of them fails the criterion regardless of its score
elsewhere. A desirable requirement (`D`-prefixed) improves the score but is not
blocking. Requirements marked "(new)" were added in response to reviewer
feedback on this rubric.

---

## General Metrics

### 1. Rule-Logic Fidelity — Weight 25%

Measures the degree to which the prompt specifies rules as pure logic
(ASP/Clingo-style) rather than as procedural code or ad-hoc string manipulation.
`lingua-rules` mandates that rule files (`.lp`) contain logic only; all lexical
data (exceptions, paradigms, word lists) must reside in separate TSV datasets. A
prompt that conflates logic with data violates the core design.

How to measure:

- Presence of ASP/Clingo constructs: does the prompt require the tool to generate
  or interpret Clingo facts and rules (e.g. `form(Lemma, "number=plural", @suffix(Lemma, "s"))`)?
- Data–logic separation: does the prompt explicitly instruct that irregular forms,
  class memberships, and paradigm tables be stored in separate datasets rather
  than hard-coded in the logic?
- Does the prompt restrict string operations to the sanctioned helpers (`@suffix`,
  `@prefix`, `@strip_suffix_add`, `@affix`) instead of arbitrary Python string methods?

Mandatory (blocking):

- **M1.1 — Logic, not procedures.** The prompt must require that rule files
  (`.lp`) contain declarative logic only, with no imperative control flow and no
  ad-hoc string manipulation.
- **M1.2 — Data–logic separation.** The prompt must explicitly require that
  irregular forms, class memberships, and paradigm tables be stored in separate
  TSV datasets rather than hard-coded in the logic.
- **M1.3 — Sanctioned helpers only.** The prompt must restrict string operations
  to the sanctioned helpers (`@suffix`, `@prefix`, `@strip_suffix_add`, `@affix`)
  and forbid arbitrary Python string methods.
- **M1.4 — Negative constraints (new).** The prompt must explicitly forbid the
  generation of rules that do not parse under Clingo. Concretely, it must (a)
  require every candidate rule to be validated by the Clingo parser before being
  accepted into the rule set, (b) require that any rule producing a parse error,
  an unsafe variable, or an undeclared predicate be rejected rather than silently
  emitted, and (c) specify that rejection is a hard failure of the generation
  step, not a warning. A prompt that allows unparseable rules to reach the output
  fails this criterion.

Desirable (improving):

- **D1.1 — Explicit Clingo constructs.** The prompt demonstrates or requires
  Clingo facts and rules in canonical form (e.g. `form(Lemma, "number=plural", @suffix(Lemma, "s"))`).
- **D1.2 — Stratification awareness.** The prompt notes that negation must be
  stratified and that recursion must be well-founded.

### 2. Feature-Key Canonicalization — Weight 15%

Measures whether the prompt enforces the canonical feature-key format used by
`lingua-rules`. A feature key is a string of `dimension=value` pairs, sorted
alphabetically by dimension and joined with `;` (e.g. `case=genitive;number=plural`).
Linting rejects keys in any other order.

How to measure:

- Does the prompt require that all morphological features be expressed as
  `dimension=value` pairs?
- Does it mandate alphabetical sorting of dimensions and the use of `;` as the separator?
- Does it specify that the tool must validate the key order (or generate keys in
  the correct order) rather than leave it to chance?

Mandatory (blocking):

- **M2.1 — Canonical form required.** The prompt must require that all
  morphological features be expressed as `dimension=value` pairs.
- **M2.2 — Sorted and joined.** The prompt must mandate alphabetical sorting of
  dimensions and the use of `;` as the separator.

Desirable (improving):

- **D2.1 — Validation, not chance.** The prompt specifies that the tool must
  validate key order (or generate keys in the correct order) rather than relying
  on incidental ordering.

### 3. Testability & Golden-File Coverage — Weight 20%

Measures the extent to which the prompt defines verifiable, automated tests that
can be run the same way as `python -m lingua_rules.cli.main test`. `lingua-rules`
relies on golden-file tests to assert that generated forms match expected outputs
(e.g. `cat → cats`, `child → children`). A prompt without a testing specification
cannot be objectively assessed.

How to measure:

- Does the prompt include a test suite or a mechanism to generate test cases from
  the ontology/datasets?
- Are the test assertions expressed in the same `Lemma + Features → Expected Form`
  format used by `lingua-rules`?
- Does the prompt require the tool to report pass/fail counts and exit codes
  (e.g. `21/21 passed`) like the test command?

Mandatory (blocking):

- **M3.1 — Test suite present.** The prompt must include a test suite or a
  mechanism to generate test cases from the ontology/datasets.
- **M3.2 — Canonical assertion format.** Test assertions must be expressed in the
  `Lemma + Features → Expected Form` format.

Desirable (improving):

- **D3.1 — Machine-readable results.** The prompt requires pass/fail counts and
  non-zero exit codes on failure (e.g. `21/21 passed`).

### 4. Lint-Compliance & Static Validation — Weight 15%

Measures whether the prompt demands static analysis of rules and datasets,
comparable to `python -m lingua_rules.cli.main lint LANG`. The lint command checks
for Clingo parse errors, undeclared features, malformed tables, and inconsistent
feature-key order. A high-quality prompt should require similar validation before
runtime.

How to measure:

- Does the prompt specify that the tool must validate the ontology or rule set
  (e.g. check that all feature dimensions are declared, that datasets are
  well-formed TSV, that no contradictory rows exist)?
- Does it require error reporting that pinpoints the offending line or rule, as
  lint does?

Mandatory (blocking):

- **M4.1 — Static validation required.** The prompt must require the tool to
  validate the ontology or rule set (declared feature dimensions, well-formed
  TSV, no contradictory rows).

Desirable (improving):

- **D4.1 — Precise diagnostics.** The prompt requires error reporting that
  pinpoints the offending line or rule.

### 5. Modularity & Extensibility — Weight 15%

Measures the prompt's ability to produce a tool that can be extended to new
languages or categories without rewriting core logic. `lingua-rules` is designed
to be language-agnostic: adding a language (e.g. Dutch) is done via templates and
datasets, not by altering the engine. The prompt should reflect this modularity.

How to measure:

- Does the prompt separate language-specific resources (ontology, grammar files)
  from generic algorithms?
- Does it allow for the addition of new categories (verbs, adjectives) by supplying
  new rule files and datasets rather than changing the code?
- Does it reference templates (e.g. `regular-affix`, `class-paradigm`,
  `exception-override`) as the preferred way to author new rules?

Mandatory (blocking):

- **M5.1 — Resource–engine separation.** The prompt must separate
  language-specific resources (ontology, grammar files) from generic algorithms.

Desirable (improving):

- **D5.1 — Category extension by data.** The prompt allows new categories (verbs,
  adjectives) to be added via new rule files and datasets rather than code changes.
- **D5.2 — Template-first authoring.** The prompt references templates (e.g.
  `regular-affix`, `class-paradigm`, `exception-override`) as the preferred way to
  author new rules.

### 6. Documentation & Traceability — Weight 10%

Measures the prompt's requirement for documenting rules, assumptions, and data
sources, enabling future maintainers to understand and audit the system.
`lingua-rules` includes a detailed design document (`docs/superpowers/specs/...`)
and README that explain every template, command, and pitfall. Prompts should
similarly demand documentation.

How to measure:

- Does the prompt require inline comments or a separate specification that explains
  each rule's purpose?
- Does it ask for a mapping between the ontology/grammar sources and the generated
  rules (traceability)?
- Does it specify that the tool should output human-readable error messages and
  help text, as the CLI does?

Mandatory (blocking):

- **M6.1 — Rule rationale.** The prompt must require inline comments or a separate
  specification explaining each rule's purpose.

Desirable (improving):

- **D6.1 — Source traceability.** The prompt asks for a mapping between the
  ontology/grammar sources and the generated rules.
- **D6.2 — Usable interface text.** The prompt specifies human-readable error
  messages and help text.

---

## Universal Lemmatizer Metrics

### 1. Typological & Script Coverage — Weight 25%

Measures the extent to which the prompt forces the lemmatizer to account for the
full range of morphological types and writing systems found across world languages.

How to measure:

- Does the prompt explicitly reference typological categories (isolating,
  agglutinative, fusional, polysynthetic, introflective) and require the lemmatizer
  to handle each?
- Does it account for non-concatenative morphology (root-and-pattern, templatic
  inflection) rather than only prefix/suffix operations?
- Does it address script diversity (Latin, Cyrillic, Arabic, Devanagari, Ethiopic,
  cuneiform, etc.) and the normalisation issues that arise (Unicode normalisation,
  romanisation, historical orthography)?
- Does it require validation on Universal Dependencies treebanks across multiple
  language families as a minimum benchmark?
- Does it handle explicit edge cases — i.e. does the prompt dictate exact behaviour
  for null results, unknown words, or unlemmatizable tokens (e.g. "If the word is
  already a lemma or unanalyzable, return the input form with `confidence: low`")?

Mandatory (blocking):

- **M1.1 — Typological breadth.** The prompt must explicitly reference typological
  categories (isolating, agglutinative, fusional, polysynthetic, introflective)
  and require the lemmatizer to handle each.
- **M1.2 — Non-concatenative morphology.** The prompt must account for
  non-concatenative morphology (root-and-pattern, templatic inflection), not only
  prefix/suffix operations.
- **M1.3 — Script diversity and normalisation.** The prompt must address script
  diversity (Latin, Cyrillic, Arabic, Devanagari, Ethiopic, cuneiform, etc.) and
  the normalisation issues that arise (Unicode normalisation, romanisation,
  historical orthography).
- **M1.4 — Edge-case behaviour.** The prompt must dictate exact behaviour for null
  results, unknown words, and unlemmatizable tokens (e.g. "if the word is already a
  lemma or unanalyzable, return the input form with `confidence: low`"). Undefined
  edge-case behaviour is a blocking defect because it makes cross-lingual
  comparison meaningless.

### 2. Morphological Complexity Handling — Weight 20%

Measures the prompt's capacity to specify how the lemmatizer deals with
agglutination, fusion, non-concatenative inflection, vowel harmony, consonant
gradation, and other high-complexity morphological phenomena.

How to measure:

- Does the prompt distinguish between inflectional and derivational morphology, and
  specify different strategies?
- Does it require handling of cumulative exponence (one affix expressing multiple
  features) and zero morphs?
- Does it address stem alternations (ablaut, umlaut, consonant mutation) as distinct
  from affixation?
- Does it specify how to normalise historical or dialectal variants against a
  standard lemma, or does it leave normalisation undefined? (High-level normalisation
  is known to trade precision for generalisation.)

Mandatory (blocking):

- **M2.1 — Inflection vs. derivation.** The prompt must distinguish between
  inflectional and derivational morphology and specify different strategies for each.
- **M2.2 — Cumulative exponence and zero morphs.** The prompt must require handling
  of cumulative exponence (one affix expressing multiple features) and zero morphs.
- **M2.3 — Stem alternations.** The prompt must address stem alternations (ablaut,
  umlaut, consonant mutation) as distinct from affixation.

Desirable (improving):

- **D2.1 — Variant normalisation policy.** The prompt specifies how to normalise
  historical or dialectal variants against a standard lemma (noting that high-level
  normalisation trades precision for generalisation).

### 3. Low-Resource & Zero-Shot Robustness — Weight 20%

Measures how well the prompt is designed to support lemmatization when training
data are scarce or absent, including zero-shot and few-shot scenarios.

How to measure:

- Does the prompt require the lemmatizer to function in zero-shot or few-shot modes,
  and does it specify how examples are selected (e.g. frequency-balanced in-context
  learning)?
- Does it include a strategy for cross-lingual transfer from related or unrelated
  languages?
- Does it require reporting performance separately for low-resource vs. high-resource
  languages, rather than only an aggregate score?
- Does it mandate evaluation on out-of-vocabulary (OOV) forms, given that OOV accuracy
  can drop to around 9% in low-shot settings?

Mandatory (blocking):

- **M3.1 — Zero/few-shot operation.** The prompt must require the lemmatizer to
  function in zero-shot or few-shot modes and specify how examples are selected
  (e.g. frequency-balanced in-context learning).
- **M3.2 — Disaggregated reporting.** The prompt must require reporting performance
  separately for low-resource vs. high-resource languages, not only an aggregate
  score.

Desirable (improving):

- **D3.1 — Cross-lingual transfer.** The prompt includes a strategy for
  cross-lingual transfer from related or unrelated languages.
- **D3.2 — OOV evaluation.** The prompt mandates evaluation on out-of-vocabulary
  forms, given that OOV accuracy can drop to around 9% in low-shot settings.

### 4. Evaluation Rigor & Cross-Lingual Fairness — Weight 15%

Measures the prompt's specification of how lemmatization quality is measured across
languages, including metric choice, aggregation, and avoidance of language-specific
bias.

How to measure:

- Does the prompt require both type-level and token-level accuracy?
- Does it mandate macro-averaging across languages (equal weight per language) rather
  than micro-averaging over tokens, which would let high-resource languages dominate?
- Does it specify accuracy for ambiguous or morphologically complex cases?
- Does it require per-language or per-family breakdowns so that failures on specific
  typological groups are visible?
- Does it include a held-out test set that is never used for prompt development,
  analogous to the UD test splits?

Mandatory (blocking):

- **M4.1 — Type and token accuracy.** The prompt must require both type-level and
  token-level accuracy.
- **M4.2 — Macro-averaging.** The prompt must mandate macro-averaging across
  languages (equal weight per language) rather than micro-averaging over tokens,
  which would let high-resource languages dominate.
- **M4.3 — Per-language breakdowns.** The prompt must require per-language or
  per-family breakdowns so that failures on specific typological groups are visible.

Desirable (improving):

- **D4.1 — Accuracy@k.** The prompt specifies accuracy for ambiguous or
  morphologically complex cases (e.g. Accuracy@1 and @3).
- **D4.2 — Held-out test set.** The prompt includes a held-out test set never used
  for prompt development, analogous to the UD test splits.

### 5. Prompt Generalizability & Reliance on Linguistic Universals — Weight 10%

Measures whether the prompt is written in terms of language-independent morphological
categories (e.g. Universal Dependencies features) rather than ad-hoc, language-specific
rules, so that it can be extended to new languages without rewriting.

How to measure:

- Does the prompt express rules in terms of UD features (UPOS, case, number, tense,
  aspect, etc.) rather than language-specific labels?
- Does it avoid embedding language-specific exception lists or hand-crafted affix
  tables for individual languages?
- Does it require the lemmatizer to generalise to unseen languages using only the
  provided universal schema and in-context examples?
- Does it include a mechanism for adding a new language without modifying the prompt's
  core logic?

Mandatory (blocking):

- **M5.1 — UD-feature framing.** The prompt must express rules in terms of Universal
  Dependencies features (UPOS, case, number, tense, aspect, etc.) rather than
  language-specific labels.
- **M5.2 — No embedded language-specific tables.** The prompt must not embed
  language-specific exception lists or hand-crafted affix tables for individual
  languages.

Desirable (improving):

- **D5.1 — Unseen-language generalisation.** The prompt requires the lemmatizer to
  generalise to unseen languages using only the universal schema and in-context
  examples.
- **D5.2 — Language-addition path.** The prompt includes a mechanism for adding a new
  language without modifying the prompt's core logic.

### 6. Output Normalization — Weight 10%

Measures the prompt's specification of what counts as the canonical lemma across
languages, including script normalisation, case, historical vs. modern lemmas, and
handling of multi-word expressions.

How to measure:

- Does the prompt define whether lemmas are case-sensitive, and how case is handled
  across scripts?
- Does it specify Unicode normalisation (NFC/NFD) and script-specific canonicalisation?
- Does it address historical vs. synchronic lemmatization and state which policy the
  universal lemmatizer follows?
- Does it require a consistent treatment of multi-word tokens and clitics?

Mandatory (blocking):

- **M6.1 — Case policy.** The prompt must define whether lemmas are case-sensitive
  and how case is handled across scripts.
- **M6.2 — Unicode normalisation.** The prompt must specify Unicode normalisation
  (NFC/NFD) and script-specific canonicalisation.
- **M6.3 — Multi-word tokens and clitics.** The prompt must require consistent
  treatment of multi-word tokens and clitics.

Desirable (improving):

- **D6.1 — Historical vs. synchronic policy.** The prompt addresses historical vs.
  synchronic lemmatization and states which policy the universal lemmatizer follows.
