# Prompts: Tongan · lemmatization

Run the four prompts in order. Each prompt is self-contained: start a new chat
for each stage and attach only the files listed under its inputs.

## 1. Building the Tongan morphological ontology

**Purpose:** build a verifiable language-specific ontology from which a lemmatizer can take its rules, lemma conventions and lexical exceptions.

```text
You are a Tongan linguist and a linguistic data engineer. Build one JSON file,
`OntoTongan.json`, for Tongan (ISO 639-3: ton, ISO 639-1: to). Work only with
the attached sources. Do not add facts from memory and do not invent rules,
examples or references.

Input A: a general ontology of human language grammar (GOLD OntoLing).
Input B: the attached grammars, dictionaries and word lists of Tongan:
{{list of attached sources}}. A reference grammar (for example Churchward's
Tongan Grammar) and a machine-readable dictionary (word, part of speech,
derivational information) are strongly recommended.
Input C (optional): the annotation guidelines of the gold corpus that will be
used for evaluation (for example, the UD Tongan documentation and the README
of the chosen treebank). Use it only for lemma conventions, never as a source
of test items.
If Input C is not attached, there is no target corpus: read every mention of
"the target corpus" below as "the attached dictionary", use Universal
Dependencies feature names, and take lemma conventions from the dictionary
headwords. Record them in `lemma_conventions` with `source: dictionary` and
`status: provisional`, and add a record to `gaps` saying that corpus
conventions were not available. Where the sources allow two reasonable lemma
choices (for example a derived verb or its base), record both and mark the
rule `lexicon_required`.

Task: keep the sections of Input A that are compatible with Tongan, but fill
them only with facts from Input B and Input C. Do not produce a reduced
demonstration ontology: transfer every fact and paradigm in Input B that is
relevant for lemmatization. The main goal of the file is to support a
working rule-based lemmatizer with the broadest coverage the sources allow.
The Morphology module must contain:

- parts of speech and the citation (dictionary) form of each one;
- orthography and normalization: the glottal stop (fakamoleki) and all its
  encodings (for example ʻ, ', ’, ʼ), vowel length marking (macron, toloi),
  stress marking if any, hyphens, word division and capitalization of proper
  names; which of these the target corpus writes and which it omits, so that
  forms can be matched with and without marks;
- preverbal particles of tense, aspect and mood (for example 'oku, na'e, 'e,
  te, kuo, if described): their forms, their meaning, whether they are
  separate tokens in the target corpus and which lemma they take;
- pronouns as full "form -> lemma" tables: person, number (singular, dual,
  plural), inclusive/exclusive first person, full and short or emphatic
  forms, and the possessive forms with their possessor person and number;
- possessive categories (for example the a-class and o-class of possessors):
  the markers, the rule that selects the class, and which classes are
  lexicon-dependent;
- articles, determiners, demonstratives, case and preposition particles
  (including the ergative and absolutive markers if the sources describe
  them), numerals, directionals and other particles, each with its lemma;
- verb derivation and inflection: causative, reciprocal, transitivizing,
  instrumental and nominalizing affixes, and passive or ergative-related
  suffixes with their consonant variants; for each affix give the pattern,
  the operation that recovers the base, the conditions, and whether the base
  can be recovered by a rule or only with the lexicon;
- reduplication (full and partial): the patterns, how to undo them, and when
  the reduplicated form is itself a lexical item with its own lemma;
- register and politeness vocabulary (ordinary, honorific, royal) as lexical
  equivalents, with the lemma convention of the target corpus (does the
  honorific item keep its own lemma or map to the ordinary one);
- any dialect or variant differences that affect spelling or form matching,
  only if the sources state them (otherwise record a gap);
- every lemma convention of the target corpus (Input C) that differs from a
  plain dictionary form: for example lemmas written in a compound notation
  such as "past#present", lemmas of particles, auxiliaries and copulas,
  proper names, the spelling of the glottal stop and macrons in lemmas;
- every condition under which a surface form is ambiguous and one rule is
  not enough (homographs among particles, roots, derived forms, pronouns).

For every rule record: an id, the input pattern, the output lemma or the
operation, the conditions (part of speech and morphological features,
written with the exact feature names of the target corpus, for example UD
`Person`, `Number`, `Clusivity`, `Tense`, `Voice`), at least one example
"form -> lemma" that is attested in Input B, the source, and a status:
`rule`, `lexicon_required` or `ambiguous`. If a rule has several possible
outputs and Input B contains a machine-readable lexicon, count in that lexicon
how often each output is correct and record the counts; if one output covers
at least 60% of at least 10 attested forms, record it as `default_replacement`
together with the counts as evidence. Do not choose defaults from intuition.
If a machine-readable dictionary or word list is part of Input B, do not copy
it into the JSON; register it in `lexicon_files` with its file name, format,
columns, licence, how a citation form is built from it, and the lemma
convention it follows. Do not fill unknown data with plausible guesses: leave
it out and add a record to `gaps` with the reason.

In `meta` give: title, version, language, ISO codes, every source that was
actually used, the date and the scope. Examples must give the Tongan form,
a gloss and a translation, and each must come from Input B. Before answering,
check that the JSON is valid, that every example really follows its rule and
that every fact has a source. Remove rules whose examples cannot be found and
list rules without an attested example under `verification`.

Return only valid UTF-8 JSON, with no Markdown and no comments.
```

