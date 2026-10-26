# Prompt 2: Build gold use-cases (development + holdout)

## Purpose

Extract two disjoint sets of gold "word form → lemma" pairs for Tajik, so that they can be used later to build (Prompt 3) and independently evaluate (Prompt 4) a rule-based lemmatizer. The `development` set may be shown to the lemmatizer-building agent. The `holdout` set must remain hidden until the final independent evaluation.

## Role

You are a linguistic data curator working on Tajik (забони тоҷикӣ, ISO 639-3: tgk). You prepare reproducible, verifiable gold datasets. You do not predict lemmas, you do not correct the sources, and you do not invent examples.

## Inputs

Use only the following, which are attached:

1. **`OntoTajik.json`** — the ontology built in Prompt 1. Use it for the language name, ISO codes, and the set of UPOS tags and morphological features that are in scope. Do not take lemmas or morphological rules from the ontology while building the gold sets.

2. **`apertium-tgk.tgk.dix`** — the Apertium morphological dictionary for Tajik. This is a **pre-annotated** source: each `<e>` entry contains an `<l>` (surface form) and an `<r>` (lemma + morphological tags). The lemma is given by the source, not predicted by you. Parse only the `<pardef>` definitions and the entries that reference them. Do not guess lemmas from surface forms.

3. **`tajik_lexdata.py`** — a Python module with exception tables (pronouns, irregular present stems, broken plurals, surface-form overrides). Each entry maps a surface form to a lemma. These are pre-annotated pairs; use them as-is.

4. **The attached Tajik grammars**:
   - **Khojayori, N. & Thompson, M. (2009).** *Tajiki Reference Grammar for Beginners.* Georgetown University Press.
   - **Ido, S. (2005).** *Tajik.* LINCOM Europa.
   - **Rzehak, L. (1999).** *Tadschikische Studiengrammatik.* Reichert.
   - **Windfuhr, G. & Perry, J. R. (2009).** "Persian and Tajik." In *The Iranian Languages*, Routledge.

   From the grammars, extract only **paradigm tables and example sentences that are already annotated with a lemma or that are presented as a form-to-base correspondence**. Do not extract a bare word and guess its lemma. Every grammar-derived pair must be traceable to a specific page, section, or paradigm table in the source.

5. **The corpus documentation (Input C, if provided)** — for lemma conventions only. Never as a source of test items.

## Outputs

Two YAML files:

- `tajik-development.yaml` — for building the lemmatizer.
- `tajik-holdout.yaml` — for independent evaluation.

Both files must be valid UTF-8 YAML and must parse without errors.

## Required structure of each YAML file

```yaml
language:
  name: Tajik
  iso639_3: tgk
  iso639_1: tg
sources:
  - name: Apertium Tajik morphological dictionary
    url: https://github.com/apertium/apertium-tgk
    version: <commit hash or release tag>
    license: <license>
    annotation_type: <statement from the repository that lemmas are manual or derived from paradigms>
  - name: tajik_lexdata.py
    version: <commit or local file hash>
    annotation_type: <one sentence: exception table with manual lemma mappings>
  - name: Khojayori & Thompson (2009)
    annotation_type: <one sentence: paradigm tables and annotated example sentences>
  - name: Ido (2005)
    annotation_type: <...>
  - name: Rzehak (1999)
    annotation_type: <...>
  - name: Windfuhr & Perry (2009)
    annotation_type: <...>
split: development | holdout
selection:
  seed: <integer seed used for random selection>
  rule: <one sentence: how pairs were sampled, how many cases per lemma, and any filters>
counts:
  total_cases: <int>
  by_source: {apertium: ..., lexdata: ..., khojayori_thompson: ..., ido: ..., rzehak: ..., windfuhr_perry: ...}
  by_upos: {NOUN: ..., VERB: ..., ADJ: ..., ...}
  by_feature:
    Case: {Nom: ..., Acc: ..., ...}
    Number: {Sing: ..., Plur: ...}
    VerbForm: {Fin: ..., Part: ..., Inf: ...}
    Tense: {Pres: ..., Past: ...}
cases:
  - sentence_id: <string; for grammar-derived cases, the section/page ID>
    token_id: <integer ID; for grammar-derived cases, a sequential integer within the source section>
    form: <surface form, original capitalization kept>
    lemma: <lemma, exactly as in the source>
    upos: <UPOS tag>
    features: <morphological features, from the source's tags or `_`>
    source: <name of the source this case was taken from>
```

If a source contributes fewer non-trivial cases than expected, or if the total sizes fall below the thresholds, add a top-level `notes` field explaining:

