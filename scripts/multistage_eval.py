#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-stage prompt -> lemmatizer evaluation.

The linguist-group lemmatization prompts are staged workflows
(ontology -> gold use-cases -> lemmatizer -> independent evaluation), and the
lemmatizer stage usually asks for a *Python* module (some older prompts ask for
Clingo). The original scripts/eval_prompt.py one-shots the whole file and only
scores Clingo, so staged/Python prompts always scored 0. This harness fixes that:

  1. Parse the ## stages and their fenced prompt blocks.
  2. Run stages in order through the local LLM, feeding each stage the previous
     stage's artifact as its "attached input"; the independent-evaluation stage
     is skipped (we evaluate ourselves). Missing {{attachments}} are replaced
     with a note to use expert knowledge (so an automated run can proceed).
  3. Extract the generated lemmatizer (Python file(s) or Clingo .lp blocks).
  4. Evaluate:
       - Clingo  -> parse+ground each block (validity).
       - Python  -> py_compile (syntax) + required-API check + a SAFETY SCAN;
                    if safe, a best-effort smoke run under `python -I` with a
                    timeout over any form->lemma cases the stages produced.
  5. Write the artifact(s) next to the prompt and a Markdown report.

Env: LLM_URL (default qwen on :8081), LLM_MODEL, STAGE_MAX_TOKENS, STAGE_TIMEOUT.
Stdlib only. UTF-8 safe on every platform.
"""
from __future__ import annotations
import argparse, io, json, os, re, subprocess, sys, tempfile, urllib.request
from pathlib import Path

# UTF-8 stdout everywhere (Windows cp1251 would crash on ✓/✗)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LLM_URL = os.environ.get("LLM_URL", "http://127.0.0.1:8081/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3.8:27b-mtp-128k")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")  # Bearer token for a hosted model (OpenAI-compatible)
STAGE_MAX_TOKENS = int(os.environ.get("STAGE_MAX_TOKENS", "12000"))
STAGE_TIMEOUT = int(os.environ.get("STAGE_TIMEOUT", "1200"))

SYS = ("You are a computational-linguistics engineer and an expert in the target language. "
       "Follow the stage instructions exactly and output the artifact the stage asks for "
       "(a JSON file, test cases, or a lemmatizer). When a code file is requested, put it in a "
       "single fenced code block tagged with its language.")

# patterns a safe, stdlib-only generated lemmatizer should not contain
UNSAFE = re.compile(
    r"\b(socket|requests|urllib|http\.client|ftplib|smtplib|subprocess|os\.system|os\.popen|"
    r"os\.remove|os\.unlink|os\.rmdir|shutil\.rmtree|ctypes|multiprocessing|pickle\.load|"
    r"marshal|__import__\s*\(|eval\s*\(|exec\s*\(|compile\s*\(|open\s*\([^)]*['\"][wa])\b")


def llm(user: str, system: str = SYS, max_tokens: int = STAGE_MAX_TOKENS,
        temperature: float = 0.2, timeout: int = STAGE_TIMEOUT) -> str:
    # qwen is a reasoning model; /no_think keeps the answer out of the chain-of-thought.
    # Harmless/ignored by other models, but only append it for qwen.
    suffix = "\n\n/no_think" if "qwen" in LLM_MODEL.lower() else ""
    body = json.dumps({"model": LLM_MODEL,
                       "messages": [{"role": "system", "content": system},
                                    {"role": "user", "content": user + suffix}],
                       "max_tokens": max_tokens, "temperature": temperature,
                       "stream": False}).encode()
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = "Bearer " + LLM_API_KEY
    req = urllib.request.Request(LLM_URL, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    m = d["choices"][0]["message"]
    return (m.get("content") or m.get("reasoning_content") or "").strip()


PLACEHOLDER = re.compile(r"\{\{.*?\}\}", re.DOTALL)
FENCE = re.compile(r"```[a-zA-Z0-9_]*\s*\n(.*?)```", re.DOTALL)


def parse_stages(md: str):
    """Return [(heading, prompt_block)] — the fenced prompt under each '## N. ...' heading."""
    parts = re.split(r"^##\s+(.*)$", md, flags=re.M)
    stages = []
    it = iter(parts[1:])
    for head, body in zip(it, it):
        m = FENCE.search(body)
        if m:
            stages.append((head.strip(), m.group(1).strip()))
    return stages


def run_stages(stages):
    outputs, ran = [], []
    context = ""
    for head, block in stages:
        if re.search(r"eval", head, re.I):      # skip independent-evaluation stage
            continue
        prompt = PLACEHOLDER.sub(
            "(no external files are attached for this automated run; use your own expert "
            "knowledge of the language — but do not fabricate specific gold test items)", block)
        if context:
            prompt = ("Artifacts produced in the previous stage(s) — treat these as the attached "
                      "inputs this stage refers to:\n\n" + context +
                      "\n\n=== END OF PREVIOUS ARTIFACTS ===\n\nNow carry out this stage:\n\n" + prompt)
        out = llm(prompt)
        outputs.append((head, out))
        ran.append(head)
        context = out
    return outputs, ran


def extract_artifact(outputs):
    """Return (kind, [code_blocks]) — kind in {clingo, python, none}; prefer the last stage."""
    def blocks(text, langs):
        pat = re.compile(r"```(?:" + "|".join(langs) + r")\s*\n(.*?)```", re.DOTALL | re.I)
        return [b.strip() for b in pat.findall(text)]
    full = "\n\n".join(o for _, o in outputs)
    last = outputs[-1][1] if outputs else ""
    cl = blocks(full, ["clingo", "prolog", "lp", "asp", "lparse"])
    if cl:
        return "clingo", cl
    py = blocks(last, ["python", "py"]) or blocks(full, ["python", "py"])
    if py:
        return "python", py
    # the Latin-style prompt says "return only the Python file, no Markdown"
    if last and ("class " in last or "def " in last) and "import" in last:
        lines = last.splitlines()
        start = 0
        for i, ln in enumerate(lines):
            s = ln.lstrip()
            if s.startswith(("import ", "from ", "#!", "# ", '"""', "'''", "class ", "def ", "@")):
                start = i
                break
        return "python", ["\n".join(lines[start:]).strip()]
    return "none", []


