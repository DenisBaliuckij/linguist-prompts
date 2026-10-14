You are an expert in Chinese (cmn) and linguistic typology. Create a complete ontology for this language in JSON format, following the GOLD OntoLing template.
Requirements
1. Structure — strictly according to the GOLD OntoLing template (see appendix).
2. Sources — use only academic grammars. List in meta.sources:
- Mandarin Chinese A Functional Reference Grammar
3. Level of detail — as in the attached OntoKon.json example.
4. Language-specific features:
- Morphological type: isolating
- Word order: SVO
- Categories: aspect, modality, classifiers
- Features: tones, classifiers, aspect particles
- Writing system: 汉字 + pinyin
5. Dialects — list the main groups, indicate phonetic/morphological differences.
6. Examples — all examples in Chinese with transliteration and translation.
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
- aspect_particles, classifiers, tone_sandhi, word_segmentation
Quality requirements
- Do not invent facts. If unsure — use only data from the attached grammars.
- Cite sources for each language feature.
- Provide examples for each morphological category.
- Distinguish synchrony and diachrony.
- Note the unique features of the language.
Output format
JSON only, without explanations. UTF-8. No comments.
Appendices:
- OntoKon.json (example of a finished ontology)
- GOLD OntoLing.json (structure template)
- Mandarin Chinese A Functional Reference Grammar