## 2. Preparing gold use-cases

### 0. Metadata

- **Version:** 1.0 (Tongan)
- **Purpose:** produce a reproducible, verifiable gold set of
  "form → lemma" pairs and/or annotated sentences for Tongan, suitable
  for (a) building a rule-based lemmatizer and (b) its independent
  evaluation.
- **Scope:** Tongan, using only the pre-annotated sources attached in
  `{{SOURCES}}` (UD/CoNLL-U data if any, dictionary entries that state
  related forms, paradigm tables and explicit form-to-base statements in
  grammars).
- **Mode:** autonomous. You do not ask clarifying questions. You output
  exactly the files required by the "Deliverable" section.

#### Placeholders (already filled for Tongan; `{{SOURCES}}` is filled by the user)

| Placeholder | Value |
|---|---|
| `{{LANG}}` | Tongan |
| `{{ISO3}}` | ton |
| `{{ISO1}}` | to |
| `{{STANDARD}}` | standard Tongan orthography (glottal stop written `ʻ`, macrons on long vowels, digraph `ng`) |
| `{{SOURCES}}` | (1) Churchward, *Tongan Grammar* (grammar, paradigm tables and explicit form-to-base statements); (2) kaikki.org Tongan extract (Wiktionary dump processed by wiktextract, JSONL; dictionary); (3) Tongan lex (lexicon / exception table, file as attached) |
| `{{SPECIAL_CHARS}}` | `ʻ` (U+02BB), `ā ē ī ō ū Ā Ē Ī Ō Ū`, digraph `ng` |

---

### 1. Role

You are a **linguistic data curator** and a use-case engineer for
lemmatizer evaluation. You work on **Tongan** (ton / to, standard
Tongan orthography). You do not predict lemmas, do not correct sources,
and do not invent examples.

---

### 2. Goal

Prepare **two disjoint** gold sets for lemmatization of Tongan:

1. `development` — may be shown to the agent that builds the lemmatizer
   (Prompt 3).
2. `holdout` — **not shown** to anyone until the final independent
   evaluation (Prompt 4). It must never be shown while the ontology, the
   lexicon or the code is written.

Each set must be:

- **verifiable** — every pair traces back to a specific location in the
  source (sent_id/token_id, grammar page/section/table, dictionary
  headword);
- **reproducible** — fixed seed, fixed selection rule, fixed source
  versions;
- **non-trivial** — `form ≠ lemma` after `str.lower()`;
- **POS-balanced** and, where possible, source-type-balanced;
- **leak-free** — no lemma appears in both development and holdout.

Additionally (where applicable) provide **annotated sentences** (CoNLL-U
or Leipzig-style interlinear glossing) as the preferred use-case type;
standalone form → lemma pairs are a fallback only.

---

### 3. Inputs

Use **only** the sources listed below. Anything not attached is
unavailable; do not guess its contents.

- **Input A — extraction procedure** (this document). Read it in full
  before starting.