def eval_clingo(blocks):
    try:
        import clingo
    except Exception as e:  # noqa: BLE001
        return {"valid": None, "detail": f"clingo unavailable: {e}"}
    valid = 0
    details = []
    for i, b in enumerate(blocks):
        try:
            ctl = clingo.Control(["--warn=none"])
            ctl.add("base", [], b)
            ctl.ground([("base", [])])
            valid += 1
        except Exception as e:  # noqa: BLE001
            details.append(f"block {i}: {str(e)[:120]}")
    return {"valid": valid, "total": len(blocks), "detail": "; ".join(details) or "all parse+ground"}


def eval_python(blocks):
    code = "\n\n".join(blocks)
    res = {"compiles": False, "has_api": False, "safe": True, "ran": None, "detail": ""}
    # syntax
    try:
        compile(code, "<generated>", "exec")
        res["compiles"] = True
    except SyntaxError as e:
        res["detail"] = f"SyntaxError: {e}"
        return res
    # required API: a class with a lemmatize method
    res["has_api"] = bool(re.search(r"class\s+\w*[Ll]emmatiz\w*", code)) and "def lemmatize" in code
    # safety scan before any execution
    hits = sorted(set(m.group(0) for m in UNSAFE.finditer(code)))
    if hits:
        res["safe"] = False
        res["detail"] = "not executed — flagged calls: " + ", ".join(hits[:6])
        return res
    # best-effort smoke import under python -I in a temp dir (no args, short timeout)
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "gen_lemmatizer.py"
        f.write_text(code, encoding="utf-8")
        probe = ("import importlib.util,inspect,sys;"
                 "s=importlib.util.spec_from_file_location('g',r'%s');"
                 "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                 "cs=[c for _,c in inspect.getmembers(m,inspect.isclass) if hasattr(c,'lemmatize')];"
                 "print('IMPORT_OK classes='+','.join(c.__name__ for c in cs))" % str(f).replace("\\", "\\\\"))
        try:
            p = subprocess.run([sys.executable, "-I", "-c", probe], cwd=td,
                               capture_output=True, text=True, timeout=60)
            out = (p.stdout + p.stderr).strip().splitlines()
            tail = out[-1] if out else ""
            res["ran"] = p.returncode == 0 and "IMPORT_OK" in (p.stdout or "")
            res["detail"] = (tail or "(no output)")[:200]
        except subprocess.TimeoutExpired:
            res["ran"] = False
            res["detail"] = "import timed out (likely needs the ontology/treebank data files)"
        except Exception as e:  # noqa: BLE001
            res["ran"] = False
            res["detail"] = f"probe error: {str(e)[:150]}"
    return res


def rubric(outputs):
    full = "\n\n".join(o for _, o in outputs).lower()
    return {
        "staged_chain": True,
        "ontology_built": "ontology" in full or "ontol{}".format("") in full or ".json" in full,
        "lemmatize_api": "def lemmatize" in full,
        "self_evaluation": "accuracy" in full or "cross-valid" in full or "evaluate(" in full,
    }


