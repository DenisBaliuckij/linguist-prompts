You are an expert in the Chukchi language and Python. Create a rule-based lemmatizer for the Chukchi language based on the OntoChukchi.json ontology.

Language context
- Morphological type: agglutinative-incorporating, predominantly suffixal, with elements of prefixation
- Word order: SVO (basic), but word order is free; postposition of the predicate is typical
- Categories: case, number, person, tense, aspect, mood, incorporation, possessiveness
- Features: vowel harmony, incorporation of a noun into a verb, ergative construction, reduplication, many cases
- Writing system: Cyrillic (from 1931 — Latin, from 1937 — Cyrillic)
- Irregular forms: Chukchi does not have a large number of truly irregular forms; suppletion is rare and mainly concerns personal pronouns (I — ымы, you — гыт, he — ытлён) and some verbs of motion

Requirements

Input
Ontology JSON populated according to GOLD OntoLing.

Output
Class ChukchiLemmatizer with methods:
- lemmatize(word, pos=None) -> Dict — lemma, POS, features, confidence
- lemmatize_sentence(sentence) -> List[Dict] — by tokens
- batch_lemmatize(words) -> List[Dict]
- generate_forms(lemma, pos) -> List[Dict] — form generation
- evaluate(test_data) -> Dict — accuracy

Architecture
- detect_pos(word) — part-of-speech detection
- _strip_noun_affixes(word) — removal of noun affixes
- _strip_verb_affixes(word) — removal of verb affixes
- _lemmatize_noun/verb/adj/pron/num/postp/conj/part — methods for each POS
- _handle_composite(text) — composite and incorporated forms

Order of checks in detect_pos
1. Exact dictionaries (pronouns, numerals, adjectives, postpositions, conjunctions, particles, nouns, derived_nouns)
2. Verb stems and aspect-tense forms
3. Possessive suffixes (STRICT check, BEFORE verb)
4. Adjective suffixes (attributive, qualitative forms)
5. Adjectival formatives (derivational)
6. Ordinal numerals
7. Infinitive and masdar forms (-н, -к, -ӈ)
8. Verb prefixes and incorporated morphemes
9. Verb endings (STRICT check: person, number, tense)
10. Plural suffixes
11. Case suffixes
12. Default: noun

Dictionaries (in __init__, if necessary)
- known_nouns, known_adjectives, known_adverbs
- known_verbs, stem_to_infinitive, infinitive_to_past, infinitive_to_stem
- verb_stems, all_verb_stems
- personal_pronouns, numerals, postpositions, conjunctions, particles
- irregular_comparatives (if any)
- known_derived_nouns (whitelist of lexicalized words)
- abstract_noun_bases (for -н/-ӈ/-к and analogues)
- incorporation_bases (frequent incorporated stems: -йыл- water, -кока- cauldron, -вэт- fat, -ным- house)

Rules from the ontology
Load from the ontology:
- Plural suffixes: ["-т", "-ыт", "-эт", "-ув", "-ва"] (for example: кэли — кэлит, ылвэ — ылвыт, вэтвын — вэтвынэт)
- Case suffixes: ["-к (absolutive)", "-ан/-эн (locative)", "-ӈ (directive)", "-гат/-га (elative)", "-кэ/-ка (dative)", "-гит/-гыт (instrumental)", "-э/-а (ergative)", "-л (possessive)"] and others — about 10 cases
- Possessive suffixes: ["-йын/-йэн (1st person singular)", "-йыт/-йэт (2nd person singular)", "-йн/-эн (3rd person singular)", "-йымы/-йэмы (1st person plural)", "-йыты/-йэты (2nd person plural)", "-йыт/-йэт (3rd person plural)"] — agree in person, number, and vowel harmony
- Verb endings: ["-ӈ (1st person singular)", "-т (2nd person singular)", "-нын/-нэн (3rd person singular)", "-мык (1st person plural)", "-тык (2nd person plural)", "-ркын/-ркэн (3rd person plural)", "-ӈэ (past)", "-ркын (present)", "-н (future)"] — depend on tense, mood, person, number
- Verb prefixes: ["на- (past)", "рэ- (present/future)", "та- (interrogative)", "ма- (negative)", "ӈа- (imperative)"] and others
- Derivational suffixes: ["-льын (possession, 'having something')", "-лӈын (privation, 'without something')", "-чгын (agent of an action)", "-тко (place of an action)", "-льы (abstract quality)"]