- **Input B — sources about Tongan.** This is the **only** source of
  facts about Tongan. Exactly three sources:
  1. **Churchward Tongan Grammar** — the only source of paradigm tables
     and explicit form-to-base statements (§6.2 C).
  2. **kaikki Tongan dictionary** (wiktextract JSONL) — the only source
     of dictionary-derived pairs (§6.2 B).
  3. **Tongan lex** — a lexicon/exception table (§6.2 D).
  Source names in `sources`, `by_source` and `source` must be exactly:
  `Churchward_Grammar`, `kaikki_Tongan`, `Tongan_lex`.
- **Input C — annotation guidelines / grammar conventions** (optional).
  Used **only** for lemmatization conventions (which form is the lemma
  of a passive, a suffixed transitive, a nominalization with `-nga`, a
  singular/plural verb pair, a possessive pronoun, etc.). **Never** used
  as a source of test items.
- **Input D — OntoTongan.json** (optional, language-specific ontology).
  Used **only** for: language name, ISO codes, and the set of UPOS tags
  and morphological features in scope. **Do not** take lemmas or
  morphological rules from the ontology while building the gold sets.
- **Input E — GOLD OntoLing** (optional, general ontology). For
  terminology reconciliation (UPOS, FEATS) only, not as a source of
  facts about Tongan.
- **Raw Tongan texts** (if attached) are **not** gold. They have no
  lemmas given by a source and must not be lemmatized by you to produce
  test items.

#### Source requirements

1. Only **pre-annotated** sources are allowed, where the lemma is
   **given by the source**, not predicted by you or by a model.
2. Prefer CoNLL-U with `FORM`, `LEMMA`, `UPOS`, `FEATS` if one is
   attached (e.g. a UD Tongan treebank). If none is attached, this is
   not a failure: use dictionary and grammar sources (§6.2 B–C) and say
   so in `notes`.
3. **Do not use as the only gold source** any corpus whose README states
   that lemmas are automatic.
4. For each source, record: `name`, `url`, `version`/`commit`,
   `license`, `annotation_type` (an explicit statement from the source
   that lemmas are manually annotated / converted / derived from
   paradigms / dictionary-based). For a UD treebank state the period and
   genres of the texts.
5. For each non-standard source (dictionary, grammar) **explicitly**
   state the origin of the lemmas and the license.
6. **Do not mix UD treebanks with different lemma conventions** in one
   set. Each source has its own lemmatization convention — record it in
   `annotation_type` and do not normalize one source's convention to
   another's.
7. **Multiple, varied sources** are strongly desired (dictionary +
   several grammars + treebank if any). Do not rely on a single source.
8. If a source is unavailable or unreadable — **say so explicitly**. Do
   not silently drop it and do not invent its content.

#### If a source yields less material than needed

The thresholds (see §7) may not be met. Tongan has very little
inflectional morphology, and annotated material is scarce, so a
shortfall is expected. In that case:

1. Record the **actual** number.
2. Explain the shortfall in a top-level `notes` field: how much each
   source contributed, why more could not be obtained, which threshold
   was not met (`development`, `holdout`, or both), and the consequences
   for Prompt 3/4 (smaller training set, smaller evaluation set, wider
   confidence interval for the holdout metric).
3. **Do not redistribute** cases between splits to hit a threshold. The
   80/20 lemma-based split must remain intact.
4. **Do not borrow** cases from any source not listed in the inputs. The
   correct output when the threshold is not met is a **smaller** dataset
   with an explicit `notes`, not a padded one.
5. Also report in `notes` the share of trivial cases (form = lemma) in
   each source that gives running text.
6. **Independence caveat.** If the same grammar or dictionary will also
   be read by the lemmatizer-building agent, state in `notes` which
   `holdout` cases come from such sources: the holdout is then
   independent only at the level of lemmas, not of sources.

---

### 4. Use-case types

1. **Preferred type — whole annotated sentences.**
   "Annotated sentence" = (a) a complete sentence in UD format with all
   tokens and `FORM/LEMMA/UPOS/FEATS` fields, **or** (b) a Leipzig-style
   interlinear glossed sentence (e.g. an example in a grammar glossed
   with its base form).
2. **Bare wordforms are a fallback only.** Used **exclusively** when no
   annotated sentences exist for Tongan in the attached sources. If
   annotated sentences exist, the fallback condition is **not** met, and
   bare wordforms must not be used.
3. **Do not mix** types in one set without need; if you do, record
   `use_case_type: sentence | wordform` on every case.

---

### 5. Annotation rules

