You are an expert in the Chinese language and Python. Create a rule-based lemmatizer for Chinese based on the OntoChinese.json ontology.

Language context
- Morphological type: isolating
- Word order: SVO
- Categories: aspect, modality, classifiers
- Features: tones, classifiers, aspect particles
- Writing system: 汉字 + pinyin
- Irregular forms: 俩 (= 两个), 仨 (= 三个), 甭 (= 不用), 别 (= 不要), 冇 (dialectal negation), 卅 (= 三十), 廿 (= 二十), 咋 (= 怎么), 啥 (= 什么), 俺 (= 我), 咱 (= 咱们), 怹 (polite 他), 妳 (feminine 你), 牠 (inanimate 它), 祂 (divine 他), 这不 (= 这不是), 那啥 (= 那个什么)

Requirements

Input
Ontology JSON populated according to GOLD OntoLing.

Output
Class ChineseLemmatizer with methods:
- lemmatize(word, pos=None) -> Dict — lemma, POS, features, confidence
- lemmatize_sentence(sentence) -> List[Dict] — by tokens
- batch_lemmatize(words) -> List[Dict]
- generate_forms(lemma, pos) -> List[Dict] — form generation
- evaluate(test_data) -> Dict — accuracy

Architecture
- detect_pos(word) — part-of-speech detection
- _strip_noun_affixes(word) — removal of noun affixes
- _strip_verb_affixes(word) — removal of verb affixes
- _lemmatize_noun/verb/adj/pron/num/classifier/particle/conj — methods for each POS
- _handle_composite(text) — composite forms

Order of checks in detect_pos
1. Exact dictionaries (pronouns, numerals, adjectives, classifiers, conjunctions, particles, nouns, derived_nouns)
2. Verb stems and aspect forms
3. Possessive particle 的 (STRICT check, BEFORE verb)
4. Adjective suffixes (comparative constructions 比, 更, 最)
5. Adjectival formatives (derivational)
6. Ordinal numerals (第 + numeral)
7. Infinitives and modal constructions
8. Verb prefixes and resultative morphemes
9. Verb endings (STRICT check: 了, 着, 过)
10. Plural suffixes (们)
11. Case particles and postpositions
12. Default: noun

Dictionaries (in __init__, if necessary)
- known_nouns, known_adjectives, known_adverbs
- known_verbs, stem_to_infinitive, infinitive_to_past, infinitive_to_stem
- aspect_stems, all_verb_stems
- personal_pronouns, numerals, classifiers, postpositions, conjunctions, particles
- irregular_comparatives (if any)
- known_derived_nouns (whitelist of lexicalized words)
- abstract_noun_bases (for -性, -化, -度 and analogues)

Rules from the ontology
Load from the ontology:
- Plural suffixes: ["们"]
- Case suffixes: [] (Chinese has no case suffixes in the traditional sense; case relations are expressed by postpositions and word order)
- Possessive suffixes: ["的"]
- Verb endings: ["了", "着", "过"]
- Verb prefixes: [] (aspect markers follow the verb; the prepositive progressive 在/正在 is a separate case)
- Derivational suffixes: ["性", "化", "度", "者", "家", "员", "手", "人"]

Features of the Chinese language
- Aspect markers: 了 (perfective), 着 (durative/progressive), 过 (experiential aspect) — follow immediately after the verb
- Progressive aspect is also expressed by prepositive 在 or 正在 + verb
- Plural: 们 is used with personal pronouns and animate nouns (people, sometimes animals); with inanimate nouns — only for stylistic purposes
- Possessive particle 的: links a modifier and the modified, marks possession
- Comparative constructions: 比 + X + 更/最 + adjective; 比字句 for comparison, 最 for superlative
- Ordinal numerals: 第 + numeral (第一, 第二), or numeral + classifier + noun (三楼, 四号)
- Classifiers: obligatory before a noun with a numeral; 个 is the universal classifier; specialized: 辆 (vehicles), 本 (books), 张 (flat objects), etc.
- Postpositions: 里, 外, 上, 下, 前, 后 — express spatial relations, follow the noun (家里, 校外, 桌上)
- Structural particles: 的 (attributive), 地 (adverbial), 得 (complementary)
- Conjunctions: 和, 跟, 同, 与 (connective), 或, 或者 (disjunctive), 但, 但是 (adversative), 因为...所以 (causal), 虽然...但是 (concessive)
- Derivational suffixes: 者, 家, 员, 手 (agent), 性, 度 (abstract nouns), 化 (process/transformation)

Fallback
If not found — return the original word with confidence=0.3.

Composite forms
Handle:
- Verb reduplication: 看看, 试试 (softening/briefness)
- Adjective reduplication: 红红的, 干干净净
- Verb + aspect marker: 吃了, 看着, 去过
- Verb + resultative morpheme: 看完, 听懂, 做好
- Noun + 们: 学生们, 朋友们
- Modifier + 的 + noun: 我的书, 红色的花
- Numeral + classifier + noun: 三辆车, 五本书
- 第 + numeral: 第一, 第二

Cache
@lru_cache for lemmatize_word.

Tests
Create create_test_suite() with {{N_TESTS}} tests covering:
- Basic nouns: 书, 人, 水, 学校
- Plural: 学生们, 朋友们, 我们, 你们, 他们
- Aspect forms: 吃了, 看着, 去过, 吃过了
- Negative forms: 不吃, 没吃, 别吃, 没有去过
- Adjectives: 大, 小, 好, 更漂亮, 最好
- Adjective formatives (derivational): 漂亮 + 的, 红红的
- Numerals: 三, 五, 第一, 第三, 三辆车
- Pronouns: 我, 你, 他, 她, 我们, 你们, 他们, 自己
- Classifiers: 个, 本, 辆, 张, 只
- Postpositions: 家里, 桌上, 校外, 门前
- Conjunctions: 和, 或者, 但是, 因为...所以
- Particles: 的, 地, 得, 了, 着, 过, 吗, 呢, 吧
- Composite forms: 看看, 红红的, 看完, 听懂
- Derived nouns: 工作者, 作家, 教员, 科学家 (agent); 可能性, 复杂度 (abstract); 现代化, 工业化 (process)
- Irregular forms: 俩 (两个), 仨 (三个), 甭 (不用), 别 (不要), 咋 (怎么), 啥 (什么), 廿 (二十), 卅 (三十)

Output format
Full class code + main() with CLI (argparse). No explanations.

Appendices:
- OntoChinese.json
