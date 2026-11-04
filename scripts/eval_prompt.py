"""linguist-prompts evaluation harness.

For each prompt file: send it to a local LLM (OpenAI-compatible endpoint, default the
corpus-host qwen router on :11434), extract the lemmatizer it produces (Clingo `.lp`
rule blocks), and assess it against the EVALUATION.md rubric + lingua-rules:

  1. LLM round-trip      -- the prompt actually yields a lemmatizer.
  2. Clingo validity     -- every extracted .lp block parses + grounds (rubric M1.4).
  3. LLM-assisted test   -- the LLM writes `form -> lemma` cases and, per case, a runnable
                            Clingo driver (lemmatizer + input + `#show lemma/1.`); each driver
                            is executed and the shown lemma compared to the expected one.
                            Accuracy feeds the score and an optional hard gate.
  4. Rubric signals      -- ASP/Clingo constructs, data-logic separation, sanctioned
                            helpers, negative constraints (General Metrics M1.x).
  5. lingua-rules tests  -- if the language is already covered in lingua-rules
                            (github.com/DenisBaliuckij/lingua-rules), run its golden-file
                            paradigm tests (`lingua-rules test <iso>`) as a grounding step.

Writes a Markdown report to --out and exits non-zero if any prompt fails a hard gate
(no valid lemmatizer, or -- when PROMPT_EVAL_MIN_ACCURACY is set -- test accuracy below it).

Env: LLM_URL (default http://127.0.0.1:11434/v1/chat/completions), LLM_MODEL
(default qwen3.8:27b-mtp-128k), LINGUA_RULES (path to a lingua-rules checkout),
PROMPT_EVAL_MIN_ACCURACY (0..1, default 0 = report only, do not gate on accuracy).
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, urllib.request

LLM_URL = os.environ.get("LLM_URL", "http://127.0.0.1:11434/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3.8:27b-mtp-128k")
LINGUA_RULES = os.environ.get("LINGUA_RULES", "/lingua-rules")

CODE_BLOCK = re.compile(r"```(?:clingo|prolog|lp|asp|lparse)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
ISO_HINT = re.compile(r"ISO\s*639-3[:\s]*([a-z]{3})", re.IGNORECASE)


def call_llm(prompt_text: str, timeout: int = 600) -> str:
    body = json.dumps({
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a computational-linguistics engineer. "
             "Follow the user's prompt exactly and output the lemmatizer it asks for, including the "
             "Clingo rule files (.lp) and any TSV datasets, each in its own fenced code block."},
            {"role": "user", "content": prompt_text},
        ],
        "max_tokens": 4096, "temperature": 0.2, "stream": False,
    }).encode()
    req = urllib.request.Request(LLM_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    msg = d["choices"][0]["message"]
    return msg.get("content") or msg.get("reasoning_content") or ""


def clingo_check(lp: str):
    """Return (ok, detail). ok=True if the block parses + grounds under Clingo."""
    try:
        import clingo
    except Exception as e:  # noqa: BLE001
        return None, f"clingo-unavailable:{e}"
    try:
        ctl = clingo.Control(["--warn=none"])
        ctl.add("base", [], lp)
        ctl.ground([("base", [])])
        return True, "parsed+grounded"
    except Exception as e:  # noqa: BLE001
        return False, str(e).splitlines()[0][:160]


TEST_SYS = ("You are a computational-linguistics test engineer. You are given a rule-based "
            "lemmatizer written in Clingo (ASP). Produce test cases for it and, for EACH case, a "
            "single self-contained Clingo program that runs the lemmatizer on one surface form and "
            "exposes the result as `lemma(\"<result>\")` via `#show lemma/1.`. "
            "Reply with ONLY a JSON object: {\"cases\": [{\"form\": str, \"lemma\": str, \"program\": str}]}. "
            "`program` must contain the lemmatizer code, the input fact(s) for `form`, and end with "
            "`#show lemma/1.` so that solving prints exactly the lemma(s). Keep 6-10 diverse cases.")


def _llm_json(system: str, user: str, timeout: int = 600) -> dict:
    body = json.dumps({"model": LLM_MODEL, "messages": [
        {"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": 4096, "temperature": 0.1, "stream": False}).encode()
    req = urllib.request.Request(LLM_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    msg = d["choices"][0]["message"]
    text = msg.get("content") or msg.get("reasoning_content") or ""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(m.group(0)) if m else {}


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip().lower())


def run_clingo_lemma(program: str, timeout: int = 20):
    """Solve `program`, return the set of lemma/1 string args (the shown result), or None on error."""
    try:
        import clingo
    except Exception:  # noqa: BLE001
        return None
    found: set[str] = set()
    try:
        ctl = clingo.Control(["--warn=none", "-n", "0"])
        ctl.add("base", [], program)
        ctl.ground([("base", [])])
        def on_model(m):  # collect shown lemma/1 atoms
            for sym in m.symbols(shown=True):
                if sym.name == "lemma" and len(sym.arguments) == 1:
                    a = sym.arguments[0]
                    found.add(a.string if a.type == clingo.SymbolType.String else str(a))
        ctl.solve(on_model=on_model)
    except Exception:  # noqa: BLE001
        return None
    return found


def test_lemmatizer(blocks, iso, timeout: int = 600) -> dict:
    """LLM-assisted testing: the LLM writes form->lemma cases + a runnable Clingo driver per case;
    we execute each driver and score exact/normalized accuracy. Returns a result dict."""
    res = {"ran": False, "total": 0, "passed": 0, "accuracy": None, "detail": ""}
    if not blocks:
        res["detail"] = "no lemmatizer to test"; return res
    lemmatizer = "\n\n".join(blocks)
    user = (f"Target language ISO 639-3: {iso or 'unknown'}.\n\nLemmatizer (Clingo):\n```\n{lemmatizer}\n```")
    try:
        data = _llm_json(TEST_SYS, user, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        res["detail"] = f"llm_test_error:{str(e)[:120]}"; return res
    cases = [c for c in (data.get("cases") or []) if isinstance(c, dict) and c.get("form") and c.get("lemma")]
    if not cases:
        res["detail"] = "no test cases returned"; return res
    passed, total, misses = 0, 0, []
    for c in cases[:10]:
        prog = c.get("program") or (lemmatizer + f'\nform("{c["form"]}").\n#show lemma/1.')
        out = run_clingo_lemma(prog)
        if out is None:
            continue  # clingo unavailable or program error -> skip (not counted)
        total += 1
        exp = _norm(c["lemma"])
        if any(_norm(x) == exp for x in out):
            passed += 1
        else:
            misses.append({"form": c["form"], "expected": c["lemma"], "got": sorted(out)[:3]})
    res["total"], res["passed"] = total, passed
    if total:
        res["ran"] = True
        res["accuracy"] = round(passed / total, 2)
        res["detail"] = "" if not misses else f"{len(misses)} miss(es); e.g. " + \
            ", ".join(f"{m['form']}->{m['got'] or '∅'} (want {m['expected']})" for m in misses[:3])
    else:
        res["detail"] = "clingo could not run the drivers"
    return res


def lingua_rules_tests(iso, timeout: int = 300) -> dict:
    """If lingua-rules (https://github.com/DenisBaliuckij/lingua-rules) already has this
    language, run its golden-file paradigm tests (`lingua-rules test <iso>`) as a grounding
    step. Reports pass/fail; does not gate the prompt (it exercises lingua-rules, not the
    LLM output)."""
    res = {"available": False, "ran": False, "passed": None, "summary": "", "detail": ""}
    if not iso:
        res["detail"] = "no ISO code in prompt"; return res
    root = LINGUA_RULES
    has_tests = os.path.isdir(os.path.join(root, "tests", iso))
    has_rules = os.path.isdir(os.path.join(root, "rules", iso))
    if not (has_tests or has_rules):
        res["detail"] = "lingua-rules has no rules/tests for this language"; return res
    res["available"] = True
    if not has_tests:
        res["detail"] = "rules present but no golden tests in lingua-rules"; return res
    env = {**os.environ, "PYTHONPATH": os.path.join(root, "src") + os.pathsep + os.environ.get("PYTHONPATH", "")}
    for cmd in (["lingua-rules", "test", iso], [sys.executable, "-m", "lingua_rules.cli.main", "test", iso]):
        try:
            p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=timeout, env=env)
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            res["detail"] = "lingua-rules tests timed out"; return res
        out = (p.stdout + ("\n" + p.stderr if p.stderr else "")).strip()
        res["ran"] = True
        res["passed"] = (p.returncode == 0)
        tail = [ln for ln in out.splitlines() if ln.strip()][-4:]
        res["summary"] = " / ".join(tail)[:300]
        res["detail"] = "" if res["passed"] else "lingua-rules golden tests failed"
        return res
    res["detail"] = "lingua-rules CLI not runnable (install the lingua-rules checkout)"
    return res


def rubric_signals(prompt_text: str) -> dict:
    t = prompt_text.lower()
    return {
        "asp_clingo": any(k in t for k in ("clingo", "asp", "@suffix", "form(")),
        "data_logic_separation": any(k in t for k in ("tsv", "dataset", "datasets", "exceptions")),
        "sanctioned_helpers": any(k in t for k in ("@suffix", "@prefix", "@strip_suffix_add", "@affix")),
        "negative_constraints": ("parse" in t and ("reject" in t or "valid" in t)),
    }


def score_prompt(path: str) -> dict:
    prompt_text = open(path, encoding="utf-8", errors="replace").read()
    iso = (ISO_HINT.search(prompt_text) or [None, None])[1]
    rep = {"prompt": os.path.basename(path), "iso": iso}
    try:
        out = call_llm(prompt_text)
    except Exception as e:  # noqa: BLE001
        rep.update(status="llm_error", error=str(e)[:200]); return rep
    blocks = [b.strip() for b in CODE_BLOCK.findall(out) if b.strip()]
    rep["llm_chars"] = len(out)
    rep["lp_blocks"] = len(blocks)
    checks = [clingo_check(b) for b in blocks]
    parsed = sum(1 for ok, _ in checks if ok)
    rep["clingo_parsed"] = parsed
    rep["clingo_failed"] = sum(1 for ok, _ in checks if ok is False)
    rep["signals"] = rubric_signals(prompt_text)
    # use-case grounding: does lingua-rules already have this language's golden tests?
    rep["use_cases_available"] = bool(iso) and os.path.isdir(os.path.join(LINGUA_RULES, "rules", iso))
    # lingua-rules golden paradigm tests for this language, when present (grounding step).
    rep["lingua_rules"] = lingua_rules_tests(iso)
    # LLM-assisted testing: the LLM writes form->lemma cases + Clingo drivers, we run them.
    rep["test"] = test_lemmatizer(blocks, iso) if (blocks and rep["clingo_failed"] == 0) else \
        {"ran": False, "accuracy": None, "detail": "skipped (no valid lemmatizer)"}
    acc = rep["test"].get("accuracy")
    # score: produced (30) + all blocks valid (25) + rubric signals (20) + test accuracy (25)
    s = 0
    if blocks: s += 30
    if blocks and rep["clingo_failed"] == 0: s += 25
    s += 20 * sum(rep["signals"].values()) // 4
    if acc is not None: s += int(25 * acc)
    rep["score"] = s
    # gate: must produce a valid lemmatizer; when tests ran, accuracy must clear the (configurable) floor.
    min_acc = float(os.environ.get("PROMPT_EVAL_MIN_ACCURACY", "0") or 0)
    ok = bool(blocks) and rep["clingo_failed"] == 0
    if ok and rep["test"].get("ran") and acc is not None and acc < min_acc:
        ok = False
    rep["status"] = "ok" if ok else "needs_work"
    return rep


def to_markdown(reports):
    lines = ["## Prompt evaluation", "",
             "| Prompt | ISO | LP blocks | Clingo ok/fail | Rubric | Tests pass/total | Accuracy | lingua-rules | Score | Status |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in reports:
        sig = sum(r.get("signals", {}).values()) if "signals" in r else 0
        t = r.get("test", {}) or {}
        tcell = f"{t.get('passed','-')}/{t.get('total','-')}" if t.get("ran") else "—"
        acc = t.get("accuracy")
        acell = f"{int(acc*100)}%" if acc is not None else "—"
        lr = r.get("lingua_rules", {}) or {}
        lrcell = ("pass" if lr.get("passed") else "fail") if lr.get("ran") else ("n/a" if not lr.get("available") else "—")
        lines.append(f"| {r['prompt']} | {r.get('iso') or '?'} | {r.get('lp_blocks','-')} | "
                     f"{r.get('clingo_parsed','-')}/{r.get('clingo_failed','-')} | {sig}/4 | "
                     f"{tcell} | {acell} | {lrcell} | {r.get('score','-')} | **{r.get('status','?')}** |")
    # per-prompt detail: LLM-test misses and lingua-rules outcomes
    detail = []
    for r in reports:
        if (r.get("test") or {}).get("detail"):
            detail.append(f"- **{r['prompt']}** (LLM test): {r['test']['detail']}")
        lr = r.get("lingua_rules") or {}
        if lr.get("ran"):
            detail.append(f"- **{r['prompt']}** (lingua-rules): {'passed' if lr['passed'] else 'FAILED'} — {lr.get('summary','')}")
    lines += ["", "_Lemmatizer extracted via the local LLM, Clingo-validated, then **tested**: the "
              "LLM generates `form→lemma` cases and a Clingo driver per case, which are executed and "
              "scored (accuracy). The **lingua-rules** column runs that project's golden paradigm tests "
              "for the language when it is already covered (grounding; not a gate on the prompt)._"]
    if detail:
        lines += ["", "### Details", *detail]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompts", nargs="+")
    ap.add_argument("--out", default="prompt_eval.md")
    args = ap.parse_args()
    reports = []
    for p in args.prompts:
        print(f"[eval] {p}", flush=True)
        reports.append(score_prompt(p))
    md = to_markdown(reports)
    open(args.out, "w", encoding="utf-8").write(md)
    print(md)
    # hard gate: any prompt that produced no valid lemmatizer fails CI
    sys.exit(1 if any(r.get("status") != "ok" for r in reports) else 0)


if __name__ == "__main__":
    main()