1. Leipzig-style interlinear glossing counts as annotation.
2. **Translation-only is not annotation.** A "translation → form" pair
   without a lemma or gloss does not qualify.
3. **Non-triviality.**
   - For bare wordforms: strictly `str.lower(form) != str.lower(lemma)`.
   - For sentences: accept if the sentence contains **at least one**
     non-trivial token; flag sentences made only of lemma-equal tokens
     with `flag: only_lemma_equal_tokens`.
   - Use `str.lower()`, **not** `casefold()`.
4. **Inflection vs derivation.**
   - Pairs that the source presents as forms of the same lexeme
     qualify: e.g. a suppletive singular/plural verb pair, pronoun and
     possessive paradigms (person, number incl. dual, clusivity),
     passive and other suffixed forms **if the source treats them as
     forms of the base verb**.
   - Derived forms (e.g. `faka-` causatives, agentive or other
     derivations) are **separate lexemes** and are **not** inflectional
     use-cases.
   - If the source itself annotates a derived form as a separate lemma,
     keep the source annotation as is and record this in
     `annotation_note`.
   - Do not decide yourself whether a suffix is inflection or
     derivation: follow the source and record its statement.
5. **Do not correct, normalize, or rewrite gold lemmas or forms.** Keep
   placeholders, alternative spellings and orthographic quirks **exactly
   as in the source**, including the variants of the glottal stop
   (`ʻ`, `'`, `’`, `` ` ``) and the presence or absence of macrons. If
   an annotation looks suspicious (for example a lemma still in
   `past#present` form), keep it and add an `annotation_note`.
6. **Do not merge or split tokens** to "clean up" a case. Tongan
   function words and particles are separate words: do not glue them to
   the verb.

---

### 6. Extraction

#### 6.1 General algorithm

1. Record the source (name, URL, version/commit, license,
   annotation_type).
2. For CoNLL-U sources, read **only syntactic words**: lines whose `ID`
   is an integer. Skip multiword-token ranges (`3-4`), empty nodes
   (`3.1`), and `PUNCT`, `SYM`, `NUM` (unless you are building a
   separate numeral sub-list), and `X`.
3. Keep **only non-trivial** cases (`str.lower(form) !=
   str.lower(lemma)`). Keep the **original** capitalization of both
   form and lemma. Store `sentence_id` and `token_id` so every pair can
   be checked against the original source.
4. Split by **lemma** (see §7.3). For a treebank with train/test
   splits, `development` ← train and `holdout` ← test, if this does not
   conflict with the lemma-disjointness rule; if it does, the
   lemma-disjointness rule wins and the conflict is recorded in `notes`.
   No sentence may appear in both sets.
5. Select with a fixed `seed`. At most N cases per sentence (default:
   3). Record the seed in `selection.seed`.
6. Every case must have a `source` (one of the inputs) and, for
   grammar- and dictionary-derived cases, a `sentence_id` pointing to a
   real page/section/table/headword.

#### 6.2 Source specifics

##### A. CoNLL-U treebank (optional; preferred if attached)

- Read only integer `ID`s. Skip `3-4`, `3.1`, `PUNCT`, `SYM`, `NUM`,
  `X`.
- Check the README: state whether lemmas are manual, converted or
  automatic. Automatic lemmas cannot be the only gold source.
- For each case record `sent_id`, `token_id`, `form`, `lemma`, `upos`,
  `feats`.

##### B. kaikki Tongan dictionary (wiktextract JSONL)

1. Read the file line by line as UTF-8 JSON. Keep only records with
   `lang_code == "to"` (Tongan). Do **not** include records of other
   languages even if the name is similar (e.g. Tonga/Nyasa, `tog`).
   Report in `notes`: number of lines read, number kept, number of
   lines that failed to parse (a parse failure is never silently
   skipped).
2. Two kinds of explicit form → lemma statements are allowed:
   - **Non-lemma entries:** a record whose `senses[].form_of` (or
     `alt_of`) names a base word. `form` = `word`, `lemma` = the
     `word` inside `form_of`/`alt_of`, `tags` = `senses[].tags`.
   - **Headword forms:** items in `forms[]` of a lemma record. `form` =
     `forms[].form`, `lemma` = `word` of that record, `tags` =
     `forms[].tags`.
   Skip `forms[]` items that are only romanization/transliteration
   (`romanization`, `transliteration`, `canonical`, and similar service
   tags), and items with empty or placeholder form (`-`, `?`).
3. `upos` — fixed mapping from `pos`: `noun` → `NOUN`, `name` →
   `PROPN`, `verb` → `VERB`, `adj` → `ADJ`, `adv` → `ADV`,
   `pron` → `PRON`, `num` → `NUM`, `prep`/`postp` → `ADP`,
   `conj` → `CCONJ`, `particle` → `PART`, `intj` → `INTJ`,
   `det` → `DET`. A `pos` not listed → `upos: "_"` and record in
   `notes`. `num` cases are kept here (numeral sub-list); do not apply
   the §6.1.2 skip to this source.
4. `features` — only from `tags` that have a direct UD equivalent
   (`passive` → `Voice=Pass`, `singular`/`dual`/`plural` →
   `Number=Sing/Dual/Plur`, `first-person`/`second-person`/
   `third-person` → `Person=1/2/3`, `inclusive`/`exclusive` →
   `Clusivity=In/Ex`). A tag with no equivalent → not added; if no tag
   maps, `features: "_"`.
5. `sentence_id` — `kaikki_<word>` for the record that contains the
   statement; `token_id` — sequential integer within the record.
6. Lemma convention: **Wiktionary**. It may differ from Churchward
   (for example, which form is the base for suffixed or suppletive
   verbs). Record this in `annotation_type`; do not harmonize.
7. **Forbidden:** generating forms from rules; using `senses[].glosses`
   or `examples` text to guess a lemma; using records without an
   explicit `form_of`/`alt_of` or `forms[]` entry.
8. **Count sanity** in `notes`: records kept; pairs from `form_of`/
   `alt_of`; pairs from `forms[]`; dropped as trivial; dropped for
   service tags/empty forms; dropped for other reasons. The sum must
   equal the number of candidate pairs, otherwise it is a parsing bug —
   fix it before continuing.
9. Provenance: kaikki data is a processed Wiktionary dump. Record the
   dump date/version from the file name or metadata, and the license
   as stated in the attached file; if the file does not state it, write
   `"not stated in the attached file; Wiktionary content is normally
   CC BY-SA"` and do not claim more.

##### C. Grammars and paradigm tables

Source: `Churchward_Grammar`. `sentence_id` = chapter/section/table in
the form `Churchward_<section>_<table>` using the numbering printed in the
attached file (never a numbering you made up).

For each grammar, look for:

- **Paradigm tables** (pronouns by person/number/clusivity, possessive
  forms, verb forms where the table gives a base form). Each row is a
  form; the column header or caption gives the lemma and features.
  Every row is a separate case.
- **Annotated (glossed) example sentences** where a form is glossed with
  its base, or the text explicitly says "X is a form of Y".
- **Explicit form-to-base statements in the text**, e.g. "the passive of
  `X` is `Y`", "`Y` is the plural of `X`" (suppletive singular/plural
  verbs).