Features of the Chukchi language
- Vowel harmony: vowels are divided into hard (а, о, у, ы, э) and soft (э, и, е); suffixes have variants with hard and soft vowels (for example, -йын / -йэн, -нын / -нэн)
- Incorporation: a noun can be incorporated into a verb before the root, forming a compound word (for example: ынпыӄэвъё — 'to buy' + ымныӈ — 'house' → ынпыӄэвъёмын — 'to build a house')
- Ergative construction: the subject of a transitive verb is marked with the ergative case (-э/-а), the direct object — with the absolutive
- Polysynthesis: one word can carry the meanings of several morphemes (person, number, tense, aspect, mood, incorporated stems)
- Reduplication: often used to express intensity or plurality (for example: кыпкып — 'very strong')
- Aspect: suffixes -ӈэ (perfective/past), -ркын (imperfective/present), -н (future), -тку (momentary action)
- Mood: indicative, imperative (imperative with the prefix ӈа-), interrogative (та-), negative (ма-)
- Personal pronouns: ымы (I), гыт (you), ытлён (he), ытлоан (she), мури (we), тури (you all), ытри (they)
- Postpositions: -к, -ӈ, -гат, etc. — express spatial and temporal relations, often merge with nouns
- Conjunctions: mostly borrowed or absent; connection is expressed by word order and verb forms
- Particles: -м, -ӈ, -к, etc. — emphatic, interrogative, demonstrative

Fallback
If not found — return the original word with confidence=0.3.

Composite forms
Handle:
- Incorporation of a noun into a verb: ынпыӄэвъёмын (to build a house), ӄэвъёйылвын (to drink water)
- Verb + aspect suffix: ыӈэӈэ (said), ыӈэркын (says), ыӈэн (will say)
- Noun + possessive suffix: ымныӈйын (my house), ымныӈйыт (your house)
- Noun + case suffix: ымныӈан (in the house), ымныӈӈ (to the house)
- Noun + plural suffix: кэлит (people), ылвыт (grasses)
- Adjective + attributive suffix: ынпыльын (strong), ынпылӈын (powerless)
- Reduplication: кыпкып (very strong), нымным (village — plural of ным)
- Numeral + classifier: there are no classifiers in the classical sense; numerals combine with nouns directly (нэнуккэт — 'three people')

Cache
@lru_cache for lemmatize_word.

Tests
Create create_test_suite() with {{N_TESTS}} tests covering:
- Basic nouns: ымныӈ (house), кэли (person), йыл (water), ным (village), яраӈы (yaranga), ылвэ (grass)
- Plural: кэлит (people), ылвыт (grasses), ымныӈыт (houses), яраӈыт (yarangas)
- Cases: ымныӈан (in the house), ымныӈӈ (to the house), ымныӈгат (from the house), ымныӈэ (house — erg.), ымныӈк (house — abs.)
- Possessive (all persons): ымныӈйын (my house), ымныӈйыт (your house), ымныӈйн (his house), ымныӈйымы (our house), ымныӈйыты (your house), ымныӈйыт (their house)
- Verbs (all tenses, all persons): ыӈэӈэ (I said), ыӈэт (you said), ыӈэнын (he said), ыӈэмык (we said), ыӈэтык (you all said), ыӈэркын (I say), ыӈэн (I will say)
- Negative forms: маӈыӈэ (I did not say), маӈыӈэт (you did not say), маӈыӈэнын (he did not say)
- Adjectives: ынпы (strong), ынпыльын (having strength), ынпылӈын (powerless), ынпыльы (strength)
- Adjective formatives (derivational): -льын (possession), -лӈын (privation), -льы (abstract quality)
- Numerals: ыннэн (one), нырэ (two), нырок (three), нырак (four), мытлыӈэн (five), ыннэнкэ (first)
- Pronouns: ымы (I), гыт (you), ытлён (he), ытлоан (she), мури (we), тури (you all), ытри (they)
- Postpositions: -к, -ӈ, -гат, -ан, -га (express spatial relations)
- Conjunctions: ынкы (and), ынан (or), но (but), ытъэ (because)
- Particles: -м, -ӈ, -к (emphatic, interrogative)
- Composite forms: ынпыӄэвъёмын (to build a house), ӄэвъёйылвын (to drink water), ымныӈйын (my house), кэлит (people)
- Derived nouns: -чгын (agent of an action: ынпыӄэвъёчгын — builder), -тко (place of an action: ынпыӄэвъётко — construction site)
- Irregular forms: ымы (I), гыт (you), ытлён (he) — suppletive forms of personal pronouns

Output format
Full class code + main() with CLI (argparse). No comments, this is important.

Appendices:
- OntoChukchi.json
