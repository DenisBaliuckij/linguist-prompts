#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared client for the OpenAI-compatible /chat/completions API used by the prompt evaluators.

Works with the lab's local model (default) and with hosted models through OpenRouter
(https://openrouter.ai), or with any other OpenAI-compatible endpoint.

Configuration (environment variables; CLI flags of the evaluators override them):

  LLM_PROVIDER        local | openrouter | openai-compatible   (default: local, or openrouter
                      when LLM_URL points at openrouter.ai)
  LLM_URL             /chat/completions URL. Default for local: the lab model; for openrouter:
                      https://openrouter.ai/api/v1/chat/completions
  LLM_MODEL           model id, e.g. "qwen3.8:27b-mtp-128k" locally or "<vendor>/<model>" on OpenRouter
                      (the list is at https://openrouter.ai/models)
  LLM_API_KEY         Bearer key for the endpoint
  OPENROUTER_API_KEY  key used when the provider is openrouter and LLM_API_KEY is empty
  LLM_ZDR             1 = OpenRouter: route only to Zero-Data-Retention endpoints
  LLM_MAX_RETRIES     retries on 429 / 5xx / network errors (default 4)

The API key is only ever sent in the Authorization header; it is never logged or written to reports.
Stdlib only.
"""
from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

LOCAL_URL = "http://127.0.0.1:11434/v1/chat/completions"
LOCAL_MODEL = "qwen3.8:27b-mtp-128k"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    """The endpoint returned an error or no usable answer."""


@dataclass
class LLMConfig:
    url: str = LOCAL_URL
    model: str = LOCAL_MODEL
    api_key: str = field(default="", repr=False)   # never printed
    provider: str = "local"
    zdr: bool = False
    max_retries: int = 4
    app_title: str = "linguist-prompts"
    app_url: str = "https://github.com/DenisBaliuckij/linguist-prompts"

    def describe(self) -> str:
        """Human-readable, key-free description for logs and reports."""
        s = f"{self.model} via {self.provider}"
        if self.provider == "openrouter" and self.zdr:
            s += " (ZDR only)"
        return s


@dataclass
class LLMResult:
    text: str
    finish_reason: str | None = None
    usage: dict = field(default_factory=dict)
    model: str | None = None          # model that actually answered (OpenRouter may report it)
    from_reasoning: bool = False      # content was empty; text is the model's reasoning field

    @property
    def truncated(self) -> bool:
        return self.finish_reason == "length"


def _truthy(v) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def make_config(provider: str | None = None, url: str | None = None, model: str | None = None,
                api_key: str | None = None, zdr: bool | None = None,
                default_url: str = LOCAL_URL, default_model: str = LOCAL_MODEL) -> LLMConfig:
    """Build a config from explicit values, falling back to the environment, then to defaults."""
    env = os.environ
    url = url or env.get("LLM_URL") or ""
    provider = (provider or env.get("LLM_PROVIDER") or "").strip().lower()
    if not provider:
        if "openrouter.ai" in url:
            provider = "openrouter"
        elif url and not any(h in url for h in ("127.0.0.1", "localhost", "[::1]")):
            provider = "openai-compatible"
        else:
            provider = "local"
    if provider not in {"local", "openrouter", "openai-compatible"}:
        raise ValueError(f"unknown LLM provider {provider!r} (use local | openrouter | openai-compatible)")
    if not url:
        url = OPENROUTER_URL if provider == "openrouter" else default_url
    key = api_key or env.get("LLM_API_KEY") or ""
    if not key and provider == "openrouter":
        key = env.get("OPENROUTER_API_KEY", "")
    model = model or env.get("LLM_MODEL") or ""
    if not model:
        if provider == "local":
            model = default_model
        else:
            raise ValueError("set the model id (--llm-model or LLM_MODEL), e.g. '<vendor>/<model>' for OpenRouter")
    if provider == "openrouter" and not key:
        raise ValueError("OpenRouter needs an API key: set OPENROUTER_API_KEY (or LLM_API_KEY / --api-key)")
    if zdr is None:
        zdr = _truthy(env.get("LLM_ZDR"))
    retries = int(env.get("LLM_MAX_RETRIES", "4") or 4)
    return LLMConfig(url=url, model=model, api_key=key, provider=provider, zdr=bool(zdr), max_retries=retries)


def _headers(cfg: LLMConfig) -> dict:
    h = {"Content-Type": "application/json"}
    if cfg.api_key:
        h["Authorization"] = "Bearer " + cfg.api_key
    if cfg.provider == "openrouter":
        # optional attribution headers recognised by OpenRouter
        h["HTTP-Referer"] = cfg.app_url
        h["X-Title"] = cfg.app_title
    return h


def _body(cfg: LLMConfig, messages, max_tokens: int, temperature: float) -> bytes:
    body = {"model": cfg.model, "messages": messages, "max_tokens": max_tokens,
            "temperature": temperature, "stream": False}
    if cfg.provider == "openrouter" and cfg.zdr:
        body["provider"] = {"zdr": True}
    return json.dumps(body).encode("utf-8")


def _retry_after(err: urllib.error.HTTPError, attempt: int) -> float:
    ra = err.headers.get("Retry-After") if err.headers else None
    try:
        if ra:
            return min(float(ra), 120.0)
    except ValueError:
        pass
    return min(2 ** attempt + random.random(), 60.0)


def _error_text(err: urllib.error.HTTPError) -> str:
    try:
        raw = err.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        raw = ""
    try:
        d = json.loads(raw)
        msg = (d.get("error") or {}).get("message") if isinstance(d.get("error"), dict) else d.get("error")
        raw = msg or raw
    except Exception:  # noqa: BLE001
        pass
    return f"HTTP {err.code}: {str(raw)[:300]}"


def chat(messages, cfg: LLMConfig, max_tokens: int = 4096, temperature: float = 0.2,
         timeout: int = 600, sleep=time.sleep) -> LLMResult:
    """One chat completion with retries on rate limits, 5xx and network errors."""
    data = _body(cfg, messages, max_tokens, temperature)
    last = ""
    for attempt in range(cfg.max_retries + 1):
        req = urllib.request.Request(cfg.url, data=data, headers=_headers(cfg))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.load(r)
        except urllib.error.HTTPError as e:
            last = _error_text(e)
            if e.code in RETRY_STATUS and attempt < cfg.max_retries:
                sleep(_retry_after(e, attempt)); continue
            raise LLMError(last) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = f"network error: {getattr(e, 'reason', e)}"
            if attempt < cfg.max_retries:
                sleep(min(2 ** attempt + random.random(), 60.0)); continue
            raise LLMError(last) from None
        if isinstance(d, dict) and d.get("error"):
            err = d["error"]
            last = (err.get("message") if isinstance(err, dict) else str(err)) or "unknown error"
            code = err.get("code") if isinstance(err, dict) else None
            if code in RETRY_STATUS and attempt < cfg.max_retries:
                sleep(min(2 ** attempt + random.random(), 60.0)); continue
            raise LLMError(f"endpoint error: {str(last)[:300]}")
        choices = d.get("choices") or []
        if not choices:
            raise LLMError("endpoint returned no choices")
        ch = choices[0]
        msg = ch.get("message") or {}
        content = msg.get("content") or ""
        from_reasoning = False
        if not content:
            content = msg.get("reasoning_content") or msg.get("reasoning") or ""
            from_reasoning = bool(content)
        return LLMResult(text=content, finish_reason=ch.get("finish_reason"), usage=d.get("usage") or {},
                         model=d.get("model"), from_reasoning=from_reasoning)
    raise LLMError(last or "no answer")


def add_cli_args(ap) -> None:
    """Common model-selection flags for the evaluators."""
    g = ap.add_argument_group("model selection (defaults: environment, then the lab's local model)")
    g.add_argument("--provider", choices=["local", "openrouter", "openai-compatible"], default=None,
                   help="where the model runs (env LLM_PROVIDER)")
    g.add_argument("--llm-url", default=None, help="OpenAI-compatible /chat/completions URL (env LLM_URL)")
    g.add_argument("--llm-model", default=None,
                   help="model id (env LLM_MODEL); on OpenRouter like '<vendor>/<model>'")
    g.add_argument("--api-key", default=None,
                   help="Bearer key. Prefer env OPENROUTER_API_KEY / LLM_API_KEY: a key on the command "
                        "line is visible to other processes and in shell history")
    g.add_argument("--zdr", action="store_true", default=None,
                   help="OpenRouter: only Zero-Data-Retention endpoints (env LLM_ZDR=1)")


def config_from_args(a, **defaults) -> LLMConfig:
    return make_config(provider=a.provider, url=a.llm_url, model=a.llm_model, api_key=a.api_key,
                       zdr=a.zdr, **defaults)


class UsageMeter:
    """Accumulates token usage (and cost, when the endpoint reports it) across calls."""

    def __init__(self):
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cost = 0.0
        self.truncated = 0

    def add(self, res: LLMResult) -> None:
        u = res.usage or {}
        self.calls += 1
        self.prompt_tokens += int(u.get("prompt_tokens") or 0)
        self.completion_tokens += int(u.get("completion_tokens") or 0)
        try:
            self.cost += float(u.get("cost") or 0)
        except (TypeError, ValueError):
            pass
        self.truncated += int(res.truncated)

    def as_dict(self) -> dict:
        d = {"calls": self.calls, "prompt_tokens": self.prompt_tokens,
             "completion_tokens": self.completion_tokens, "truncated_answers": self.truncated}
        if self.cost:
            d["cost_usd"] = round(self.cost, 4)
        return d
