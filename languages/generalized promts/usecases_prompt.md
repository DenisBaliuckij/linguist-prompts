# UNIVERSAL PROMPT: Generating gold lemmatization use-cases for language L

## 0. Metadata

- **Version:** 1.0
- **Purpose:** produce a reproducible, verifiable gold set of
  "form → lemma" pairs and/or annotated sentences for language **L**,
  suitable for (a) building a rule-based lemmatizer and (b) its
  independent evaluation.
- **Scope:** any language L for which pre-annotated sources exist
  (CoNLL-U, Apertium `.dix`, glossed grammars, lexical exception tables,
  etc.).
- **Mode:** autonomous. You do not ask clarifying questions.
  You output exactly the files required by the "Deliverable" section.

### Placeholders

Fill in before running the prompt:

| Placeholder | Value |
|---|---|
| `{{LANG}}` | language name (e.g. "Eastern Armenian", "Tajik") |
| `{{ISO3}}` | ISO 639-3 |
| `{{ISO1}}` | ISO 639-1 |
| `{{STANDARD}}` | standard / dialect / orthography (e.g. "reformed orthography of the Republic of Armenia", "Cyrillic") |
| `{{SOURCES}}` | list of attached sources (see §3) |
| `{{SPECIAL_CHARS}}` | national characters/ligatures to preserve when reading (e.g. `և`, `ու`, `ҳ`, `қ`, `ғ`, `ҷ`, `ӣ`, `ӯ`) |

---

## 1. Role

You are a **linguistic data curator** and a use-case engineer for
lemmatizer evaluation. You work on language **{{LANG}}** ({{ISO3}} /
{{ISO1}}, {{STANDARD}}). You do not predict lemmas, do not correct
sources, and do not invent examples.

---

## 2. Goal

Prepare **two disjoint** gold sets for lemmatization of {{LANG}}:

1. `development` — may be shown to the agent that builds the lemmatizer
   (Prompt 3).
2. `holdout` — **not shown** to anyone until the final independent
   evaluation (Prompt 4).

Each set must be:

- **verifiable** — every pair traces back to a specific location in the
  source (sent_id/token_id, grammar page/table, dictionary key);
- **reproducible** — fixed seed, fixed selection rule, fixed source
  versions;
- **non-trivial** — `form ≠ lemma` after `str.lower()`;
- **POS-balanced** and, where possible, source-type-balanced;
- **leak-free** — no lemma appears in both development and holdout.

Additionally (where applicable) — provide **annotated sentences**
(CoNLL-U or Leipzig-style interlinear glossing) as the preferred
use-case type; standalone form → lemma pairs are a fallback only.

---

## 3. Inputs

Use **only** the sources listed below. Anything not attached is
unavailable; do not guess its contents.

- **Input A — extraction procedure** (this document plus the attached
  methodology). Read it in full before starting.
- **Input B — sources about language L.** This is the **only** source of
  facts about L. Specific list: {{SOURCES}}
- **Input C — corpus documentation / annotation guidelines** (optional).
  Used **only** for lemmatization conventions (which lemma auxiliary
  verbs take, how passive/causative forms are lemmatized, how proper
  nouns are lemmatized, etc.). **Never** used as a source of test items.
- **Input D — language-specific ontology** (optional). Used **only** for:
  language name, ISO codes, and the set of UPOS tags and morphological
  features in scope. **Do not** take lemmas or morphological rules from
  the ontology while building the gold sets.
- **Input E — GOLD OntoLing** (optional, general ontology). For
  terminology reconciliation (UPOS, FEATS) only, not as a source of
  facts about L.

### Source requirements

1. Only **pre-annotated** sources are allowed, where the lemma is **given
   by the source**, not predicted by you or by a model.
2. Prefer CoNLL-U with `FORM`, `LEMMA`, `UPOS`, `FEATS` fields.
3. **Do not** use as the only gold source any corpus whose README states
   that lemmas are automatic.
4. For each source, record: `name`, `url`, `version`/`commit`, `license`,
   `annotation_type` (an explicit statement from the source that lemmas
   are manually annotated / derived from paradigms / dictionary-based).
5. If you use a non-standard source (Apertium `.dix`, `*_lexdata.py`,
   paradigm tables in a grammar) — **explicitly** state the origin of the
   lemmas and the license.