- **Suppletive and irregular forms** stated explicitly as such.

For each grammar-derived case record:

- `source` — the grammar name;
- `sentence_id` — section/page/table identifier
  (e.g. `<Grammar>_Ch4_Pronouns_Table4.1`);
- `token_id` — sequential integer within the section;
- `form` — exactly as printed;
- `lemma` — exactly as given by the grammar;
- `upos`, `features` — from the paradigm labels, using only UD feature
  names present in the ontology (Person, Number incl. `Dual`,
  Clusivity, Voice, Aspect, Poss, PronType, whichever are in scope). If
  the grammar gives no explicit tags — infer them from the headers; if
  inference is impossible — `features: "_"` and record this in `notes`.

**Forbidden:** extracting a bare word from a grammar and guessing its
lemma. Every pair must come from an **explicit** form-to-lemma
statement in the source.

##### D. Tongan lex (lexicon / exception table)

1. First determine the file format (Python dicts, TSV/CSV, JSON, text)
   and read it as UTF-8 with its real structure; state the format in
   `notes`. Do not guess the structure.
2. Allowed pairs: only those where the file explicitly maps a surface
   form (key/left column) to a lemma (value/right column). Entries that
   give only a gloss or only a headword are not pairs.
3. `upos` — from the dict/column name if it unambiguously gives a
   category (pronouns → `PRON`, verbs → `VERB`, etc.); otherwise
   `upos: "_"`. `features` — only from explicit columns/labels,
   otherwise `"_"`.
