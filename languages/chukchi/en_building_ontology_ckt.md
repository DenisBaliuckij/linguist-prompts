You are an expert in Chukchi (ckt) and linguistic typology. Create a complete ontology for this language in JSON format, following the GOLD OntoLing template.

Requirements

1. Structure — strictly according to the GOLD OntoLing template (see appendix).

2. Sources — use only academic grammars. List in meta.sources:
- The Grammar of Chukchi (Michael Dunn)

3. Level of detail — as in the attached OntoKon.json example.

4. Language-specific features:
- Morphological type: non-linear, polysynthetic, incorporating
- Word order: free (SOV is basic, but inversions are permitted; verify against the grammars)
- Categories: case, number, person, tense, aspect, mood, incorporation
- Features: incorporation, non-linear morphology, ablaut (vowel alternation), polysynthetic structure
- Writing system: Cyrillic (since the 1930s; Latin earlier)

5. Dialects — list the main groups (for example, Chaun, Anadyr, Kolyma), indicate phonetic/morphological differences.

6. Examples — all examples in Chukchi with transliteration and translation.

Mandatory sections

- meta (title, version, description, sources, language_name, iso_code, classification, speaker_population, location, dialects, standard_dialect, gold_base_uri)
- Core_Foundations (Language, Linguistic_System, Linguistic_Taxon, Genetic_Taxon, Geographic_Taxon, Political_Taxon, Endangerment_Taxon, Language_Family, Language_Subfamily, Dialect, The_Linguistic_Sign, Linguistic_Unit, Language_varieties)
- Phonetics_and_Phonology (Phonetics, Phonetic_Units, Phonetic_Features, Phonetic_Rules, Segment_Units — Consonants/Vowels, Suprasegmental_Units, Phonological_System, Orthographic_System)
- Morphology (Basic_Units — Word/Morpheme/Affix, Morphological_Operations — Inflection/Derivation, The_Lexicon_and_Paradigms, Morphological_Meanings_and_Categories, Key_Categories_for_Nouns, Key_Categories_for_Verbs, Morphological_Typology, Part_Of_Speech_Property, GOLD_Specific_Morphological_Classes, GOLD_Specific_Grammatical_Categories)
- Syntax (Core_Foundations, Syntactic_Categories_and_Features, Constituency_and_Phrase_Structure, Clause_and_Sentence_Types, Communicative_Categories, Syntactic_Relations)
- Semantics (Core_Theoretical_Foundations, Lexical_Semantics, Grammatical_Semantics, Semantics_of_the_Sentence, Reference_and_Quantification)
- Interfaces_and_Integration (Phonetics-Phonology, Phonology-Morphology, Morphology-Syntax, Syntax-Semantics, Semantics-Pragmatics)
- Relations_and_Properties (Object_Properties, Datatype_Properties)
- Lexicon_Overview (20-25 sample entries: nouns, verbs, adjectives)

Additional mandatory sections (language-specific):

- incorporation_rules (rules of incorporation: which roots can be incorporated, position, constraints)
- nonlinear_morphology (description of non-linear processes: ablaut, vowel alternation, reduplication)
- ablaut_patterns (table of vowel alternations in the stem: e → a, i → e, etc.)
- polysynthetic_structure (structure of the polysynthetic word: order of morphemes, template)
- vowel_harmony (if applicable — rules of vowel harmony)
- incorporation_types (nominal incorporation, verbal incorporation, etc.)

Quality requirements

- Do not invent facts. If unsure — use only data from the attached grammars.
- Cite sources for each language feature.
- Provide examples for each morphological category.
- Distinguish synchrony and diachrony.
- Note the unique features of the language (polysynthesis, incorporation, ablaut).
- For each non-linear form, indicate how it is formed and how to reverse it for lemmatization.

Output format

JSON only, without explanations. UTF-8. No comments.

Appendices:
- OntoKon.json (example of a finished ontology)
- GOLD OntoLing.json (structure template)
- The Grammar of Chukchi (Michael Dunn)