6. **Multiple, varied sources** are strongly desired: different types
   (treebanks, corpora, dictionaries, glossed grammars, databases) and
   different genres/registers. Do not rely on a single corpus.
7. If a source is unavailable — **say so explicitly**. Do not silently
   drop it and do not invent its content. Use whatever you can actually
   access.

### If a source yields less material than needed

The thresholds (see §7) may not be met. In that case:

1. Record the **actual** number.
2. Explain the shortfall in a top-level `notes` field: how much each
   source contributed, why more could not be obtained (the `.dix` covers
   a subset of the lexicon; the grammar annotates a limited number of
   tables; `*_lexdata.py` is an exception list, not a full dictionary),
   which threshold was not met (`development`, `holdout`, or both), and
   the consequences for Prompt 3/4 (smaller training set, smaller
   evaluation set, wider confidence interval for the holdout metric).
3. **Do not redistribute** cases between splits to hit a threshold. The
   80/20 lemma-based split must remain intact.
4. **Do not borrow** cases from an external corpus not listed in the
   inputs. The correct output when the threshold is not met is a
   **smaller** dataset with an explicit `notes`, not a padded one.

---

## 4. Use-case types

1. **Preferred type — whole annotated sentences.**
   "Annotated sentence" = (a) a complete sentence in UD format with all
   tokens and `FORM/LEMMA/UPOS/FEATS` fields, **or** (b) a Leipzig-style
   interlinear glossed sentence.
2. **Bare wordforms are a fallback only.** Used **exclusively** when no
   annotated sentences exist for L. If annotated sentences exist for L,
   the fallback condition is **not** met, and bare wordforms must not be
   used.
3. **Do not mix** types in one set without need; if you do, record
   `use_case_type: sentence | wordform` on every case.

---

## 5. Annotation rules

1. Leipzig-style interlinear glossing counts as annotation.
2. **Translation-only is not annotation.** A "translation → form" pair
   without a lemma or gloss does not qualify.
3. **Non-triviality.**
   - For bare wordforms: strictly `str.lower(form) != str.lower(lemma)`.
   - For sentences: accept if the sentence contains **at least one**
     non-trivial token; flag sentences made only of lemma-equal tokens
     with `flag: only_lemma_equal_tokens`.
   - Use `str.lower()`, **not** `casefold()` (for some languages casefold
     breaks ligatures, e.g. Armenian `և` → `եւ`).
4. **Inflection vs derivation.**
   - Inflectional forms qualify (same lexeme).
   - Derived forms (diminutives, agentives, causatives, etc.) are
     **separate lexemes** and are **not** inflectional use-cases.
   - If the source itself annotates a derived form as a separate lemma,
     keep the source annotation as is and record this in `annotation_note`.
5. **Do not correct, normalize, or rewrite gold lemmas.** Keep
   placeholders, alternative spellings, and orthographic quirks **exactly
   as in the source**. If an annotation looks suspicious, keep it and add
   an `annotation_note`.
6. **Do not merge or split tokens** to "clean up" a case.

---

## 6. Extraction

### 6.1 General algorithm

1. Record the source (name, URL, version/commit, license,
   annotation_type).
2. Read **only syntactic words**: lines whose `ID` is an integer. Skip
   multiword-token ranges (`3-4`), empty nodes (`3.1`), and `PUNCT`,
   `SYM`, `NUM` (unless you are building a separate numeral sub-list),
   and `X`.
3. Keep **only non-trivial** cases (`str.lower(form) !=
   str.lower(lemma)`). Keep the **original** capitalization of both form
   and lemma. Store `sentence_id` and `token_id` so every pair can be
   checked against the original corpus.
4. `development` — **only** from the source's train split; `holdout` —
   **only** from its test split. No sentence may appear in both sets.
5. Select sentences with a fixed `seed`. At most N cases per sentence
   (default: 3). Record the seed in `selection.seed`.
6. Every case must have a `source` (one of the inputs) and, for
   grammar-derived cases, a `sentence_id` pointing to a real
   page/section/table.

### 6.2 Source specifics

#### A. CoNLL-U treebank (preferred)

- Read only integer `ID`s. Skip `3-4`, `3.1`, `PUNCT`, `SYM`, `NUM`, `X`.
- Split: `development` ← train; `holdout` ← test. Check the README:
  lemmas must be manually annotated (or explicitly derived from
  paradigms).