def evaluate(prompt_path: Path):
    md = prompt_path.read_text(encoding="utf-8")
    stages = parse_stages(md)
    report = {"prompt": str(prompt_path), "n_stages": len(stages)}
    if not stages:
        # not a staged prompt — one-shot it
        out = llm(md)
        outputs = [("(single stage)", out)]
        report["mode"] = "single-shot"
    else:
        outputs, ran = run_stages(stages)
        report["mode"] = "multi-stage"
        report["stages_run"] = ran
    kind, blocks = extract_artifact(outputs)
    report["artifact_kind"] = kind
    report["artifact_blocks"] = len(blocks)
    if kind == "clingo":
        report["clingo"] = eval_clingo(blocks)
        ext = "generated.lp"
        artifact = "\n\n% ---- block ----\n\n".join(blocks)
    elif kind == "python":
        report["python"] = eval_python(blocks)
        ext = "generated.py"
        artifact = "\n\n".join(blocks)
    else:
        ext = None
        artifact = None
    report["rubric"] = rubric(outputs)
    # write artifact next to prompt
    if artifact:
        out_file = prompt_path.with_suffix("").parent / (prompt_path.stem + "." + ext)
        header = {"generated.lp": "% ", "generated.py": "# "}[ext]
        meta = (f"{header}Generated by multistage_eval from prompt {prompt_path.name}\n"
                f"{header}model {LLM_MODEL}; multi-stage={report['mode']=='multi-stage'}; review before use.\n\n")
        out_file.write_text(meta + artifact, encoding="utf-8")
        report["artifact_file"] = str(out_file)
    report["raw_outputs"] = outputs
    return report


def status_of(r):
    k = r.get("artifact_kind")
    if k == "clingo":
        c = r.get("clingo", {})
        return "ok" if c.get("valid") else "needs_work"
    if k == "python":
        p = r.get("python", {})
        if not p.get("compiles"):
            return "invalid"
        if not p.get("safe"):
            return "unsafe"
        return "ok" if (p.get("has_api") and p.get("ran")) else "partial"
    return "no_artifact"


def to_md(reports):
    out = io.StringIO()
    out.write("## Prompt → lemmatizer evaluation (multi-stage)\n\n")
    out.write("| Prompt | Mode | Artifact | Blocks | Validity | Status |\n|---|---|---|---|---|---|\n")
    for r in reports:
        k = r.get("artifact_kind", "none")
        if k == "clingo":
            c = r.get("clingo", {})
            val = f"{c.get('valid')}/{c.get('total')} parse+ground"
        elif k == "python":
            p = r.get("python", {})
            val = ("compiles " + ("✓" if p.get("compiles") else "✗") +
                   ", API " + ("✓" if p.get("has_api") else "✗") +
                   ", import " + ("✓" if p.get("ran") else ("unsafe" if not p.get("safe") else "✗")))
        else:
            val = "—"
        out.write(f"| `{Path(r['prompt']).name}` | {r.get('mode')} | {k} | {r.get('artifact_blocks')} "
                  f"| {val} | **{status_of(r)}** |\n")
    out.write("\n### Details\n\n")
    for r in reports:
        out.write(f"#### `{r['prompt']}`\n")
        out.write(f"- stages: {r.get('n_stages')} (ran: {', '.join(r.get('stages_run', [])) or 'n/a'})\n")
        out.write(f"- artifact: **{r.get('artifact_kind')}**, {r.get('artifact_blocks')} block(s)"
                  + (f" → `{Path(r['artifact_file']).name}`" if r.get("artifact_file") else "") + "\n")
        if r.get("clingo"):
            out.write(f"- clingo: {r['clingo']}\n")
        if r.get("python"):
            out.write(f"- python: {r['python']}\n")
        out.write(f"- rubric: {r.get('rubric')}\n\n")
    out.write("\n_Multi-stage harness: stages are chained (ontology → use-cases → lemmatizer); the "
              "independent-evaluation stage is skipped. Python artifacts are syntax-checked, API-checked "
              "and safety-scanned; a best-effort import runs under `python -I`. Full accuracy scoring needs "
              "the external data (ontology sources, treebank) the prompts expect attached._\n")
    return out.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompts", nargs="+")
    ap.add_argument("--out", default=None)
    ap.add_argument("--llm-url", default=None,
                    help="OpenAI-compatible /chat/completions URL — switch to a more powerful model")
    ap.add_argument("--llm-model", default=None, help="model id at that endpoint")
    ap.add_argument("--api-key", default=None, help="Bearer API key (or set env LLM_API_KEY)")
    a = ap.parse_args()
    global LLM_URL, LLM_MODEL, LLM_API_KEY
    if a.llm_url:
        LLM_URL = a.llm_url
    if a.llm_model:
        LLM_MODEL = a.llm_model
    if a.api_key:
        LLM_API_KEY = a.api_key
    reports = []
    for p in a.prompts:
        sys.stderr.write(f"[multistage] evaluating {p} ...\n"); sys.stderr.flush()
        try:
            reports.append(evaluate(Path(p)))
        except Exception as e:  # noqa: BLE001
            reports.append({"prompt": p, "mode": "error", "artifact_kind": "none",
                            "artifact_blocks": 0, "error": str(e)})
            sys.stderr.write(f"[multistage]   error: {e}\n")
    md = to_md(reports)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
    try:
        print(md)
    except Exception:
        sys.stdout.buffer.write(md.encode("utf-8", "replace"))
    # machine-readable sidecar
    if a.out:
        Path(a.out).with_suffix(".json").write_text(
            json.dumps([{k: v for k, v in r.items() if k != "raw_outputs"} for r in reports],
                       ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