- what was expected,
- what was actually produced,
- why the source could not yield more (e.g. the `.dix` file only lists a subset of paradigms, or the grammar only annotates a limited number of tables),
- what the consequences for Prompts 3 and 4 are (smaller training set, smaller evaluation set, reduced statistical significance).

## Algorithm

### Step 1: Extract from `apertium-tgk.tgk.dix`

1. Parse the XML. Identify all `<pardef>` blocks. Each `<pardef>` defines a paradigm class (e.g. `кард.ан__vblex`, `будан__vbser`).
2. For each `<e>` entry inside a `<pardef>`, extract:
   - `surface` = the text inside `<l>`;
   - `lemma` = the text inside `<r>`, up to the first `<s n="...">` tag;
   - `tags` = all `<s n="...">` values inside `<r>`.
3. For dictionary entries that reference a paradigm (`<e><p><l>...</l><r>...</r></p><par n="..."/></e>`), combine the stem with each paradigm ending to produce the full surface form and its lemma.
4. Map Apertium tags to UPOS and morphological features. Use this mapping:
   - `n` → `NOUN`
   - `vblex`, `vbser`, `vbmod` → `VERB`
   - `adj` → `ADJ`
   - `adv` → `ADV`
   - `prn` → `PRON`
   - `num` → `NUM`
   - `pr`, `post` → `ADP`
   - `cnjcoo`, `cnjsub` → `CCONJ` / `SCONJ`
   - `part` → `PART`
   - `ij` → `INTJ`
   - For verbs: `inf` → `VerbForm=Inf`; `pp` → `VerbForm=Part`; `pri` → `Tense=Pres`; `past` → `Tense=Past`; `p1`/`p2`/`p3` → `Person=1`/`2`/`3`; `sg`/`pl` → `Number=Sing`/`Plur`; `neg` → `Polarity=Neg`.
   - For nouns: `sg`/`pl` → `Number=Sing`/`Plur`; `acc` → `Case=Acc`; if no case tag, leave `Case` empty.
   - For adjectives: `comp` → `Degree=Cmp`; `sup` → `Degree=Sup`.
   - If a tag has no direct UD equivalent, leave the corresponding feature empty.
5. Skip entries whose lemma is identical to the surface form after lower-casing. Skip tokens tagged as `punct`, `sym`, `num` (unless you are building a numeral sub-list), or `x`.

#### Specific checks for the `.dix` file

Before using the extracted pairs, verify that the `.dix` file was parsed correctly:

- **Well-formedness.** The file parses as XML without errors. If it does not, record the exact parse error in `notes` and do not proceed with a partial parse that silently drops entries.
- **Paradigm resolution.** Every `<par n="..."/>` reference resolves to a `<pardef>` block that is defined in the file or in an included file. List unresolved references in `notes`.
- **Stem + ending composition.** For each referenced paradigm, spot-check at least five entries by hand: the concatenation of the `<l>` inside the dictionary `<e>` and each `<l>` inside the paradigm must produce the surface form, and the `<r>` inside the paradigm must combine with the `<r>` inside the dictionary entry to produce the lemma. If a spot-check fails, the paradigm is being misread; do not include entries from it, and record the failing paradigm in `notes`.
- **No double extraction.** A form that appears both as a standalone `<e>` and as a stem-plus-paradigm combination must be recorded once, with a `sources` field listing both origins.
- **No silent drops.** If a paradigm is skipped, the reason must be recorded in `notes`. Reasons may include: unresolved `<par>` reference, missing lemma in `<r>`, malformed XML, or a tag with no mapping.
- **Encoding.** The file is read as UTF-8. Verify that Cyrillic characters (`ҳ`, `қ`, `ғ`, `ҷ`, `ӣ`, `ӯ`, `ҷ`) survive the read without replacement characters.
- **Count sanity.** Report in `notes`:
  - the number of `<pardef>` blocks parsed,
  - the number of dictionary `<e>` entries that reference a paradigm,
  - the total number of surface forms produced,
  - the number of surface forms dropped as trivial (form == lemma),
  - the number of surface forms dropped for any other reason.
  These four numbers must add up to the total number of `<e>` entries processed. If they do not, there is a parsing bug; fix it before continuing.

#### If Apertium yields fewer cases than the thresholds require

The thresholds are:

- `development` ≥ 1000 cases,
- `holdout` ≥ 300 cases.

If, after parsing `apertium-tgk.tgk.dix`, `tajik_lexdata.py`, and the grammars, the totals are below these thresholds:

1. **Record the actual number.** Do not fabricate cases to reach the threshold.
2. **Explain the shortfall** in a top-level `notes` field:
   - how many cases each source actually contributed,
   - why the source could not yield more (e.g. the `.dix` file only covers a subset of the lexicon, the grammars only annotate a limited number of paradigm tables, `tajik_lexdata.py` is an exception list and not a full dictionary),
   - which specific threshold could not be met (`development`, `holdout`, or both),
   - the consequences for downstream prompts: smaller training set for Prompt 3, smaller evaluation set for Prompt 4, reduced statistical power, and a note that the holdout score will have a wider confidence interval.
3. **Do not redistribute** cases from one split to the other to hit the threshold. The 80/20 split by lemma must stay intact. If the total number of unique lemmas is too small, `holdout` will be smaller than 300, and that must be reported, not hidden.
4. **Do not borrow cases from an external corpus** that was not listed as an input. If the thresholds cannot be reached from the listed inputs, the correct output is a smaller dataset with an explicit `notes` explanation, not a padded one.

### Step 2: Extract from `tajik_lexdata.py`

1. Import the module. For each dict (`PRONOUNS`, `IRREGULAR_PRESENT`, `BROKEN_PLURALS`, `SURFACE`, `SPECIAL`, `IZOFA_PREPS`), read the key–value pairs.
2. The key is the surface form, the value is the lemma.
3. Assign UPOS from the dict name:
   - `PRONOUNS` → `PRON`
   - `IRREGULAR_PRESENT` → `VERB`
   - `BROKEN_PLURALS` → `NOUN`
   - `SURFACE`, `SPECIAL`, `IZOFA_PREPS` → infer from the lemma where possible; if ambiguous, leave `UPOS` as `_`.
4. Skip any pair where the surface form equals the lemma after lower-casing.

### Step 3: Extract from the grammars

For each grammar, look for:

- **Paradigm tables** (conjugation tables, declension tables, pronoun tables). Each row is a form; the column header or the table caption gives the lemma and features. For example, in a verb paradigm table, the row `меравам` under the column “1sg present” in the table for `рафтан` gives the pair `меравам → рафтан` with `UPOS=VERB`, `Tense=Pres`, `Person=1`, `Number=Sing`.
- **Annotated example sentences** where a form is glossed with its lemma or where the text explicitly states “X is a form of Y”.
- **Form-to-base correspondences in the text**, e.g. a sentence like “The past stem of `кардан` is `кард`” gives the pair `кард → кардан` with `UPOS=VERB`, `VerbForm=Part` (or `Tense=Past` depending on the context).
- **Suppletive comparatives**: a table or sentence stating that `беҳтар` is the comparative of `хуб` gives `беҳтар → хуб` with `UPOS=ADJ`, `Degree=Cmp`.
- **Irregular verb stems**: a table listing present and past stems gives the pairs `present_stem → infinitive` and `past_stem → infinitive`, both with `UPOS=VERB`.

For each grammar-derived case, record:
- `source`: the grammar name (e.g. `Ido (2005)`).
- `sentence_id`: the section or page identifier (e.g. `Ido2005_Ch3_Verbs_Table3.2`).
- `token_id`: a sequential integer within that section.
- `form`: the surface form exactly as printed in the grammar.
- `lemma`: the lemma exactly as given by the grammar.
- `upos` and `features`: derived from the paradigm labels in the grammar. If the grammar does not give morphological tags explicitly, use the column/row headers to infer them; if inference is not possible, leave `features` as `_` and record that in `notes`.

Do not extract a bare word from a grammar and guess its lemma. Every grammar-derived pair must come from an explicit form-to-lemma statement in the source.

### Step 4: Filter, deduplicate, and split

1. **Filter trivial cases.** After applying `str.lower()` to both `form` and `lemma`, keep the pair only if `form_lower != lemma_lower`. Store the **original** capitalization in the output.
2. **Deduplicate by `(form_lower, lemma_lower, upos)`.** If the same pair appears from two sources (e.g. Apertium and a grammar), keep one entry and record both sources in a `sources` list field on that case.
3. **Split by lemma, not by form.** Assign each **unique lemma** to `development` or `holdout` with a fixed random seed and an 80/20 ratio. All cases of a lemma go into the same set. This prevents leakage: a form of the same lemma cannot appear in both sets.
4. **Minimum sizes:** `development` ≥ 1000 cases, `holdout` ≥ 300 cases. If a source does not contribute enough non-trivial cases, record the actual number and explain the shortfall in `notes` (see Step 1 above). Do not silently borrow from another split, and do not pad with invented cases.
5. **Sample reproducibly.** Record the seed in `selection.seed`. Shuffle the unique lemmas with that seed before splitting.

### Step 5: Count and report