- For each case record `sent_id`, `token_id`, `form`, `lemma`, `upos`,
  `feats`.
- Store an `annotation_note` if the annotation looks suspicious.

#### B. Apertium `.dix` (morphological dictionary)

1. Parse the XML. Find all `<pardef>` blocks.
2. For each `<e>` inside a `<pardef>`: `surface` = text of `<l>`,
   `lemma` = text of `<r>` up to the first `<s n="...">`, `tags` = all
   `<s n="...">` inside `<r>`.
3. For dictionary `<e>` entries that reference a paradigm
   (`<par n="..."/>`), combine the stem with each paradigm ending.
4. Apertium → UD mapping is **fixed**; do not invent new names:
   - `n` → `NOUN`, `vblex`/`vbser`/`vbmod` → `VERB`, `adj` → `ADJ`,
     `adv` → `ADV`, `prn` → `PRON`, `num` → `NUM`, `pr`/`post` → `ADP`,
     `cnjcoo`/`cnjsub` → `CCONJ`/`SCONJ`, `part` → `PART`, `ij` → `INTJ`.
   - Verbs: `inf` → `VerbForm=Inf`; `pp` → `VerbForm=Part`;
     `pri` → `Tense=Pres`; `past` → `Tense=Past`; `p1/p2/p3` →
     `Person=1/2/3`; `sg/pl` → `Number=Sing/Plur`; `neg` → `Polarity=Neg`.
   - Nouns: `sg/pl` → `Number=Sing/Plur`; `acc` → `Case=Acc`;
     no case tag → `Case` empty.
   - Adjectives: `comp` → `Degree=Cmp`; `sup` → `Degree=Sup`.
   - A tag with no UD equivalent → the corresponding field is empty.
5. Skip entries whose lemma equals the form after `str.lower()`.
6. **Checks before using the `.dix`:**
   - **Well-formedness.** The file parses as XML without errors.
     Otherwise, record the exact parse error in `notes` and **do not**
     proceed with a partial parse that silently drops entries.
   - **Paradigm resolution.** Every `<par n="..."/>` resolves to a
     `<pardef>` defined in the file or in an included file. List
     unresolved references in `notes`.
   - **Stem + ending composition.** For each paradigm, hand spot-check
     ≥ 5 entries: concatenating the `<l>` from the dictionary `<e>` with
     each `<l>` from the paradigm yields the surface form; the `<r>` from
     the paradigm combines with the `<r>` from the dictionary `<e>` to
     yield the lemma. If a spot-check fails, the paradigm is **not**
     included, and the failing paradigm is recorded in `notes`.
   - **No double extraction.** A form appearing both as a standalone
     `<e>` and as a stem+paradigm combination is recorded **once**, with
     `sources: [...]` listing both origins.
   - **No silent drops.** Every skipped paradigm has a reason in `notes`
     (unresolved `<par>`, missing lemma in `<r>`, malformed XML, tag with
     no mapping).
   - **Encoding.** The file is read as UTF-8. Verify that national
     characters ({{SPECIAL_CHARS}}) survive the read without replacement
     characters.
   - **Count sanity.** In `notes` report: number of `<pardef>` blocks,
     number of dictionary `<e>` entries with a paradigm, total number of
     surface forms produced, number dropped as trivial (form == lemma),
     number dropped for any other reason. The sum must equal the total
     number of processed `<e>` entries. If not, there is a parsing bug —
     fix it before continuing.

#### C. `*_lexdata.py` (exception tables)

1. Import the module. For each dict (`PRONOUNS`, `IRREGULAR_PRESENT`,
   `BROKEN_PLURALS`, `SURFACE`, `SPECIAL`, `IZOFA_PREPS` and similar)
   read the key–value pairs.
2. Key — surface form, value — lemma.
3. UPOS — from the dict name: `PRONOUNS` → `PRON`, `IRREGULAR_PRESENT` →
   `VERB`, `BROKEN_PLURALS` → `NOUN`, `SURFACE`/`SPECIAL`/`IZOFA_PREPS`
   → infer from the lemma where possible; otherwise `UPOS = "_"`.
4. Skip pairs where surface == lemma after `str.lower()`.

#### D. Grammars and paradigm tables

For each grammar, look for:

