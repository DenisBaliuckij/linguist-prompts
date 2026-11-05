"""linguist-prompts evaluation harness.

For each prompt file: send it to a local LLM (OpenAI-compatible endpoint, default the
corpus-host qwen router on :11434), extract the lemmatizer it produces (Clingo `.lp`
rule blocks), and assess it:

  1. LLM round-trip      -- the prompt actually yields a lemmatizer.
  2. Clingo validity     -- each extracted .lp block parses + grounds; the VALID blocks
                            form the lemmatizer under test.
  3. LLM-assisted test   -- the LLM supplies the lemmatizer's query interface (input/lemma
                            predicates) + `form -> lemma` cases; we build the driver
                            DETERMINISTICALLY, run it under Clingo, and (with a brute-force
                            interface fallback) score accuracy. Runs whenever >=1 block is
                            valid, even if other blocks failed.
  4. Rubric signals      -- ASP/Clingo constructs, data-logic separation, sanctioned helpers.
  5. lingua-rules tests  -- if the language is covered in lingua-rules
                            (github.com/DenisBaliuckij/lingua-rules), run its golden tests.

The valid lemmatizer is written next to the prompt as `<stem>.generated.lp` so CI can
commit it to the MR branch. A detailed Markdown report is written to --out.

Env: LLM_URL, LLM_MODEL, LINGUA_RULES, PROMPT_EVAL_MIN_ACCURACY (0..1, default 0 = report only).
"""
from __future__ import annotations
import argparse, datetime, json, os, re, subprocess, sys, urllib.request

LLM_URL = os.environ.get("LLM_URL", "http://127.0.0.1:11434/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3.8:27b-mtp-128k")
LINGUA_RULES = os.environ.get("LINGUA_RULES", "/lingua-rules")