In each file, count cases by source, by UPOS, and by the main morphological features (`Case`, `Number`, `VerbForm`, `Tense`, `Person`, `Degree`). Report the actual distribution, even if uneven. Do not hide gaps. If the totals are below the thresholds, report the actual numbers in `notes` and state that the thresholds were not met.

## Anti-hallucination rules

- **Do not invent lemmas.** Every lemma must come from the source: the `<r>` element in Apertium, the value in `tajik_lexdata.py`, or an explicit statement in a grammar.
- **Do not guess a lemma from a form.** If a form appears in a grammar without a stated lemma, do not include it.
- **Do not correct, normalize, or rewrite gold lemmas.** Keep placeholders, alternative spellings, and annotation quirks exactly as they appear.
- **Do not merge or split tokens** to make a case “cleaner.”
- **Do not use a statistics page as a substitute for the raw source.** Parse the `.dix` file itself, import the `.py` module itself, read the grammar PDFs/pages themselves.
- **Do not mix lemma conventions across sources.** Apertium, `tajik_lexdata.py`, and each grammar may follow different conventions (e.g. participles under the verb vs. separate lemmas, spelling of `ӣ`/`и`). Record the convention per source in `sources.annotation_type`. Do not normalize one source’s convention to another’s.
- **Do not pad the dataset to reach the thresholds.** If the sources do not yield enough cases, report the actual number and explain.

## Verification (before writing the outputs)

Run these checks and fix problems before returning anything:

1. Both YAML files parse.
2. `language`, `sources`, `split`, `selection`, `counts`, `cases` are present in both files.
3. All `cases` have `form_lower != lemma_lower`.
4. All `(form_lower, lemma_lower, upos)` triples are unique within a file.
5. No lemma appears in both `development` and `holdout`.
6. `development` has at least 1000 cases; `holdout` has at least 300 cases. If not, `notes` must state the actual numbers and the reason.
7. Every case has a `source` field naming one of the inputs.
8. For grammar-derived cases, `sentence_id` points to a real section, page, or table in the grammar.
9. The recorded seed reproduces the same split when the procedure is re-run.
10. `counts.by_source`, `counts.by_upos`, and `counts.by_feature` reflect what is actually in `cases` (spot-check at least three values by hand).
11. For the `.dix` parse: the counts reported in `notes` add up (paradefs parsed, dictionary entries with paradigms, surface forms produced, trivial drops, other drops). If they do not, there is a parsing bug.
12. For the `.dix` parse: at least five stem-plus-paradigm combinations were spot-checked by hand against the raw XML.

If any of these checks fails, fix it before returning the files.

## Anti-patterns to avoid

- **Using a statistics page as a substitute for the raw source.** You must parse the `.dix` file, import the `.py` module, and read the grammars themselves.
- **Including trivial cases.** A pair whose form equals its lemma after case folding is useless.
- **Inventing lemmas.** If the source does not give a lemma, drop the case and record why in `notes`.
- **Splitting by form instead of by lemma.** This leaks the same lemma into both sets and makes the holdout score meaningless.
- **Mixing sources without recording the convention.** Each source has its own lemma conventions; record them in `sources.annotation_type`.
- **Dropping cases silently.** Every dropped case must be accounted for in `selection.rule` or `notes`.
- **Skipping the seed.** A selection without a recorded seed cannot be reproduced.
- **Padding the dataset to reach the thresholds.** If the sources do not yield enough cases, report the actual number, not an inflated one.
- **Silently accepting a partial `.dix` parse.** If some paradigms are unresolved, or some entries are dropped for a parse reason, that must appear in `notes` with the count.

## Output format

Return only the two YAML files, as valid UTF-8, with no Markdown around them and no prose. If a file is too long to return in one message, return it in parts, but each part must itself be valid YAML or must clearly continue a single YAML document.

## Notes

- The ontology is used only to know the language name, the ISO codes, and the set of UPOS tags and morphological features that are in scope. Do not take lemmas or morphological rules from the ontology while building the gold sets.
- The `holdout` file must not be used by any subsequent prompt until the final evaluation stage. If you produce it in the same working directory as the development file, name it clearly and state in the file header that it is reserved for evaluation only.
- If a grammar gives a paradigm table with 6 rows (1sg, 2sg, 3sg, 1pl, 2pl, 3pl) for a verb, each row is a separate case. Do not treat the whole table as one case.
- If `tajik_lexdata.py` contains a mapping whose lemma is not in any other source, keep it. It is a legitimate pre-annotated pair.
- Apertium tags may use different names than UD. Use the mapping in Step 1; do not invent new feature names.
- If, after all sources are processed, the totals are below the thresholds, do not attempt to fix the shortfall by any means other than recording it accurately in `notes`. The next prompts will read those numbers and adjust their expectations accordingly.