4. `sentence_id` — dict/table name (or file section) plus the key,
   e.g. `Tongan_lex_<dictname>_<key>`; `token_id` — sequential within
   the dict/table.
5. Skip pairs where form == lemma after `str.lower()`. Keep a lemma that
   occurs in no other source.
6. Record in `notes` where the lemmas come from (author, origin,
   license as stated in the file). If the file does not say, write
   "origin not stated" and do not invent one.
7. Count sanity as in B.8.

#### 6.3 Working with existing extractions

If partial extractions already exist in the working directory — keep
what is good, fix what is fixable, delete what is bad. Do not start from
scratch unless necessary.

---

### 7. Filtering, deduplication, split

1. **Trivial cases.** After `str.lower(form)` and `str.lower(lemma)`,
   keep the pair only if `form_lower != lemma_lower`. Preserve the
   **original** capitalization in the output.
2. **Deduplication** by `(form_lower, lemma_lower, upos)`. If a pair
   came from two sources — keep one record and list both in
   `sources: [...]`.
3. **Split by lemma, not by form.** Assign each **unique lemma** to
   `development` or `holdout` with a fixed `seed` in an **80/20**
   ratio. All forms of one lemma go to the same split.
4. **Thresholds:**
   - `development` ≥ **1000** cases;
   - `holdout` ≥ **300** cases.
   If the sources cannot provide that — see §3 "If a source yields less
   material than needed". **Do not** pad artificially and **do not**
   redistribute to hit a threshold.
5. **Reproducibility.** Record the `seed` in `selection.seed`. Shuffle
   the unique lemmas with this seed before splitting.
6. **POS diversity.** Do not skew toward one POS. Cover verbs, nouns,
   adjectives, pronouns, numerals and other classes; **deliberately**
   sample irregular / suppletive / homonymous forms. If the
   distribution is uneven, do not hide it.
7. **Source diversity.** Do not rely on one source if several are
   available. Record `by_source` in `counts`.

---

### 8. Checks before saving

Run these and fix problems **before** returning the files:

1. Both YAML files parse.
2. Both contain `language`, `sources`, `split`, `selection`, `counts`,
   `cases`.
3. For every case, `form_lower != lemma_lower`.
4. All `(form_lower, lemma_lower, upos)` triples are unique within a
   file.
5. No lemma appears in both `development` and `holdout`; no sentence
   appears in both.
6. `development` ≥ 1000 cases; `holdout` ≥ 300 cases. If not, `notes`
   contains the actual numbers and the reason.
7. Every case has a `source` naming one of the inputs.
8. For grammar- and dictionary-derived cases, `sentence_id` points to a
   real section/page/table/headword.
9. The recorded seed reproduces the same split when the procedure is
   re-run.
10. `counts.by_source`, `counts.by_upos`, `counts.by_feature` reflect
    what is actually in `cases` (spot-check at least three values by
    hand).
11. National characters (`ʻ`, macron vowels) survive reading and writing
    without replacement characters or silent change of the glottal-stop
    variant.
12. **Hallucination check** done: every pair/sentence is verified
    against the source; nothing is reconstructed or paraphrased.
13. **POS diversity check** done.
14. **Source diversity check** done.
15. **Use-case count check** done (actual number, not padded).

If any check fails — fix it before returning the files.

---

### 9. Anti-patterns (what you must NOT do)

- Using a summary or statistics page instead of the raw source.
- Including trivial cases (form == lemma).
- Inventing lemmas. If the source does not give a lemma — drop the case
  and record the reason in `notes`.
- Generating forms by rules and presenting them as gold.
- Lemmatizing raw texts yourself.
- Splitting by form instead of by lemma (this leaks).
- Mixing sources without recording the convention.
- Silently dropping cases. Every drop is accounted for in
  `selection.rule` or `notes`.
- Skipping the seed.
- Padding the dataset to reach a threshold.
- Normalizing `ʻ` variants or adding/removing macrons.
- Annotating use-cases yourself (translation is not annotation).
- Treating derived forms (`faka-` etc.) as inflectional on your own
  authority.
