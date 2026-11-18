Prompt 5: Iterative Refinement and Context Preparation for Prompt 3 (Russian)
Role
You are a diagnostic engineer and computational linguist. Your job is to analyze the error report from Prompt 4, formulate hypotheses, fix general rules (NOT individual test words), and prepare the context header for the next build.
Inputs

    The russian-holdout-report.md and russian-holdout-errors.csv from Prompt 4.
    OntoRussian.json (The ontology)
    *.lp (Generation rules)
    russian_lemmatizer.py (Analysis code)
    russian-computational-model.json (The intermediate machine-readable model, if there is)

Task: The Iteration Loop (Max 3 iterations)
Step 1: Analyze and Classify
Read the error report. Group errors into two main buckets:

    Systemic Errors (Rule/Ontology bugs): Patterns where a general rule fails (e.g., "all reflexive verbs lose their suffix", "epenthetic vowel is missing", "wrong ranking for homographs").
    Unique/Lexicon Errors (OOV): Words simply missing from the dictionary (e.g., rare proper names, neologisms).

Step 2: Formulate Hypotheses & Fix

    For Systemic Errors: You MUST fix the root cause.
        If the rule is wrong, update OntoRussian.json or russian-computational-model.json.
        If the Python ranking logic is flawed, describe the required change in your report, but DO NOT rewrite russian_lemmatizer.py yourself. Instruct the user to apply it via the Context Header for Prompt 3.
        CRITICAL: Do NOT hardcode specific holdout words into the code (e.g., if form == "трактором": return "трактор"). Fix the general rule that covers them.
    For Unique/Lexicon Errors:
        If the word is a valid lexical item, add it to the irregular lists in the ontology/computational model.
        If it's a rare/dialectal form not covered by the grammar, add it to meta.notes.gaps and ignore it for this iteration.

Step 3: Generate Context Header for Prompt 3
After applying fixes, you MUST generate a special Markdown block that the user will copy and paste at the very beginning of Prompt 3 before the next run. This block strictly instructs Prompt 3 to delete old files and rewrite everything from scratch based on the updated ontology.
Format of the generated block (copy and fill):
[Iteration N/3] Context and Full Rewrite Instructions:
The ontology (OntoRussian.json) and/or Python logic have been updated to fix systemic errors identified in the previous stage (Holdout accuracy: X.X% -> Y.Y%).
Fixed categories: [list them, e.g., fleeting vowels, reflexivity, participle suffixes].
CRITICAL INSTRUCTIONS FOR THE AGENT (PROMPT 3):

    DELETE the old files russian_lemmatizer.py and russian-computational-model.json from the working directory.
    DO NOT TRY to "patch" or update the old code.
    READ the updated OntoRussian.json from scratch and regenerate russian-computational-model.json.
    WRITE new rules to rules/ru-lemmatizer/, completely replacing the old ones.
    DO NOT OVERWRITE files in rules/ru/ (these are the original files from the lingua-rules repository).
    Generate the artifacts from scratch, relying ONLY on the current state of the ontology.

Stopping Criteria
Stop iterating if:

    You have completed 3 iterations.
    Holdout accuracy has not improved (plateau, delta < 0.5%).
    The Prompt 4 report contains only missing_lexicon (OOV) errors that cannot be fixed with general rules.

Required Outputs
1. Iteration Log: russian-iteration-log.md
For each iteration, record:

    Iteration number.
    Error classification: counts per category (from Prompt 4).
    Hypotheses: one per top category, with rationale.
    Changes made: list of files modified, with a brief description.
    CV results: mean accuracy, delta from previous iteration.
    Holdout results: accuracy, delta from previous iteration.
    Decision: accept / reject, with rationale.

2. Final Report: russian-final-report.md
Structure:

    Summary: one-paragraph overview of the final results.
    Final metrics: table with CV and holdout accuracy.
    Improvement trajectory: table showing the delta at each iteration.
    Ontology defects: list of gaps or errors in the ontology that were identified and fixed.
    Limitations: explicit list of what the lemmatizer still does not handle, with counts.
    Reproducibility: SHA-256 hashes of the final lemmatizer and rules.

3. Updated Artifacts

    OntoRussian.json (updated).
    russian-computational-model.json (updated).
    rules/ru-lemmatizer/*.lp (regenerated).
    The Context Header for Prompt 3 (see Step 3).

Anti-patterns (CRITICAL)

    Do NOT hardcode holdout words. This is overfitting and invalidates the evaluation.
    Do NOT modify the holdout set or the evaluation script.
    Do NOT run Prompt 4 more than once per iteration.
    Do NOT write "everything is fixed" without specific lists of modified rules and ontology nodes.


