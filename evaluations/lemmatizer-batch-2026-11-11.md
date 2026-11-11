> **Honest batch, 2026-11-11.** Generated with the local qwen3.8:27b (CPU) via scripts/multistage_eval.py. All outputs are **invalid** — the generator model is the limiter, not the prompts. Re-run with a stronger model: `--llm-url … --llm-model … --api-key …`. Generated .py files are the raw model output, kept for review.

## Prompt → lemmatizer evaluation (multi-stage)

| Prompt | Mode | Artifact | Blocks | Validity | Status |
|---|---|---|---|---|---|
| `prompts.md` | multi-stage | python | 1 | compiles ✗, API ✗, import ✗ | **invalid** |
| `prompts.md` | multi-stage | python | 1 | compiles ✗, API ✗, import ✗ | **invalid** |
| `prompts.md` | multi-stage | none | 0 | — | **no_artifact** |
| `building_lemmatizer.md` | single-shot | python | 1 | compiles ✗, API ✗, import ✗ | **invalid** |
| `building_lemmatizer_ckt.md` | single-shot | python | 1 | compiles ✗, API ✗, import ✗ | **invalid** |

### Details

#### `languages\latin\lemmatization\prompts.md`
- stages: 4 (ran: 1. Building the Latin morphological ontology, 2. Preparing gold use-cases, 3. Building a rule-based lemmatizer)
- artifact: **python**, 1 block(s) → `prompts.generated.py`
- python: {'compiles': False, 'has_api': False, 'safe': True, 'ran': None, 'detail': 'SyntaxError: unterminated string literal (detected at line 23) (<generated>, line 23)'}
- rubric: {'staged_chain': True, 'ontology_built': True, 'lemmatize_api': False, 'self_evaluation': True}

#### `languages\persian\lemmatization\prompts.md`
- stages: 4 (ran: 1. Building the Persian morphological ontology, 2. Preparing gold use-cases, 3. Building a rule-based lemmatizer)
- artifact: **python**, 1 block(s) → `prompts.generated.py`
- python: {'compiles': False, 'has_api': False, 'safe': True, 'ran': None, 'detail': 'SyntaxError: unterminated string literal (detected at line 7) (<generated>, line 7)'}
- rubric: {'staged_chain': True, 'ontology_built': True, 'lemmatize_api': True, 'self_evaluation': True}

#### `languages\spanish\lemmatization\prompts.md`
- stages: 4 (ran: 1. Построение испанской морфологической онтологии, 2. Подготовка gold use-cases, 3. Создание rule-based лемматизатора, 4. Независимая оценка лемматизатора)
- artifact: **none**, 0 block(s)
- rubric: {'staged_chain': True, 'ontology_built': True, 'lemmatize_api': False, 'self_evaluation': True}

#### `languages\chinese\building_lemmatizer.md`
- stages: 0 (ran: n/a)
- artifact: **python**, 1 block(s) → `building_lemmatizer.generated.py`
- python: {'compiles': False, 'has_api': False, 'safe': True, 'ran': None, 'detail': 'SyntaxError: unterminated string literal (detected at line 28) (<generated>, line 28)'}
- rubric: {'staged_chain': True, 'ontology_built': True, 'lemmatize_api': True, 'self_evaluation': True}

#### `languages\chukchi\building_lemmatizer_ckt.md`
- stages: 0 (ran: n/a)
- artifact: **python**, 1 block(s) → `building_lemmatizer_ckt.generated.py`
- python: {'compiles': False, 'has_api': False, 'safe': True, 'ran': None, 'detail': 'SyntaxError: invalid decimal literal (<generated>, line 30)'}
- rubric: {'staged_chain': True, 'ontology_built': True, 'lemmatize_api': True, 'self_evaluation': True}


_Multi-stage harness: stages are chained (ontology → use-cases → lemmatizer); the independent-evaluation stage is skipped. Python artifacts are syntax-checked, API-checked and safety-scanned; a best-effort import runs under `python -I`. Full accuracy scoring needs the external data (ontology sources, treebank) the prompts expect attached._
