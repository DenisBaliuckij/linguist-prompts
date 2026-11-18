"""Tests for scripts/llm_client.py and the evaluators' model selection - no network, a local fake endpoint."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

import llm_client as lc

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
KEY = "sk-or-test-SECRET-123"


class FakeEndpoint:
    """OpenAI-compatible /chat/completions stub. `replies` is a list of (status, json_body) served in order."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                n = int(self.headers.get("Content-Length") or 0)
                outer.requests.append({"headers": dict(self.headers),
                                       "body": json.loads(self.rfile.read(n) or b"{}")})
                status, body = outer.replies.pop(0) if outer.replies else (500, {"error": "no reply"})
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                if status == 429:
                    self.send_header("Retry-After", "0")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1/chat/completions"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *a):
        self.server.shutdown()


def ok(text, finish="stop", usage=None, model="vendor/model"):
    return 200, {"model": model, "choices": [{"message": {"role": "assistant", "content": text},
                                              "finish_reason": finish}],
                 "usage": usage or {"prompt_tokens": 10, "completion_tokens": 5}}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in ("LLM_PROVIDER", "LLM_URL", "LLM_MODEL", "LLM_API_KEY", "OPENROUTER_API_KEY", "LLM_ZDR",
              "LLM_MAX_RETRIES", "LLM_JUDGE_MODEL"):
        monkeypatch.delenv(k, raising=False)


# ---------------------------------------------------------------- configuration
def test_default_is_local_model():
    cfg = lc.make_config()
    assert cfg.provider == "local" and cfg.url == lc.LOCAL_URL and cfg.model == lc.LOCAL_MODEL
    assert cfg.api_key == ""


def test_openrouter_takes_key_from_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    cfg = lc.make_config(provider="openrouter", model="vendor/model")
    assert cfg.url == lc.OPENROUTER_URL and cfg.api_key == KEY


def test_openrouter_detected_from_url(monkeypatch):
    monkeypatch.setenv("LLM_URL", lc.OPENROUTER_URL)
    monkeypatch.setenv("LLM_MODEL", "vendor/model")
    monkeypatch.setenv("LLM_API_KEY", KEY)
    assert lc.make_config().provider == "openrouter"


def test_openrouter_requires_key_and_model(monkeypatch):
    with pytest.raises(ValueError, match="API key"):
        lc.make_config(provider="openrouter", model="vendor/model")
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    with pytest.raises(ValueError, match="model id"):
        lc.make_config(provider="openrouter")


def test_key_never_in_repr_or_description(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    cfg = lc.make_config(provider="openrouter", model="vendor/model", zdr=True)
    assert KEY not in repr(cfg) and KEY not in cfg.describe()
    assert cfg.describe() == "vendor/model via openrouter (ZDR only)"


# ---------------------------------------------------------------- requests
def test_openrouter_request_headers_and_zdr():
    with FakeEndpoint([ok("hello")]) as ep:
        cfg = lc.LLMConfig(url=ep.url, model="vendor/model", api_key=KEY, provider="openrouter", zdr=True)
        res = lc.chat([{"role": "user", "content": "hi"}], cfg, max_tokens=50)
    req = ep.requests[0]
    assert req["headers"]["Authorization"] == f"Bearer {KEY}"
    assert req["headers"]["X-Title"] == "linguist-prompts"
    assert req["body"]["model"] == "vendor/model" and req["body"]["max_tokens"] == 50
    assert req["body"]["provider"] == {"zdr": True}
    assert res.text == "hello" and not res.truncated and res.usage["completion_tokens"] == 5


def test_local_request_has_no_auth_and_no_provider_field():
    with FakeEndpoint([ok("x")]) as ep:
        lc.chat([{"role": "user", "content": "hi"}], lc.LLMConfig(url=ep.url))
    req = ep.requests[0]
    assert "Authorization" not in req["headers"] and "provider" not in req["body"]


def test_retries_on_rate_limit_then_succeeds():
    with FakeEndpoint([(429, {"error": {"message": "rate limited"}}), (503, {"error": "busy"}), ok("done")]) as ep:
        res = lc.chat([{"role": "user", "content": "hi"}], lc.LLMConfig(url=ep.url, max_retries=3),
                      sleep=lambda s: None)
    assert res.text == "done" and len(ep.requests) == 3


def test_error_message_is_readable_and_has_no_key():
    with FakeEndpoint([(401, {"error": {"message": "No auth credentials found"}})]) as ep:
        cfg = lc.LLMConfig(url=ep.url, api_key=KEY, provider="openrouter", model="m")
        with pytest.raises(lc.LLMError) as ei:
            lc.chat([{"role": "user", "content": "hi"}], cfg, sleep=lambda s: None)
    assert "401" in str(ei.value) and "No auth credentials" in str(ei.value) and KEY not in str(ei.value)


def test_truncation_and_reasoning_fallback_are_reported():
    body = {"choices": [{"message": {"content": None, "reasoning": "thinking..."}, "finish_reason": "length"}]}
    with FakeEndpoint([(200, body)]) as ep:
        res = lc.chat([{"role": "user", "content": "hi"}], lc.LLMConfig(url=ep.url))
    assert res.truncated and res.from_reasoning and res.text == "thinking..."


def test_usage_meter_sums_tokens_cost_and_truncation():
    m = lc.UsageMeter()
    m.add(lc.LLMResult("a", "stop", {"prompt_tokens": 3, "completion_tokens": 4, "cost": 0.001}))
    m.add(lc.LLMResult("b", "length", {"prompt_tokens": 1, "completion_tokens": 2, "cost": 0.002}))
    assert m.as_dict() == {"calls": 2, "prompt_tokens": 4, "completion_tokens": 6,
                           "truncated_answers": 1, "cost_usd": 0.003}


# ---------------------------------------------------------------- evaluators end to end
PY_LEMMATIZER = "```python\nclass Lemmatizer:\n    def lemmatize(self, w):\n        return w\n```"


def _run(script, args, env_extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("LLM_", "OPENROUTER_"))}
    env.update(env_extra)
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True,
                          text=True, env=env, timeout=120)