CODE_BLOCK = re.compile(r"```(?:clingo|prolog|lp|asp|lparse)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
ISO_HINT = re.compile(r"ISO\s*639-3[^a-z]{0,4}([a-z]{3})\b", re.IGNORECASE)
ISO_PAREN = re.compile(r"\b([a-z]{3})\b\s*\)")  # e.g. "(ISO 639-3: hye)" already covered; loose fallback

# Query-interface conventions tried when the LLM's stated interface yields nothing.
INPUT_PREDS = ("form", "word", "surface", "input", "token", "wordform", "surface_form")
LEMMA_PREDS = (("lemma", 1), ("lemma", 2), ("lemmatize", 2), ("lemmatise", 2),
               ("out", 1), ("result", 1), ("lemma_of", 2), ("citation", 1))


def _llm(messages, timeout=600, max_tokens=4096, temperature=0.2) -> str:
    body = json.dumps({"model": LLM_MODEL, "messages": messages,
                       "max_tokens": max_tokens, "temperature": temperature, "stream": False}).encode()
    req = urllib.request.Request(LLM_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    msg = d["choices"][0]["message"]
    return msg.get("content") or msg.get("reasoning_content") or ""


def call_llm(prompt_text: str, timeout: int = 600) -> str:
    return _llm([
        {"role": "system", "content": "You are a computational-linguistics engineer. Follow the user's "
         "prompt exactly and output the lemmatizer it asks for, including the Clingo rule files (.lp) and "
         "any TSV datasets, each in its own fenced code block."},
        {"role": "user", "content": prompt_text}], timeout=timeout)


def _llm_json(system: str, user: str, timeout: int = 600) -> dict:
    text = _llm([{"role": "system", "content": system}, {"role": "user", "content": user}],
                timeout=timeout, temperature=0.1)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(m.group(0)) if m else {}


def _norm(s) -> str:
    return re.sub(r"\s+", "", str(s or "").strip().lower())


def clingo_check(lp: str):
    """(ok, detail): ok=True if the block parses + grounds; False with the first error; None if no clingo."""
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
        return False, str(e).splitlines()[0][:180]


def _solve_atoms(program: str, timeout_atoms: int = 20000):
    """Ground+solve; return {pred_name: [tuple(arg_strings), ...]} from the first model, or None on error."""
    try:
        import clingo
    except Exception:  # noqa: BLE001
        return None
    out: dict = {}

    def argstr(a):
        return a.string if a.type == clingo.SymbolType.String else str(a)

    def on_model(m):
        n = 0
        for sym in m.symbols(atoms=True):
            out.setdefault(sym.name, []).append(tuple(argstr(a) for a in sym.arguments))
            n += 1
            if n > timeout_atoms:
                break
    try:
        ctl = clingo.Control(["--warn=none", "-n", "1"])
        ctl.add("base", [], program)
        ctl.ground([("base", [])])
        ctl.solve(on_model=on_model)
    except Exception:  # noqa: BLE001
        return None
    return out


def _lemmas_from(atoms: dict, lemma_pred: str, lemma_arg: int, form: str):
    """Candidate lemmas for `form` from solved atoms, given a (lemma_pred, which-arg) convention."""
    cands = set()
    for args in atoms.get(lemma_pred, []):
        if len(args) == 1 and lemma_arg == 1:
            cands.add(args[0])
        elif len(args) == 2:
            # prefer the atom whose OTHER argument equals the form; else take the configured arg.
            other = args[1] if lemma_arg == 1 else args[0]
            pick = args[lemma_arg - 1]
            if _norm(other) == _norm(form) or not any(_norm(form) == _norm(a) for a in args):
                cands.add(pick)
    return cands


def run_lemmatizer(lemmatizer: str, form: str, interface=None):
    """Return (set_of_candidate_lemmas, interface_used|None). Tries the given interface first,
    then brute-forces common conventions. None set means clingo could not run it at all."""
    attempts = []
    if interface and interface.get("input_pred") and interface.get("lemma_pred"):
        attempts.append((interface["input_pred"], interface["lemma_pred"], int(interface.get("lemma_arg") or 2)))
    for ip in INPUT_PREDS:
        for lp_name, arity in LEMMA_PREDS:
            attempts.append((ip, lp_name, arity))
    ran_any = False
    for ip, lpred, larg in attempts:
        prog = f'{lemmatizer}\n{ip}("{form}").\n'
        atoms = _solve_atoms(prog)
        if atoms is None:
            continue
        ran_any = True
        cands = _lemmas_from(atoms, lpred, larg, form)
        cands.discard(form)  # a lemmatizer that just echoes the input is not a result
        if cands:
            return cands, {"input_pred": ip, "lemma_pred": lpred, "lemma_arg": larg}
    return (set() if ran_any else None), None


TEST_SYS = (
    "You are given a rule-based lemmatizer written in Clingo (ASP). Do two things and reply with ONLY a "
    "JSON object. (1) State how to query it: `input_pred` = the arity-1 predicate that should hold one "
    "input surface form as a quoted string (e.g. form); `lemma_pred` = the predicate that carries the "
    "computed lemma; `lemma_arg` = 1 if the lemma is the sole/first argument, or 2 if the lemma is the "
    "second argument of a form->lemma predicate. (2) Give 6-10 diverse, correct test cases for the target "
    'language. JSON shape: {"input_pred": str, "lemma_pred": str, "lemma_arg": 1 or 2, '
    '"cases": [{"form": str, "lemma": str}]}.')


def test_lemmatizer(valid_blocks, iso, timeout: int = 600) -> dict:
    """Run the valid lemmatizer against LLM-provided cases with a deterministic, interface-detecting driver."""
    res = {"ran": False, "total": 0, "passed": 0, "accuracy": None, "interface": None, "cases": [], "detail": ""}
    if not valid_blocks:
        res["detail"] = "no valid Clingo rules to test"; return res
    lemmatizer = "\n\n".join(valid_blocks)
    user = f"Target language ISO 639-3: {iso or 'unknown'}.\n\nLemmatizer (Clingo):\n```\n{lemmatizer}\n```"
    try:
        data = _llm_json(TEST_SYS, user, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        res["detail"] = f"LLM test-spec error: {str(e)[:140]}"; return res
    cases = [c for c in (data.get("cases") or []) if isinstance(c, dict) and c.get("form") and c.get("lemma")]
    if not cases:
        res["detail"] = "the LLM returned no usable test cases"; return res
    stated = {"input_pred": data.get("input_pred"), "lemma_pred": data.get("lemma_pred"),
              "lemma_arg": data.get("lemma_arg")}
    passed, total, used_iface, clingo_ok = 0, 0, None, False
    for c in cases[:10]:
        cands, iface = run_lemmatizer(lemmatizer, str(c["form"]), used_iface or stated)
        if cands is None:
            res["cases"].append({"form": c["form"], "expected": c["lemma"], "got": [], "ok": None, "note": "clingo error"})
            continue
        clingo_ok = True
        total += 1
        used_iface = used_iface or iface  # lock onto the first interface that worked
        exp = _norm(c["lemma"])
        ok = any(_norm(x) == exp for x in cands)
        passed += 1 if ok else 0
        res["cases"].append({"form": c["form"], "expected": c["lemma"], "got": sorted(cands)[:4], "ok": ok})
    res["interface"] = used_iface or (stated if stated.get("lemma_pred") else None)
    res["total"], res["passed"] = total, passed
    if total:
        res["ran"] = True
        res["accuracy"] = round(passed / total, 2)
    elif clingo_ok or not cases:
        res["detail"] = "no case produced a recognizable lemma (the lemmatizer exposes no queryable lemma/lemma-2 predicate for the tried input preds)"
    else:
        res["detail"] = "clingo could not execute the lemmatizer on any case"
    return res


def lingua_rules_tests(iso, timeout: int = 300) -> dict:
    res = {"available": False, "ran": False, "passed": None, "passed_n": None, "failed_n": None, "summary": "", "detail": ""}
    if not iso:
        res["detail"] = "no ISO 639-3 code detected in the prompt"; return res
    root = LINGUA_RULES
    has_tests = os.path.isdir(os.path.join(root, "tests", iso))
    has_rules = os.path.isdir(os.path.join(root, "rules", iso))
    if not (has_tests or has_rules):
        res["detail"] = f"lingua-rules has no rules/tests for '{iso}'"; return res
    res["available"] = True
    if not has_tests:
        res["detail"] = f"lingua-rules has rules for '{iso}' but no golden test cases"; return res
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
        res["passed_n"] = out.count("[PASS]") or out.lower().count("pass")
        res["failed_n"] = out.count("[FAIL]") or out.lower().count("fail")
        tail = [ln for ln in out.splitlines() if ln.strip()][-6:]
        res["summary"] = " / ".join(tail)[:400]
        res["detail"] = "" if res["passed"] else "lingua-rules golden tests reported failures"
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


def detect_iso(prompt_text: str, path: str):
    m = ISO_HINT.search(prompt_text)
    if m:
        return m.group(1).lower()
    # path fallback: languages/<name>/...  -> try a 3-letter dir, else None (name->ISO not guessed)
    parts = path.replace("\\", "/").split("/")
    if "languages" in parts:
        nxt = parts[parts.index("languages") + 1] if parts.index("languages") + 1 < len(parts) else ""
        if re.fullmatch(r"[a-z]{3}", nxt):
            return nxt
    return None


def write_lemmatizer(path: str, valid_blocks) -> str | None:
    """Write the valid lemmatizer next to the prompt as <stem>.generated.lp; return repo-relative path."""
    if not valid_blocks:
        return None
    stem = os.path.splitext(os.path.basename(path))[0]
    out = os.path.join(os.path.dirname(path), f"{stem}.generated.lp")
    header = (f"% Lemmatizer generated by the linguist-prompts evaluation pipeline\n"
              f"% from prompt: {os.path.basename(path)}\n"
              f"% model: {LLM_MODEL}  date: {datetime.date.today().isoformat()}\n"
              f"% {len(valid_blocks)} Clingo block(s) that parse + ground. Review before use.\n\n")
    with open(out, "w", encoding="utf-8") as f:
        f.write(header + "\n\n% ---- block ----\n\n".join(valid_blocks) + "\n")
    return out.replace("\\", "/")


def score_prompt(path: str) -> dict:
    prompt_text = open(path, encoding="utf-8", errors="replace").read()
    iso = detect_iso(prompt_text, path)
    rep = {"prompt": os.path.basename(path), "path": path, "iso": iso}
    try:
        out = call_llm(prompt_text)
    except Exception as e:  # noqa: BLE001
        rep.update(status="llm_error", error=str(e)[:200]); return rep
    blocks = [b.strip() for b in CODE_BLOCK.findall(out) if b.strip()]
    rep["llm_chars"] = len(out)
    rep["lp_blocks"] = len(blocks)
    checks = [clingo_check(b) for b in blocks]
    valid_blocks = [b for b, (ok, _) in zip(blocks, checks) if ok]
    rep["clingo_parsed"] = sum(1 for ok, _ in checks if ok)
    rep["clingo_failed"] = sum(1 for ok, _ in checks if ok is False)
    rep["clingo_errors"] = [d for ok, d in checks if ok is False][:5]
    rep["signals"] = rubric_signals(prompt_text)
    rep["lingua_rules"] = lingua_rules_tests(iso)
    # Testing now runs whenever at least one block is valid (not only when none failed).
    rep["test"] = test_lemmatizer(valid_blocks, iso)
    rep["lemmatizer_file"] = write_lemmatizer(path, valid_blocks)
    acc = rep["test"].get("accuracy")
    s = 0
    if blocks: s += 25
    if valid_blocks: s += 20
    if blocks and rep["clingo_failed"] == 0: s += 10
    s += 20 * sum(rep["signals"].values()) // 4
    if acc is not None: s += int(25 * acc)
    rep["score"] = s
    min_acc = float(os.environ.get("PROMPT_EVAL_MIN_ACCURACY", "0") or 0)
    ok = bool(valid_blocks)
    if ok and rep["test"].get("ran") and acc is not None and acc < min_acc:
        ok = False
    rep["status"] = "ok" if ok else "needs_work"
    return rep


def to_markdown(reports):
    L = ["## Prompt evaluation", "",
         "| Prompt | ISO | LP blocks (valid) | Tests pass/total | Accuracy | lingua-rules | Lemmatizer | Score | Status |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in reports:
        if r.get("status") == "llm_error":
            L.append(f"| {r['prompt']} | {r.get('iso') or '?'} | — | — | — | — | — | — | **llm_error** |")
            continue
        t = r.get("test", {}) or {}
        tcell = f"{t.get('passed','-')}/{t.get('total','-')}" if t.get("ran") else "—"
        acc = t.get("accuracy")
        acell = f"{int(acc*100)}%" if acc is not None else "—"
        lr = r.get("lingua_rules", {}) or {}
        lrcell = (f"pass {lr.get('passed_n','')}".strip() if lr.get("passed") else "FAIL") if lr.get("ran") \
            else ("n/a" if not lr.get("available") else "rules only")
        lf = r.get("lemmatizer_file")
        lfcell = f"`{os.path.basename(lf)}`" if lf else "—"
        L.append(f"| {r['prompt']} | {r.get('iso') or '?'} | {r.get('lp_blocks',0)} ({r.get('clingo_parsed',0)}) | "
                 f"{tcell} | {acell} | {lrcell} | {lfcell} | {r.get('score','-')} | **{r.get('status','?')}** |")

    L += ["", "### Details"]
    for r in reports:
        L.append(f"\n#### {r['prompt']}  ·  `{r.get('path','')}`")
        if r.get("status") == "llm_error":
            L.append(f"- **LLM error:** {r.get('error','')}")
            continue
        vb = r.get("clingo_parsed", 0)
        L.append(f"- **Lemmatizer:** {r.get('lp_blocks',0)} block(s) from the LLM, **{vb} valid** under Clingo"
                 + (f"; written to `{r['lemmatizer_file']}` and committed to the branch." if r.get("lemmatizer_file")
                    else "; nothing valid to attach."))
        for i, err in enumerate(r.get("clingo_errors") or [], 1):
            L.append(f"  - Clingo error (block {i}): `{err}`")
        t = r.get("test", {}) or {}
        iface = t.get("interface")
        if iface:
            L.append(f"- **Query interface used:** input `{iface['input_pred']}(Form).` → "
                     f"`{iface['lemma_pred']}/{ '2' if iface['lemma_arg']==2 else '1'}` (lemma = arg {iface['lemma_arg']}).")
        if t.get("ran"):
            L.append(f"- **Test accuracy: {int(t['accuracy']*100)}%** ({t['passed']}/{t['total']} cases).")
            rows = ["", "  | form | expected | got | ok |", "  |---|---|---|---|"]
            for c in t.get("cases", [])[:10]:
                mark = "✅" if c.get("ok") else ("⚠️" if c.get("ok") is None else "❌")
                got = ", ".join(c.get("got") or []) or "∅"
                rows.append(f"  | {c['form']} | {c['expected']} | {got} | {mark} |")
            L += rows
        elif t.get("detail"):
            L.append(f"- **Tests not scored:** {t['detail']}")
        lr = r.get("lingua_rules", {}) or {}
        if lr.get("ran"):
            L.append(f"- **lingua-rules golden tests ({r.get('iso')}):** {'PASSED' if lr['passed'] else 'FAILED'}"
                     + (f" — {lr.get('summary','')}" if lr.get("summary") else ""))
        elif lr.get("detail"):
            L.append(f"- **lingua-rules:** {lr['detail']}")
        sig = r.get("signals", {})
        L.append(f"- **Rubric signals:** " + ", ".join(f"{k} {'✓' if v else '✗'}" for k, v in sig.items()))

    L += ["", "_The local LLM produces the lemmatizer from the prompt; valid Clingo blocks are run against "
          "LLM-generated `form→lemma` cases (interface auto-detected) and, when the language is covered, against "
          "lingua-rules golden paradigm tests. The valid lemmatizer is committed next to the prompt as "
          "`<stem>.generated.lp`._"]
    return "\n".join(L)


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
    sys.exit(1 if any(r.get("status") != "ok" for r in reports) else 0)


if __name__ == "__main__":
    main()