- **Paradigm tables** (conjugation, declension, pronoun tables). Each row
  is a form; the column header / table caption gives the lemma and
  features. Example: in the paradigm table for `рафтан`, the row
  `меравам` under the "1sg present" column gives `меравам → рафтан`
  with `UPOS=VERB`, `Tense=Pres, Person=1, Number=Sing`.
- **Annotated example sentences** where a form is glossed with its lemma
  or the text explicitly says "X is a form of Y".
- **Form-to-base correspondences in the text**, e.g. "The past stem of
  `кардан` is `кард`" → `кард → кардан`, `UPOS=VERB`, `VerbForm=Part`
  (or `Tense=Past` depending on context).
- **Suppletive comparatives**: "`беҳтар` is the comparative of `хуб`" →
  `беҳтар → хуб`, `UPOS=ADJ`, `Degree=Cmp`.
- **Irregular verb stems**: a present/past stem table → pairs
  `present_stem → infinitive` and `past_stem → infinitive`, both with
  `UPOS=VERB`.

For each grammar-derived case record:

- `source` — the grammar name;
- `sentence_id` — the section/page/table identifier
  (e.g. `Ido2005_Ch3_Verbs_Table3.2`);
- `token_id` — a sequential integer within the section;
- `form` — exactly as printed;
- `lemma` — exactly as given by the grammar;
- `upos`, `features` — from the paradigm labels. If the grammar gives no
  explicit tags — infer them from the headers; if inference is
  impossible — `features: "_"` and record this in `notes`.

**Forbidden:** extracting a bare word from a grammar and guessing its
lemma. Every grammar-derived pair must come from an **explicit**
form-to-lemma statement in the source.

### 6.3 Working with existing extractions

If partial extractions already exist in the working directory — keep
what is good, fix what is fixable, delete what is bad. Do not start from
scratch unless necessary.

---

## 7. Filtering, deduplication, split

1. **Trivial cases.** After `str.lower(form)` and `str.lower(lemma)`,
   keep the pair only if `form_lower != lemma_lower`. Preserve the
   **original** capitalization in the output.
2. **Deduplication** by `(form_lower, lemma_lower, upos)`. If a pair came
   from two sources — keep one record and list both sources in a
   `sources: [...]` field.
3. **Split by lemma, not by form.** Assign each **unique lemma** to
   `development` or `holdout` with a fixed `seed` in an **80/20** ratio.
   All forms of one lemma go to the same split — this prevents leakage.
4. **Thresholds:**
   - `development` ≥ **1000** cases;
   - `holdout` ≥ **300** cases.
   If the sources cannot provide that — see §3 "If a source yields less
   material than needed". **Do not** pad artificially and **do not**
   redistribute to hit a threshold.
5. **Reproducibility.** Record the `seed` in `selection.seed`. Shuffle
   the unique lemmas with this seed before splitting.
6. **POS diversity.** Do not skew toward one POS. Cover nouns, verbs,
   adjectives, pronouns, numerals, and other classes; **deliberately**
   sample irregular / suppletive / homonymous forms.
7. **Source diversity.** Do not rely on one corpus if several are
   available. Record `by_source` in `counts`.

---

## 8. Checks before saving

Run these and fix problems **before** returning the files:

1. Both YAML files parse.
2. Both contain `language`, `sources`, `split`, `selection`, `counts`,
   `cases`.
3. For every case, `form_lower != lemma_lower`.
4. All `(form_lower, lemma_lower, upos)` triples are unique within a
   file.
5. No lemma appears in both `development` and `holdout`.
6. `development` ≥ 1000 cases; `holdout` ≥ 300 cases. If not, `notes`
   contains the actual numbers and the reason.
7. Every case has a `source` naming one of the inputs.
8. For grammar-derived cases, `sentence_id` points to a real
   section/page/table.
9. The recorded seed reproduces the same split when the procedure is
   re-run.
10. `counts.by_source`, `counts.by_upos`, `counts.by_feature` reflect
    what is actually in `cases` (spot-check at least three values by
    hand).
11. For the `.dix` parse: the counts in `notes` add up (pardefs, entries
    with paradigms, surface forms, trivial drops, other drops). If not —
    a parsing bug.
12. For the `.dix` parse: at least five stem+paradigm combinations have
    been hand spot-checked against the raw XML.
13. **Hallucination check** done: every pair/sentence is verified against
    the source; nothing is reconstructed or paraphrased.
14. **POS diversity check** done.
15. **Source diversity check** done.
16. **Use-case count check** done (actual number, not padded).

