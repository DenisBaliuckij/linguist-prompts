Ты — эксперт по Chukchi (ckt) и лингвистической типологии. Создай полную онтологию для этого языка в формате JSON, следуя шаблону GOLD OntoLing.

Требования

1. Структура — строго по шаблону GOLD OntoLing (см. приложение).

2. Источники — используй только академические грамматики. Перечисли в meta.sources:
- The Grammar of Chukchi (Michael Dunn)

3. Уровень детализации — как в приложенном примере OntoKon.json.

4. Язык-специфика:
- Морфологический тип: non-linear, polysynthetic, incorporating
- Порядок слов: свободный (SOV — базовая, но допустимы инверсии; уточнить по грамматикам)
- Категории: падеж, число, лицо, время, вид, наклонение, инкорпорация
- Особенности: инкорпорация, нелинейная морфология, аблаут (чередование гласных), полисинтетическая структура
- Письменность: кириллица (с 1930-х; ранее латиница)

5. Диалекты — перечисли основные группы (например, чаунский, анадырский, колымский), укажи фонетические/морфологические различия.

6. Примеры — все примеры на Chukchi с транслитерацией и переводом.

Обязательные разделы

- meta (title, version, description, sources, language_name, iso_code, classification, speaker_population, location, dialects, standard_dialect, gold_base_uri)
- Core_Foundations (Language, Linguistic_System, Linguistic_Taxon, Genetic_Taxon, Geographic_Taxon, Political_Taxon, Endangerment_Taxon, Language_Family, Language_Subfamily, Dialect, The_Linguistic_Sign, Linguistic_Unit, Language_varieties)
- Phonetics_and_Phonology (Phonetics, Phonetic_Units, Phonetic_Features, Phonetic_Rules, Segment_Units — Consonants/Vowels, Suprasegmental_Units, Phonological_System, Orthographic_System)
- Morphology (Basic_Units — Word/Morpheme/Affix, Morphological_Operations — Inflection/Derivation, The_Lexicon_and_Paradigms, Morphological_Meanings_and_Categories, Key_Categories_for_Nouns, Key_Categories_for_Verbs, Morphological_Typology, Part_Of_Speech_Property, GOLD_Specific_Morphological_Classes, GOLD_Specific_Grammatical_Categories)
- Syntax (Core_Foundations, Syntactic_Categories_and_Features, Constituency_and_Phrase_Structure, Clause_and_Sentence_Types, Communicative_Categories, Syntactic_Relations)
- Semantics (Core_Theoretical_Foundations, Lexical_Semantics, Grammatical_Semantics, Semantics_of_the_Sentence, Reference_and_Quantification)
- Interfaces_and_Integration (Phonetics-Phonology, Phonology-Morphology, Morphology-Syntax, Syntax-Semantics, Semantics-Pragmatics)
- Relations_and_Properties (Object_Properties, Datatype_Properties)
- Lexicon_Overview (20-25 sample entries: nouns, verbs, adjectives)

Дополнительные обязательные разделы (язык-специфичные):

- incorporation_rules (правила инкорпорации: какие корни могут инкорпорироваться, позиция, ограничения)
- nonlinear_morphology (описание нелинейных процессов: аблаут, чередование гласных, редупликация)
- ablaut_patterns (таблица чередований гласных в основе: e → a, i → e и т.д.)
- polysynthetic_structure (структура полисинтетического слова: порядок морфем, шаблон)
- vowel_harmony (если применимо — правила гармонии гласных)
- incorporation_types (номинальная инкорпорация, глагольная инкорпорация и т.д.)

Требования к качеству

- Не выдумывай факты. Если не уверен — используй только данные из приложенных грамматик.
- Указывай источники для каждой языковой особенности.
- Приводи примеры для каждой морфологической категории.
- Различай синхронию и диахронию.
- Отмечай уникальные черты языка (полисинтетизм, инкорпорация, аблаут).
- Для каждой нелинейной формы указывай, как она образуется и как её реверсировать для лемматизации.

Формат вывода

Только JSON, без пояснений. UTF-8. Без комментариев.

Приложения:
- OntoKon.json (пример готовой онтологии)
- GOLD OntoLing.json (шаблон структуры)
- The Grammar of Chukchi (Michael Dunn)