- Reconstructing, paraphrasing, or guessing forms.
- Outputting bare wordforms when annotated sentences exist.
- Relying on a single source when multiple are available.
- Inventing `sent_id`s or source locations.
- Taking lemmas or rules from OntoTongan.json.
- Asking questions instead of producing the files.
- Repeating a mistake that has already been corrected once.

---

### 10. Deliverable

Return **two YAML files** (UTF-8, valid YAML, no surrounding Markdown,
no prose between them):

- `tongan-development.yaml`
- `tongan-holdout.yaml`

If a file does not fit in one message — return it in parts, but each
part must itself be valid YAML or an explicit continuation of a single
YAML document.

### Required structure of each file

```yaml
language:
  name: Tongan
  iso639_3: ton
  iso639_1: to
sources:
  - name: "<source name: Churchward_Grammar | kaikki_Tongan | Tongan_lex>"
    url: "<URL or local file>"
    version: "<commit / release tag / edition / local file hash>"
    license: "<license>"
    annotation_type: "<one sentence, where the lemmas come from>"
  # repeat the block for every source actually used
split: "<development or holdout>"
selection:
  seed: 0
  rule: "<one sentence, how pairs were sampled, how many cases per lemma or sentence, which filters>"
counts:
  total_cases: 0
  by_source:
    "<source name>": 0
  by_upos:
    VERB: 0
    NOUN: 0
    PRON: 0
  by_feature:  # only features actually present in the sources
    Person:
      "1": 0
      "2": 0
      "3": 0
    Number:
      Sing: 0
      Dual: 0
      Plur: 0
    Clusivity:
      In: 0
      Ex: 0
    Voice:
      Pass: 0
    Aspect: {}
    PronType: {}
    Poss:
      "Yes": 0
cases:
  - sentence_id: "<page, section or headword ID>"
    token_id: 0
    form: "<surface, original capitalization and orthography kept>"
    lemma: "<lemma exactly as in the source>"
    upos: "<UPOS or _>"
    features: "<FEATS from the source or _>"
    source: "<source name>"
    use_case_type: "<sentence or wordform>"
    annotation_note: "<optional, if the annotation is suspicious>"
notes: |
  <optional; mandatory if thresholds are not met, see section 3>
```

### Header of the `holdout` file

Add to the `holdout` file's `notes`, as its first line:
`RESERVED FOR FINAL EVALUATION. MUST NOT BE SHOWN TO THE LEMMATIZER-BUILDING AGENT.`

---

### 11. Notes on special cases

- If a grammar gives a paradigm table with several rows (e.g. person ×
  number × clusivity) — **each row is a separate case**.
- If a dictionary or grammar gives a lemma that appears in no other
  source — **keep it**. It is a legitimate pre-annotated pair.
- Use only UD feature names that appear in OntoTongan.json or the UD
  guidelines; do not invent new names.
- Use `str.lower()`, **not** `casefold()`.
- If, after processing all sources, the totals are below the thresholds
  — **do not** try to close the shortfall with anything other than
  accurately recording it in `notes`. The next prompts will read those
  numbers and adjust their expectations.


## 3. Building a rule-based lemmatizer

**Purpose:** generate a local Python lemmatizer from the ontology and the development set, without using the holdout set.

