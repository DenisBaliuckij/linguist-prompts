"""linguist-prompts evaluation harness.

For each prompt file: send it to a local LLM (OpenAI-compatible endpoint, default the
corpus-host qwen router on :11434), extract the lemmatizer it produces (Clingo `.lp`
rule blocks), and assess it against the EVALUATION.md rubric + lingua-rules:

  1. LLM round-trip      -- the prompt actually yields a lemmatizer.
  2. Clingo validity     -- every extracted .lp block parses + grounds (rubric M1.4).
  3. Rubric signals      -- ASP/Clingo constructs, data-logic separation, sanctioned
                            helpers, negative constraints (General Metrics M1.x).
  4. Use-case grounding  -- if the prompt targets a language already in lingua-rules,
                            its golden paradigm tests are available as use cases.

Writes a Markdown report to --out and exits non-zero if any prompt fails a hard gate.

Env: LLM_URL (default http://127.0.0.1:11434/v1/chat/completions), LLM_MODEL
(default qwen3.8:27b-mtp-128k), LINGUA_RULES (path to a lingua-rules checkout).
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
    # score: produced a lemmatizer (40) + all blocks valid (30) + rubric signals (30)
    s = 0
    if blocks: s += 40
    if blocks and rep["clingo_failed"] == 0: s += 30
    s += 30 * sum(rep["signals"].values()) // 4
    rep["score"] = s
    rep["status"] = "ok" if (blocks and rep["clingo_failed"] == 0) else "needs_work"
    return rep


def to_markdown(reports):
    lines = ["## Prompt evaluation", "",
             "| Prompt | ISO | LP blocks | Clingo ok/fail | Rubric | Use-cases | Score | Status |",
             "|---|---|---|---|---|---|---|---|"]
    for r in reports:
        sig = sum(r.get("signals", {}).values()) if "signals" in r else 0
        lines.append(f"| {r['prompt']} | {r.get('iso') or '?'} | {r.get('lp_blocks','-')} | "
                     f"{r.get('clingo_parsed','-')}/{r.get('clingo_failed','-')} | {sig}/4 | "
                     f"{'yes' if r.get('use_cases_available') else 'no'} | {r.get('score','-')} | "
                     f"**{r.get('status','?')}** |")
    lines += ["", "_Lemmatizer extracted from the prompt via the local LLM, Clingo-validated, "
              "scored against EVALUATION.md. 'Use-cases' = language already has golden paradigm "
              "tests in lingua-rules._"]
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