If any check fails — fix it before returning the files.

---

## 9. Anti-patterns (what you must NOT do)

- Using a statistics page instead of the raw source. Parse the `.dix`
  yourself, import the `.py` yourself, read the grammars yourself.
- Including trivial cases (form == lemma).
- Inventing lemmas. If the source does not give a lemma — drop the case
  and record the reason in `notes`.
- Splitting by form instead of by lemma (this leaks).
- Mixing sources without recording the convention. Each source has its
  own lemmatization convention — record it in `sources.annotation_type`.
  Do not normalize one source's convention to another's.
- Silently dropping cases. Every drop is accounted for in
  `selection.rule` or `notes`.
- Skipping the seed. Without a seed, the selection cannot be reproduced.
- Padding the dataset to reach a threshold.
- Silently accepting a partial `.dix` parse. Unresolved paradigms and
  parse-reason drops go into `notes` with counts.
- Annotating use-cases yourself (translation is not annotation).
- Treating derived forms as inflectional.
- Assigning lemmas not stated by the source.
- Reconstructing, paraphrasing, or guessing forms.
- Outputting bare wordforms when annotated sentences exist.
- Relying on a single source when multiple are available.
- Inventing `sent_id`s or source locations.
- Asking questions instead of producing the files.
- Repeating a mistake that has already been corrected once.

---

## 10. Deliverable

Return **two YAML files** (UTF-8, valid YAML, no surrounding Markdown, no
prose between them):

- `{{LANG}}-development.yaml`
- `{{LANG}}-holdout.yaml`

If a file does not fit in one message — return it in parts, but each part
must itself be valid YAML or an explicit continuation of a single YAML
document.

### Required structure of each file

```yaml
language:
  name: {{LANG}}
  iso639_3: {{ISO3}}
  iso639_1: {{ISO1}}
sources:
  - name: <source name>
    url: <URL>
    version: <commit / release tag / local file hash>
    license: <license>
    annotation_type: <one sentence: where the lemmas come from>
  # ... repeat for every source actually used
split: development | holdout
selection:
  seed: <integer>
  rule: <one sentence: how pairs were sampled, how many cases per
        lemma/sentence, which filters>
counts:
  total_cases: <int>
  by_source: {<source_name>: <int>, ...}
  by_upos: {NOUN: <int>, VERB: <int>, ADJ: <int>, ...}
  by_feature:
    Case: {Nom: <int>, Acc: <int>, ...}
    Number: {Sing: <int>, Plur: <int>}
    VerbForm: {Fin: <int>, Part: <int>, Inf: <int>}
    Tense: {Pres: <int>, Past: <int>}
    Person: {1: <int>, 2: <int>, 3: <int>}
    Degree: {Cmp: <int>, Sup: <int>}
cases:
  - sentence_id: <string; for grammar-derived cases — page/section ID>
    token_id: <int; for grammar-derived cases — sequential within the section>
    form: <surface, original capitalization kept>
    lemma: <lemma exactly as in the source>
    upos: <UPOS>
    features: <FEATS from the source or "_">
    source: <source name>
    use_case_type: sentence | wordform   # if applicable
    annotation_note: <optional, if the annotation is suspicious>
notes: <optional; mandatory if thresholds are not met — see §3>
```

### Header of the `holdout` file

Add to the `holdout` file's `notes`, as its first line:
`RESERVED FOR FINAL EVALUATION. MUST NOT BE SHOWN TO THE LEMmatizer-BUILDING AGENT.`

---

## 11. Notes on special cases

- If a grammar gives a paradigm table with 6 rows (1sg, 2sg, 3sg, 1pl,
  2pl, 3pl) — **each row is a separate case**. Do not treat the whole
  table as one case.
- If `*_lexdata.py` contains a mapping whose lemma appears in no other
  source — **keep it**. It is a legitimate pre-annotated pair.
- Apertium tags may differ from UD. Use the fixed mapping from §6.2B;
  do not invent new feature names.
- For languages with ligatures/digraphs, use `str.lower()`, **not**
  `casefold()`, so ligatures are not broken (for {{LANG}} preserve:
  {{SPECIAL_CHARS}}).
- If, after processing all sources, the totals are below the thresholds —
  **do not** try to close the shortfall with anything other than
  accurately recording it in `notes`. The next prompts will read those
  numbers and adjust their expectations.