```text
You are a Python engineer and a Tongan expert. Write one file,
`tongan_lemmatizer.py`, with the class `TonganLemmatizer` (a small helper
module for reading a dictionary format is allowed). Use only:

- `OntoTongan.json`;
- the files listed in its `lexicon_files`;
- `tongan-development.yaml`;
- the Python 3.11+ standard library (plus PyYAML for reading YAML).

Never read `tongan-holdout.yaml`: it is reserved for independent evaluation.

Required API:

class TonganLemmatizer:
    def __init__(self, ontology_path="OntoTongan.json",
                 dev_path="tongan-development.yaml") -> None: ...
    def lemmatize(self, form: str, upos: str, features: str = "_") -> dict[str, str]: ...
    def lemmatize_sentence(self, tokens: list[dict]) -> list[dict]: ...

Requirements:
1. Load the rules, rule statuses, lemma conventions and lexical exceptions
   from the ontology; do not write an independent, incompatible list of
   rules in the code. Build the lexicon from the ontology, its
   `lexicon_files` and the development set, keyed by (normalized form,
   UPOS).
2. Normalize before lookup: Unicode NFC; unify all glottal-stop variants (ʻ, ', ’, ʼ)
   to the form used in the lexicon; match with and without macrons (try the
   exact marked form first, then the unmarked form). Output
   the lemma in the spelling of the lexicon entry; PROPN lemmas keep the
   initial capital; rule outputs are lower case.
3. Apply in this order: exact entries of the development set, exact entries
   of the lexicon and word-list files, particle and pronoun tables from the
   ontology, then affix-stripping and reduplication rules confirmed by a known
   base in the lexicon, then rules with status `rule`, then `default_replacement`.
4. When the dictionary gives several analyses, rank them by agreement with the
   UD features and UPOS, then by how often the lemma occurs in the development set.
   Report rejected lemmas in `reason`.
5. Follow the lemma conventions of the ontology: how particles, auxiliaries,
   pronouns, honorific forms and compound-notation lemmas are lemmatized.
6. If no lexicon and no unambiguous rule can decide, use the rule's
   `default_replacement` and set `confidence="default"`; otherwise return
   the form unchanged in `lemma`, set `confidence="ambiguous"` and explain
   why in `reason`. Do not invent a lemma.
7. Support at least NOUN, PROPN, VERB, AUX, PRON, DET, ADJ, PART and the
   indeclinable classes (ADV, ADP, CCONJ, SCONJ, INTJ) through the dictionary. In
   `lemmatize_sentence` keep the original token, the lemma, the applied
   rule and the confidence: `exact`, `rule`, `lexicon`, `default` or
   `ambiguous`.
8. Add `evaluate(cases_path)` with exact-match accuracy and a breakdown by
   UPOS; it must write a CSV with form, expected, actual, UPOS, status and
   the reason for each error.
9. List the known limitations in the module docstring. Do not claim full
   lemmatization of Tongan.

Every result of `lemmatize` must have exactly the fields `lemma`, `rule`,
`confidence` and `reason`. For example:

{"lemma": "akoʻi", "rule": "transitive_suffix_i", "confidence": "lexicon", "reason": "other analyses: ['ako' + suffix -ʻi]"}

or, when nothing can decide:

{"lemma": "ia", "rule": "", "confidence": "ambiguous", "reason": "pronoun and demonstrative readings; UPOS and features do not decide"}

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

- `tongan_lemmatizer.py` (and its helper module, if any);
- `OntoTongan.json` and the files in its `lexicon_files`;
- `tongan-development.yaml`;
- `tongan-holdout.yaml`.

Before the run, record SHA-256 hashes of the code, the ontology and both
YAML files, and check them again before scoring. You must not change any of
them after you have seen any result. For every case run:

result = TonganLemmatizer().lemmatize(form, upos, features)
actual = result["lemma"]
passed = actual == lemma

Compare lemmas exactly, as Unicode strings in NFC; also report a second,
case-insensitive accuracy, but do not replace the exact one with it.

Create two files:

1. `tongan-evaluation-results.csv` with every case, without exception:
   sentence_id, token_id, form, expected, actual, upos, features, status,
   rule, confidence, reason.
2. `tongan-evaluation-report.md` with these sections:
   - source and version of the holdout set;
   - number of cases, correct answers, errors, exact-match accuracy and
     case-insensitive accuracy;
   - accuracy and number of cases by UPOS;
   - accuracy by form type where the features allow it
     (person, number, clusivity, tense, voice);
   - how many cases were answered by the lexicon, by a rule, by a default
     or returned as ambiguous, and the accuracy of each group;
   - all errors with ID, form, expected and actual lemma;
   - error groups: missing lexicon entry, wrong analysis of a homograph,
     spelling variant (glottal stop encoding, macrons, hyphenation),
     corpus lemma convention, derived form with wrong base (affix, reduplication),
     capitalization, particle or pronoun table, annotation 
     (placeholder or alternative lemma), other;
   - an ablation: the same lemmatizer built without the development set
     (ontology and lexicon files only), to show how much the result depends
     on corpus-derived lexicon;
   - limitations of the test and concrete next improvements.

Do not delete failed cases, do not correct the gold annotation and do not
round results in a way that hides errors. If the code does not run, that is
also a result: give the traceback and set accuracy to `not computed`.
```