def test_multistage_eval_runs_against_openrouter_style_endpoint(tmp_path):
    prompt = tmp_path / "prompts.md"
    prompt.write_text("## 1. Build a lemmatizer\n\n```text\nWrite a Python Lemmatizer class.\n```\n",
                      encoding="utf-8")
    out = tmp_path / "report.md"
    with FakeEndpoint([ok(PY_LEMMATIZER, usage={"prompt_tokens": 20, "completion_tokens": 30, "cost": 0.01})]) as ep:
        p = _run("multistage_eval.py", [str(prompt), "--out", str(out), "--provider", "openrouter",
                                        "--llm-url", ep.url, "--llm-model", "vendor/model", "--zdr"],
                 {"OPENROUTER_API_KEY": KEY})
    assert p.returncode == 0, p.stderr
    req = ep.requests[0]
    assert req["headers"]["Authorization"] == f"Bearer {KEY}" and req["body"]["provider"] == {"zdr": True}
    md = out.read_text(encoding="utf-8")
    assert "vendor/model via openrouter (ZDR only)" in md and "$0.01" in md and "| **ok** |" in md
    assert KEY not in md and KEY not in p.stdout and KEY not in p.stderr
    assert (tmp_path / "prompts.generated.py").exists()


def test_multistage_eval_flags_truncated_stage(tmp_path):
    prompt = tmp_path / "prompts.md"
    prompt.write_text("## 1. Build a lemmatizer\n\n```text\nWrite it.\n```\n", encoding="utf-8")
    out = tmp_path / "report.md"
    with FakeEndpoint([ok("```python\nx = 'unterminated\n```", finish="length")]) as ep:
        p = _run("multistage_eval.py", [str(prompt), "--out", str(out), "--llm-url", ep.url,
                                        "--llm-model", "m"], {})
    assert p.returncode == 0, p.stderr
    assert "answer cut at max_tokens in:" in out.read_text(encoding="utf-8")


def test_eval_prompt_reports_model_and_llm_error_without_key(tmp_path):
    prompt = tmp_path / "prompts.md"
    prompt.write_text("## Lemmatizer\n\n```text\nBuild a Clingo lemmatizer.\n```\n", encoding="utf-8")
    out = tmp_path / "report.md"
    with FakeEndpoint([(402, {"error": {"message": "Insufficient credits"}})]) as ep:
        p = _run("eval_prompt.py", [str(prompt), "--out", str(out), "--provider", "openrouter",
                                    "--llm-url", ep.url, "--llm-model", "vendor/model"],
                 {"OPENROUTER_API_KEY": KEY, "LINGUA_RULES": str(tmp_path / "none")})
    md = out.read_text(encoding="utf-8")
    assert "vendor/model via openrouter" in md and "Insufficient credits" in md and "llm_error" in md
    assert KEY not in md and KEY not in p.stdout and KEY not in p.stderr


def test_eval_prompt_refuses_openrouter_without_key(tmp_path):
    prompt = tmp_path / "prompts.md"
    prompt.write_text("x", encoding="utf-8")
    p = _run("eval_prompt.py", [str(prompt), "--provider", "openrouter", "--llm-model", "vendor/model"], {})
    assert p.returncode != 0 and "OPENROUTER_API_KEY" in p.stderr
