# Generalized · ontology

A language-independent system prompt, the Universal Ontology Generator (UOG), that asks the model to build a GOLD/OntoLing-aligned JSON ontology for any target language. The ontology is meant as the blueprint for NLP tools: rule-based FSTs, neural lemmatizers, morphological analyzers and dependency parsers. Every linguistic rule in it must come with a `rule_description`, an `example` and a `computational_mapping` that says how an algorithm handles the feature.

Put the prompt into the system prompt (or the first message) of a new chat, then send the name of the target language. The prompt adapts the output to the language's typology: features the language lacks are set to `null` / `not_applicable` with a `typological_note`, isolating languages shift the weight to syntax and the exception lexicon, polysynthetic languages to verbal morphology, fusional languages to stem alternations and paradigm tables.

Author: Inna Skrynnikova ([@skrynin25-png](https://github.com/skrynin25-png)), generalized from her Hungarian ontology prompts. The original is the Word document "Ontology prompts.docx" (October 2026).
