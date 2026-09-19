# linguist-prompts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Task 7 is interactive (owner must supply credentials and confirm outward-facing steps) — run it inline with the owner, never in a subagent.**

**Goal:** Launch a public GitHub repo where linguists collaborate on Markdown prompts via protected-branch PRs, plus a Sunday pipeline that emails a Russian summary of the week's merged PRs.

**Architecture:** A content repo (`languages/<lang>/<subject>/`) with a GitHub Actions cron workflow that runs one stdlib-only Python script. The script reads merged PRs from the GitHub REST API, renders a deterministic Russian digest (text + HTML), and sends it over Yandex SMTP using secrets from a GitHub Environment restricted to `main`.

**Tech Stack:** Python 3.12 (stdlib only at runtime), pytest (tests only), GitHub Actions, `gh` CLI, Yandex SMTP.

**Spec:** `docs/superpowers/specs/2026-09-19-linguist-prompts-design.md`

## Global Constraints

- Working directory: `C:\Repositories\linguist-prompts` (Git Bash: `/c/Repositories/linguist-prompts`), local branch `main`. The folder `.git.corrupt-backup/` is excluded locally — never `git add -A` / `git add .`; add files by explicit path.
- Runtime code is Python stdlib only — no third-party runtime dependencies. pytest is for tests only.
- Digest window: half-open `[start, end)`; `end` = most recent Sunday 18:00 UTC that is ≤ now; `start` = `end` − 7 days.
- Email subject: `Сводка linguist-prompts: DD.MM.YYYY–DD.MM.YYYY`. Empty week body: «За неделю изменений нет». All email text is Russian; README.md and CONTRIBUTING.md are Russian (README has a one-line English summary on top).
- Digest is a deterministic template: no LLM, no external API.
- SMTP: Yandex `smtp.yandex.ru`, port `465` (implicit SSL), authenticated with an app password; `MAIL_FROM` must equal `SMTP_USER`.
- Secrets `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`, `MAIL_TO` live in GitHub Environment `digest` (deployment branch policy: `main` only). Recipient addresses appear only in `MAIL_TO` — never in the repo, never in chat. Secret values are typed by the owner via `gh secret set` (`! ` prefix), never pasted into the conversation.
- Workflow triggers: `schedule: cron "0 18 * * 0"` and `workflow_dispatch` (boolean `dry_run`, default `true`; scheduled runs are never dry). Permissions: `contents: read`, `pull-requests: read`. No `pull_request*` triggers.
- Branch protection on `main`: PR required, 1 approving review, dismiss stale approvals, `enforce_admins: true`, no force-push, no deletion, no required status checks. Squash merge only; auto-delete head branches. **Apply protection last** (Task 7) — after it, nobody, including the owner, can push to `main`.
- License: CC-BY-4.0.
- Every commit message ends with a blank line and these two trailer lines:
  ```
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01F5B6asG3P3jhnXALys1Z6x
  ```

## File Structure

| File | Responsibility |
|---|---|
| `.gitattributes`, `.gitignore` | LF line endings; ignore caches |
| `LICENSE` | CC-BY-4.0 legal code |
| `README.md`, `CONTRIBUTING.md` | Russian docs: structure, PR flow, digest, limitations |
| `.github/PULL_REQUEST_TEMPLATE.md` | Russian PR template (feeds the digest) |
| `languages/russian/grammar/{README,prompts}.md` | Seed example subject |
| `pytest.ini` | `pythonpath = scripts`, `testpaths = tests` |
| `scripts/weekly_digest.py` | The whole digest: window, GitHub collection, Russian rendering, SMTP, CLI |
| `tests/test_weekly_digest.py` | pytest suite (no network) |
| `.github/workflows/weekly-digest.yml` | Sunday cron + manual dispatch |

---

### Task 1: Repo skeleton and Russian docs

**Files:**
- Create: `.gitattributes`, `.gitignore`, `LICENSE`, `README.md`, `CONTRIBUTING.md`, `.github/PULL_REQUEST_TEMPLATE.md`, `languages/russian/grammar/README.md`, `languages/russian/grammar/prompts.md`

**Interfaces:**
- Produces: the `languages/<lang>/<subject>/` layout that `group_key()` in Task 2 parses (`languages/russian/grammar/prompts.md` → group `russian/grammar`).

- [ ] **Step 1: Create the git housekeeping files**

**Create `.gitattributes`:**

```
* text=auto eol=lf
```

**Create `.gitignore`:**

```
__pycache__/
.pytest_cache/
.venv/
```

- [ ] **Step 2: Fetch the CC-BY-4.0 license text from GitHub's license API**

Run:
```bash
cd /c/Repositories/linguist-prompts
gh api licenses/cc-by-4.0 --jq .body > LICENSE
head -3 LICENSE
```
Expected: the first line is `Attribution 4.0 International`. If `gh` fails, run `gh auth status` and stop to tell the owner.

- [ ] **Step 3: Create README.md**

**Create `README.md`:**

````markdown
# linguist-prompts

*A public collection of prompts written and reviewed by linguists, organised per language and per subject. Every change goes through a pull request.*

Публичный репозиторий, в котором лингвисты совместно пишут, дорабатывают и обсуждают промпты. Промпты хранятся в Markdown-файлах, сгруппированных по языкам и по темам.

## Структура

```
languages/
  <язык>/
    <тема>/
      README.md    — о чём эта тема и как ею пользоваться
      prompts.md   — сами промпты
```

Пример: [`languages/russian/grammar/`](languages/russian/grammar/). Новый язык или новая тема — это просто новая папка, нигде ничего регистрировать не нужно.

## Как вносить изменения

Прямые коммиты в `main` запрещены. Любое изменение вносится через pull request и должно получить одно одобрение от другого участника. Подробности — в [CONTRIBUTING.md](CONTRIBUTING.md).

## Еженедельная сводка

Каждое воскресенье в 18:00 UTC GitHub Actions собирает все pull request'ы, слитые за прошедшую неделю, и отправляет на почту сводку на русском языке: кто и что изменил. Если изменений не было, приходит короткое письмо «За неделю изменений нет». Скрипт: [`scripts/weekly_digest.py`](scripts/weekly_digest.py).

> **Ограничение GitHub.** Если в публичном репозитории 60 дней нет активности, запланированные workflow отключаются автоматически, и сводки перестают приходить. Если это случилось, включите workflow заново на вкладке Actions.

## Лицензия

[CC-BY-4.0](LICENSE): материалы можно использовать и изменять, указывая авторство.
````

- [ ] **Step 4: Create CONTRIBUTING.md**

**Create `CONTRIBUTING.md`:**

`````markdown
# Как вносить изменения

## Порядок работы

1. Создайте ветку от `main` (например, `russian-grammar-cases`).
2. Добавьте или измените файлы в `languages/<язык>/<тема>/`.
3. Откройте pull request и заполните шаблон: что изменилось и зачем. Этот текст попадает в еженедельную сводку.
4. Обсудите изменения в комментариях к pull request'у. Для слияния нужно одно одобрение (Approve) от другого участника.
5. После одобрения pull request сливается методом squash, ветка удаляется автоматически.

Свои изменения нельзя одобрить самостоятельно, а в `main` нельзя пушить напрямую — это касается всех, включая владельца репозитория.

## Именование папок

- Язык — по-английски, строчными буквами: `russian`, `english`, `german`.
- Тема — по-английски, строчными буквами, слова через дефис: `grammar`, `idioms`, `business-writing`.

## Формат `prompts.md`

Каждый промпт — отдельный раздел второго уровня:

````text
## Название промпта

**Назначение:** одна фраза о том, для чего промпт.

```text
Текст промпта. Переменные пишите в двойных фигурных скобках: {{текст}}.
```
````

## Формат `README.md` темы

Одним-двумя абзацами опишите, какие задачи решают промпты темы и что важно знать при их использовании.
`````

- [ ] **Step 5: Create the PR template and the seed subject**

**Create `.github/PULL_REQUEST_TEMPLATE.md`:**

````markdown
## Что изменилось
<!-- Кратко: какие промпты добавлены, изменены или удалены -->

## Зачем
<!-- Почему это улучшает промпты; ссылка на обсуждение, если оно было -->

## Язык и тема
<!-- Например: russian/grammar -->
````

**Create `languages/russian/grammar/README.md`:**

````markdown
# Русский язык · грамматика

Промпты для задач по русской грамматике: проверка согласования, разбор предложений, объяснение правил.

Сами промпты — в файле [prompts.md](prompts.md).
````

**Create `languages/russian/grammar/prompts.md`:**

````markdown
# Промпты: русский язык · грамматика

## Проверка согласования

**Назначение:** найти ошибки согласования в тексте.

```text
Ты — редактор-лингвист. Проверь текст ниже на ошибки согласования по роду, числу и падежу. Для каждой ошибки укажи фрагмент, правильный вариант и краткое объяснение. Если ошибок нет, напиши «Ошибок согласования не найдено».

Текст:
{{текст}}
```
````

- [ ] **Step 6: Verify and commit**

Run:
```bash
cd /c/Repositories/linguist-prompts
git add .gitattributes .gitignore LICENSE README.md CONTRIBUTING.md .github/PULL_REQUEST_TEMPLATE.md languages
git status -s
```
Expected: 8 files staged (`A`), nothing untracked except nothing (the backup folder is excluded).

```bash
git commit -F - <<'EOF'
docs: add repo skeleton, Russian docs, PR template and seed subject

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01F5B6asG3P3jhnXALys1Z6x
EOF
```

---

### Task 2: Digest helpers — window, grouping, approvers, mail config

**Files:**
- Create: `pytest.ini`, `scripts/weekly_digest.py`, `tests/test_weekly_digest.py`

**Interfaces:**
- Produces (all in `scripts/weekly_digest.py`, imported in tests as `import weekly_digest as wd`):
  - `class ConfigError(Exception)`
  - `@dataclass(frozen=True) class MailConfig: host: str; port: int; user: str; password: str; sender: str; recipients: tuple[str, ...]`
  - `digest_window(now: datetime) -> tuple[datetime, datetime]` — `(start, end)`, UTC-aware; raises `ValueError` for naive input
  - `group_key(path: str) -> str` — `"russian/grammar"` or `OTHER_GROUP` (`"Прочее"`)
  - `approvers_from_reviews(reviews: list[dict]) -> tuple[str, ...]` — sorted logins
  - `parse_mail_to(value: str) -> tuple[str, ...]`
  - `load_mail_config(env: Mapping[str, str]) -> MailConfig`
  - Module constants `GITHUB_API`, `OTHER_GROUP`; the imports at the top of the module are used by all later tasks.

- [ ] **Step 1: Write pytest.ini and the failing tests**

**Create `pytest.ini`:**

```ini
[pytest]
pythonpath = scripts
testpaths = tests
```

**Create `tests/test_weekly_digest.py`:**

```python
"""Tests for scripts/weekly_digest.py - no network, fixture data only."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import weekly_digest as wd

UTC = timezone.utc
REPO = "acme/linguist-prompts"


def dt(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


START = dt(2026, 9, 13, 18, 0)
END = dt(2026, 9, 20, 18, 0)


# --- digest_window ---------------------------------------------------------


@pytest.mark.parametrize(
    "now, expected_end",
    [
        (dt(2026, 9, 20, 18, 5), dt(2026, 9, 20, 18, 0)),  # Sunday, after 18:00
        (dt(2026, 9, 20, 18, 0), dt(2026, 9, 20, 18, 0)),  # Sunday, exactly 18:00
        (dt(2026, 9, 20, 17, 59), dt(2026, 9, 13, 18, 0)),  # Sunday, before 18:00
        (dt(2026, 9, 16, 12, 0), dt(2026, 9, 13, 18, 0)),  # Wednesday
        (dt(2026, 9, 19, 23, 0), dt(2026, 9, 13, 18, 0)),  # Saturday
        (dt(2026, 9, 14, 0, 0), dt(2026, 9, 13, 18, 0)),  # Monday
    ],
)
def test_digest_window_end_is_latest_sunday_1800_utc(now, expected_end):
    start, end = wd.digest_window(now)
    assert end == expected_end
    assert start == expected_end - timedelta(days=7)


def test_digest_window_converts_other_timezones_to_utc():
    msk = timezone(timedelta(hours=3))
    now = datetime(2026, 9, 20, 21, 0, tzinfo=msk)  # == 18:00 UTC
    start, end = wd.digest_window(now)
    assert end == dt(2026, 9, 20, 18, 0)
    assert end.utcoffset() == timedelta(0)
    assert start.utcoffset() == timedelta(0)


def test_digest_window_rejects_naive_datetime():
    with pytest.raises(ValueError):
        wd.digest_window(datetime(2026, 9, 20, 18, 0))


# --- group_key -------------------------------------------------------------


@pytest.mark.parametrize(
    "path, expected",
    [
        ("languages/russian/grammar/prompts.md", "russian/grammar"),
        ("languages/russian/grammar/README.md", "russian/grammar"),
        ("languages/english/idioms/deep/nested.md", "english/idioms"),
        ("languages/russian/README.md", wd.OTHER_GROUP),
        ("README.md", wd.OTHER_GROUP),
        (".github/workflows/weekly-digest.yml", wd.OTHER_GROUP),
    ],
)
def test_group_key(path, expected):
    assert wd.group_key(path) == expected


# --- approvers_from_reviews ------------------------------------------------


def review(user, state, submitted_at):
    return {"user": {"login": user}, "state": state, "submitted_at": submitted_at}


def test_approvers_latest_decisive_state_wins():
    reviews = [
        review("bob", "APPROVED", "2026-09-15T10:00:00Z"),
        review("carol", "CHANGES_REQUESTED", "2026-09-15T10:05:00Z"),
        review("carol", "APPROVED", "2026-09-15T11:00:00Z"),
        review("dave", "APPROVED", "2026-09-15T10:10:00Z"),
        review("dave", "CHANGES_REQUESTED", "2026-09-15T12:00:00Z"),
    ]
    assert wd.approvers_from_reviews(reviews) == ("bob", "carol")


def test_approvers_comment_does_not_cancel_approval():
    reviews = [
        review("bob", "APPROVED", "2026-09-15T10:00:00Z"),
        review("bob", "COMMENTED", "2026-09-15T11:00:00Z"),
    ]
    assert wd.approvers_from_reviews(reviews) == ("bob",)


def test_approvers_dismissed_approval_is_removed():
    reviews = [
        review("bob", "APPROVED", "2026-09-15T10:00:00Z"),
        review("bob", "DISMISSED", "2026-09-15T11:00:00Z"),
    ]
    assert wd.approvers_from_reviews(reviews) == ()


def test_approvers_ignores_pending_and_deleted_users():
    reviews = [
        {"user": {"login": "bob"}, "state": "PENDING", "submitted_at": None},
        {"user": None, "state": "APPROVED", "submitted_at": "2026-09-15T10:00:00Z"},
    ]
    assert wd.approvers_from_reviews(reviews) == ()


# --- mail config -----------------------------------------------------------

GOOD_ENV = {
    "SMTP_HOST": "smtp.yandex.ru",
    "SMTP_PORT": "465",
    "SMTP_USER": "bot@yandex.ru",
    "SMTP_PASSWORD": "app-password",
    "MAIL_FROM": "bot@yandex.ru",
    "MAIL_TO": "a@x.ru, b@y.ru",
}


def test_parse_mail_to_accepts_commas_and_semicolons():
    assert wd.parse_mail_to("a@x.ru, b@y.ru;c@z.ru") == ("a@x.ru", "b@y.ru", "c@z.ru")


def test_parse_mail_to_empty():
    assert wd.parse_mail_to(" ; , ") == ()


def test_load_mail_config_ok():
    cfg = wd.load_mail_config(GOOD_ENV)
    assert cfg.host == "smtp.yandex.ru"
    assert cfg.port == 465
    assert cfg.user == "bot@yandex.ru"
    assert cfg.password == "app-password"
    assert cfg.sender == "bot@yandex.ru"
    assert cfg.recipients == ("a@x.ru", "b@y.ru")


def test_load_mail_config_reports_all_missing_names():
    env = {k: v for k, v in GOOD_ENV.items() if k not in ("SMTP_PASSWORD", "MAIL_TO")}
    with pytest.raises(wd.ConfigError) as exc:
        wd.load_mail_config(env)
    assert "SMTP_PASSWORD" in str(exc.value)
    assert "MAIL_TO" in str(exc.value)


def test_load_mail_config_rejects_non_integer_port():
    with pytest.raises(wd.ConfigError, match="SMTP_PORT"):
        wd.load_mail_config({**GOOD_ENV, "SMTP_PORT": "ssl"})


def test_load_mail_config_rejects_from_different_from_user():
    with pytest.raises(wd.ConfigError, match="MAIL_FROM"):
        wd.load_mail_config({**GOOD_ENV, "MAIL_FROM": "other@yandex.ru"})


def test_load_mail_config_rejects_empty_recipient_list():
    with pytest.raises(wd.ConfigError, match="MAIL_TO"):
        wd.load_mail_config({**GOOD_ENV, "MAIL_TO": " ; "})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /c/Repositories/linguist-prompts && python -m pytest -q`
Expected: collection error `ModuleNotFoundError: No module named 'weekly_digest'`. (If `No module named pytest`, run `python -m pip install pytest` first.)

- [ ] **Step 3: Write the module header and helpers**

**Create `scripts/weekly_digest.py`:**

```python
"""Weekly digest of merged pull requests, emailed in Russian.

Stdlib only. Run by .github/workflows/weekly-digest.yml every Sunday 18:00 UTC.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import smtplib
import sys
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any

GITHUB_API = "https://api.github.com"
OTHER_GROUP = "Прочее"
DIGEST_WEEKDAY = 6  # Sunday, as returned by datetime.weekday()
DIGEST_HOUR_UTC = 18

REQUIRED_MAIL_ENV = (
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "MAIL_FROM",
    "MAIL_TO",
)

_GROUP_RE = re.compile(r"^languages/([^/]+)/([^/]+)/")


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class MailConfig:
    host: str
    port: int
    user: str
    password: str
    sender: str
    recipients: tuple[str, ...]


def digest_window(now: datetime) -> tuple[datetime, datetime]:
    """Return the half-open window [start, end) the digest covers.

    `end` is the most recent Sunday 18:00 UTC that is <= now, `start` is 7 days
    earlier. Anchoring to the calendar (not to `now`) means a delayed cron run
    can neither miss nor double-count a pull request.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)
    days_back = (now.weekday() - DIGEST_WEEKDAY) % 7
    end = (now - timedelta(days=days_back)).replace(
        hour=DIGEST_HOUR_UTC, minute=0, second=0, microsecond=0
    )
    if end > now:
        end -= timedelta(days=7)
    return end - timedelta(days=7), end


def group_key(path: str) -> str:
    """Map a changed file path to 'language/subject', else OTHER_GROUP."""
    match = _GROUP_RE.match(path)
    return f"{match[1]}/{match[2]}" if match else OTHER_GROUP


def approvers_from_reviews(reviews: list[dict[str, Any]]) -> tuple[str, ...]:
    """Logins whose latest decisive review (approve/changes/dismiss) is APPROVED."""
    latest: dict[str, str] = {}
    for item in sorted(reviews, key=lambda r: r.get("submitted_at") or ""):
        user = (item.get("user") or {}).get("login")
        state = item.get("state")
        if user and state in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            latest[user] = state
    return tuple(sorted(u for u, s in latest.items() if s == "APPROVED"))


def parse_mail_to(value: str) -> tuple[str, ...]:
    return tuple(p.strip() for p in re.split(r"[;,]", value) if p.strip())


def load_mail_config(env: Mapping[str, str]) -> MailConfig:
    missing = [name for name in REQUIRED_MAIL_ENV if not env.get(name)]
    if missing:
        raise ConfigError(
            "Missing required environment variables: " + ", ".join(missing)
        )
    try:
        port = int(env["SMTP_PORT"])
    except ValueError:
        raise ConfigError("SMTP_PORT must be an integer") from None
    user = env["SMTP_USER"].strip()
    sender = env["MAIL_FROM"].strip()
    if sender.lower() != user.lower():
        raise ConfigError(
            "MAIL_FROM must equal SMTP_USER (Yandex rejects other From addresses)"
        )
    recipients = parse_mail_to(env["MAIL_TO"])
    if not recipients:
        raise ConfigError("MAIL_TO contains no addresses")
    return MailConfig(
        host=env["SMTP_HOST"],
        port=port,
        user=user,
        password=env["SMTP_PASSWORD"],
        sender=sender,
        recipients=recipients,
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest -q`
Expected: `25 passed`.

- [ ] **Step 5: Commit**

```bash
git add pytest.ini scripts/weekly_digest.py tests/test_weekly_digest.py
git commit -F - <<'EOF'
feat(digest): add window, grouping, approver and mail-config helpers

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01F5B6asG3P3jhnXALys1Z6x
EOF
```

---

### Task 3: Collect merged PRs from the GitHub API

**Files:**
- Modify: `scripts/weekly_digest.py` (append)
- Modify: `tests/test_weekly_digest.py` (append)

**Interfaces:**
- Consumes: `approvers_from_reviews`, `GITHUB_API`, the module imports (Task 2).
- Produces:
  - `@dataclass(frozen=True) class FileChange: path: str; status: str` (`status` ∈ `"added" | "modified" | "removed" | "renamed"`)
  - `@dataclass(frozen=True) class MergedPR: number: int; title: str; url: str; author: str; approvers: tuple[str, ...]; merged_at: datetime; files: tuple[FileChange, ...]`
  - `Api = Callable[[str], Any]` — takes an API path (e.g. `"/repos/o/r/pulls?..."`), returns parsed JSON
  - `make_github_api(token: str) -> Api`
  - `paginate(api: Api, path: str) -> list` — appends `?per_page=100&page=N`, stops on a page with < 100 items
  - `parse_ts(value: str) -> datetime`, `normalize_status(raw: str) -> str`
  - `collect_merged_prs(api: Api, repo: str, start: datetime, end: datetime) -> list[MergedPR]` — merged in `[start, end)`, oldest merge first

- [ ] **Step 1: Append the failing tests**

**Append to `tests/test_weekly_digest.py`:**

```python
# --- GitHub collection -----------------------------------------------------


def list_path(page: int) -> str:
    return (
        f"/repos/{REPO}/pulls?state=closed&sort=updated&direction=desc"
        f"&per_page=100&page={page}"
    )


def files_path(number: int, page: int = 1) -> str:
    return f"/repos/{REPO}/pulls/{number}/files?per_page=100&page={page}"


def reviews_path(number: int, page: int = 1) -> str:
    return f"/repos/{REPO}/pulls/{number}/reviews?per_page=100&page={page}"


def pr_json(number, merged_at, updated_at=None, login="alice"):
    return {
        "number": number,
        "title": f"PR {number}",
        "html_url": f"https://github.com/{REPO}/pull/{number}",
        "user": {"login": login},
        "merged_at": merged_at,
        "updated_at": updated_at or merged_at,
    }


def file_json(path, status="modified"):
    return {"filename": path, "status": status}


def fake_api(routes):
    calls = []

    def api(path):
        calls.append(path)
        return routes[path]

    api.calls = calls
    return api


def test_paginate_follows_full_pages():
    pages = {
        "/x?per_page=100&page=1": list(range(100)),
        "/x?per_page=100&page=2": [100, 101],
    }
    assert wd.paginate(lambda p: pages[p], "/x") == list(range(102))


def test_paginate_stops_on_short_page():
    calls = []

    def api(path):
        calls.append(path)
        return [1, 2, 3]

    assert wd.paginate(api, "/x") == [1, 2, 3]
    assert calls == ["/x?per_page=100&page=1"]


def test_collect_merged_prs_filters_window_and_sorts():
    routes = {
        list_path(1): [
            pr_json(14, "2026-09-21T09:00:00Z"),  # after the window
            pr_json(13, "2026-09-20T18:00:00Z"),  # exactly END: excluded
            pr_json(12, "2026-09-19T08:00:00Z", login="bob"),
            pr_json(11, None, updated_at="2026-09-18T08:00:00Z"),  # closed, unmerged
            pr_json(10, "2026-09-13T18:00:00Z"),  # exactly START: included
            pr_json(9, "2026-09-10T08:00:00Z"),  # before the window
        ],
        files_path(12): [
            file_json("languages/russian/grammar/prompts.md", "added"),
            file_json("README.md", "changed"),
        ],
        reviews_path(12): [review("carol", "APPROVED", "2026-09-19T07:00:00Z")],
        files_path(10): [file_json("languages/english/idioms/prompts.md", "removed")],
        reviews_path(10): [],
    }
    api = fake_api(routes)

    prs = wd.collect_merged_prs(api, REPO, START, END)

    assert [p.number for p in prs] == [10, 12]  # oldest merge first
    pr12 = prs[1]
    assert pr12.title == "PR 12"
    assert pr12.url == f"https://github.com/{REPO}/pull/12"
    assert pr12.author == "bob"
    assert pr12.approvers == ("carol",)
    assert pr12.merged_at == dt(2026, 9, 19, 8, 0)
    assert pr12.files == (
        wd.FileChange("languages/russian/grammar/prompts.md", "added"),
        wd.FileChange("README.md", "modified"),  # unknown statuses -> modified
    )
    assert prs[0].files == (
        wd.FileChange("languages/english/idioms/prompts.md", "removed"),
    )
    assert prs[0].approvers == ()


def test_collect_merged_prs_continues_while_pages_are_in_window():
    routes = {
        list_path(1): [
            pr_json(1000 + i, None, updated_at="2026-09-18T00:00:00Z")
            for i in range(100)
        ],
        list_path(2): [pr_json(5, "2026-09-15T10:00:00Z")],
        files_path(5): [file_json("README.md")],
        reviews_path(5): [],
    }
    api = fake_api(routes)

    prs = wd.collect_merged_prs(api, REPO, START, END)

    assert [p.number for p in prs] == [5]
    assert list_path(2) in api.calls
    assert list_path(3) not in api.calls


def test_collect_merged_prs_stops_when_page_is_older_than_window():
    routes = {
        list_path(1): [
            pr_json(1000 + i, None, updated_at="2026-09-01T00:00:00Z")
            for i in range(100)
        ],
    }
    api = fake_api(routes)

    assert wd.collect_merged_prs(api, REPO, START, END) == []
    assert api.calls == [list_path(1)]


def test_collect_merged_prs_follows_file_pagination():
    routes = {
        list_path(1): [pr_json(7, "2026-09-15T10:00:00Z")],
        files_path(7, 1): [file_json(f"languages/a/b/{i}.md") for i in range(100)],
        files_path(7, 2): [file_json("languages/a/b/last.md")],
        reviews_path(7): [],
    }

    prs = wd.collect_merged_prs(fake_api(routes), REPO, START, END)

    assert len(prs[0].files) == 101


def test_make_github_api_sends_auth_and_parses_json(monkeypatch):
    seen = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, *args):
            return b'[{"ok": true}]'

    def fake_urlopen(request, timeout=None):
        seen["url"] = request.full_url
        seen["auth"] = request.get_header("Authorization")
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(wd.urllib.request, "urlopen", fake_urlopen)

    api = wd.make_github_api("tok")

    assert api("/repos/a/b/pulls") == [{"ok": True}]
    assert seen["url"] == "https://api.github.com/repos/a/b/pulls"
    assert seen["auth"] == "Bearer tok"
    assert seen["timeout"] == 30
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `python -m pytest -q`
Expected: the new tests FAIL with `AttributeError: module 'weekly_digest' has no attribute 'paginate'` (or `FileChange` / `make_github_api`); the Task 2 tests still pass.

- [ ] **Step 3: Append the implementation**

**Append to `scripts/weekly_digest.py`:**

```python


@dataclass(frozen=True)
class FileChange:
    path: str
    status: str  # "added" | "modified" | "removed" | "renamed"


@dataclass(frozen=True)
class MergedPR:
    number: int
    title: str
    url: str
    author: str
    approvers: tuple[str, ...]
    merged_at: datetime
    files: tuple[FileChange, ...]


Api = Callable[[str], Any]


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize_status(raw: str) -> str:
    return raw if raw in ("added", "removed", "renamed") else "modified"


def make_github_api(token: str) -> Api:
    def api(path: str) -> Any:
        request = urllib.request.Request(
            GITHUB_API + path,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "linguist-prompts-weekly-digest",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    return api


def paginate(api: Api, path: str) -> list[Any]:
    items: list[Any] = []
    page = 1
    while True:
        batch = api(f"{path}?per_page=100&page={page}")
        items.extend(batch)
        if len(batch) < 100:
            return items
        page += 1


def collect_merged_prs(
    api: Api, repo: str, start: datetime, end: datetime
) -> list[MergedPR]:
    """Return pull requests merged in [start, end), oldest merge first."""
    raw_prs: list[dict[str, Any]] = []
    page = 1
    while True:
        batch = api(
            f"/repos/{repo}/pulls?state=closed&sort=updated&direction=desc"
            f"&per_page=100&page={page}"
        )
        for pr in batch:
            merged_at = pr.get("merged_at")
            if merged_at and start <= parse_ts(merged_at) < end:
                raw_prs.append(pr)
        # merged_at <= updated_at and the list is sorted by updated_at
        # descending, so once a page ends before `start` nothing later matches.
        if len(batch) < 100 or parse_ts(batch[-1]["updated_at"]) < start:
            break
        page += 1

    result: list[MergedPR] = []
    for pr in raw_prs:
        number = pr["number"]
        files = paginate(api, f"/repos/{repo}/pulls/{number}/files")
        reviews = paginate(api, f"/repos/{repo}/pulls/{number}/reviews")
        result.append(
            MergedPR(
                number=number,
                title=pr["title"],
                url=pr["html_url"],
                author=pr["user"]["login"],
                approvers=approvers_from_reviews(reviews),
                merged_at=parse_ts(pr["merged_at"]),
                files=tuple(
                    FileChange(f["filename"], normalize_status(f["status"]))
                    for f in files
                ),
            )
        )
    result.sort(key=lambda p: p.merged_at)
    return result
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/weekly_digest.py tests/test_weekly_digest.py
git commit -F - <<'EOF'
feat(digest): collect merged PRs, files and approvers from the GitHub API

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01F5B6asG3P3jhnXALys1Z6x
EOF
```

---

### Task 4: Render the Russian digest (text + HTML)

**Files:**
- Modify: `scripts/weekly_digest.py` (append)
- Modify: `tests/test_weekly_digest.py` (append)

**Interfaces:**
- Consumes: `MergedPR`, `FileChange`, `group_key`, `OTHER_GROUP` (Tasks 2–3).
- Produces:
  - `plural_ru(n: int, one: str, few: str, many: str) -> str`
  - `digest_subject(repo: str, start: datetime, end: datetime) -> str` → `"Сводка linguist-prompts: 13.09.2026–20.09.2026"`
  - `group_prs(prs: list[MergedPR]) -> list[tuple[str, list[tuple[MergedPR, tuple[FileChange, ...]]]]]` — groups sorted alphabetically, `OTHER_GROUP` last; a PR appears in every group it touched with only that group's files; a PR with no files goes to `OTHER_GROUP` with `()`
  - `render_text(prs, start, end, repo) -> str`
  - `render_html(prs, start, end, repo) -> str`

- [ ] **Step 1: Append the failing tests**

**Append to `tests/test_weekly_digest.py`:**

```python
# --- rendering -------------------------------------------------------------


def make_pr(
    number=12,
    title="Добавить примеры падежей",
    author="alice",
    approvers=("bob",),
    merged_at=None,
    files=None,
):
    return wd.MergedPR(
        number=number,
        title=title,
        url=f"https://github.com/{REPO}/pull/{number}",
        author=author,
        approvers=tuple(approvers),
        merged_at=merged_at or dt(2026, 9, 15, 10, 0),
        files=tuple(
            files
            if files is not None
            else [wd.FileChange("languages/russian/grammar/prompts.md", "added")]
        ),
    )


@pytest.mark.parametrize(
    "n, expected",
    [
        (0, "many"),
        (1, "one"),
        (2, "few"),
        (3, "few"),
        (4, "few"),
        (5, "many"),
        (11, "many"),
        (12, "many"),
        (14, "many"),
        (20, "many"),
        (21, "one"),
        (22, "few"),
        (111, "many"),
    ],
)
def test_plural_ru(n, expected):
    assert wd.plural_ru(n, "one", "few", "many") == expected


def test_digest_subject():
    assert (
        wd.digest_subject(REPO, START, END)
        == "Сводка linguist-prompts: 13.09.2026–20.09.2026"
    )


def test_group_prs_orders_groups_and_splits_files_per_group():
    pr = make_pr(
        files=[
            wd.FileChange("languages/russian/grammar/prompts.md", "modified"),
            wd.FileChange("languages/english/idioms/prompts.md", "added"),
            wd.FileChange("README.md", "modified"),
        ]
    )

    groups = wd.group_prs([pr])

    assert [key for key, _ in groups] == [
        "english/idioms",
        "russian/grammar",
        wd.OTHER_GROUP,
    ]
    first_pr, first_files = groups[0][1][0]
    assert first_pr is pr
    assert [f.path for f in first_files] == ["languages/english/idioms/prompts.md"]


def test_group_prs_puts_pr_without_files_into_other_group():
    pr = make_pr(files=[])
    assert wd.group_prs([pr]) == [(wd.OTHER_GROUP, [(pr, ())])]


def test_render_text_normal_week():
    text = wd.render_text([make_pr()], START, END, REPO)

    assert "Сводка linguist-prompts" in text
    assert "Период: 13.09.2026 18:00 – 20.09.2026 18:00 (UTC)" in text
    assert "Репозиторий: https://github.com/acme/linguist-prompts" in text
    assert "Всего: 1 слитый PR, 1 участник, 1 изменённый файл." in text
    assert "== russian/grammar ==" in text
    assert f"• #12 Добавить примеры падежей — https://github.com/{REPO}/pull/12" in text
    assert "Автор: @alice · Одобрили: @bob · Слит: 15.09.2026" in text
    assert "– добавлен: languages/russian/grammar/prompts.md" in text


def test_render_text_multiple_groups_in_order_with_other_last():
    pr = make_pr(
        files=[
            wd.FileChange("languages/russian/grammar/prompts.md", "modified"),
            wd.FileChange("languages/english/idioms/prompts.md", "added"),
            wd.FileChange("README.md", "modified"),
        ]
    )

    text = wd.render_text([pr], START, END, REPO)

    assert (
        text.index("== english/idioms ==")
        < text.index("== russian/grammar ==")
        < text.index("== Прочее ==")
    )
    assert "Всего: 1 слитый PR, 1 участник, 3 изменённых файла." in text


def test_render_text_totals_count_unique_authors_and_files():
    prs = [make_pr(number=1), make_pr(number=2)]  # same author, same file
    text = wd.render_text(prs, START, END, REPO)
    assert "Всего: 2 слитых PR, 1 участник, 1 изменённый файл." in text


def test_render_text_without_approvers_shows_dash():
    text = wd.render_text([make_pr(approvers=())], START, END, REPO)
    assert "Одобрили: —" in text


def test_render_text_pr_without_files_is_still_listed():
    text = wd.render_text([make_pr(files=[])], START, END, REPO)
    assert "== Прочее ==" in text
    assert "• #12" in text


def test_render_text_empty_week():
    text = wd.render_text([], START, END, REPO)
    assert "За неделю изменений нет." in text
    assert "Период: 13.09.2026 18:00 – 20.09.2026 18:00 (UTC)" in text
    assert "Репозиторий: https://github.com/acme/linguist-prompts" in text
    assert "Всего" not in text


def test_render_html_normal_week():
    out = wd.render_html([make_pr()], START, END, REPO)
    assert "<h3>russian/grammar</h3>" in out
    assert f'<a href="https://github.com/{REPO}/pull/12">' in out
    assert "<code>languages/russian/grammar/prompts.md</code>" in out
    assert "Автор: @alice" in out


def test_render_html_escapes_untrusted_text():
    out = wd.render_html(
        [make_pr(title="<script>alert(1)</script> & co")], START, END, REPO
    )
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; co" in out
    assert "<script>" not in out


def test_render_html_empty_week():
    out = wd.render_html([], START, END, REPO)
    assert "За неделю изменений нет." in out
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `python -m pytest -q`
Expected: the new tests FAIL with `AttributeError: module 'weekly_digest' has no attribute 'plural_ru'` (or `group_prs`, `render_text`, ...).

- [ ] **Step 3: Append the implementation**

**Append to `scripts/weekly_digest.py`:**

```python


STATUS_LABELS = {
    "added": "добавлен",
    "modified": "изменён",
    "removed": "удалён",
    "renamed": "переименован",
}

GroupEntry = tuple[MergedPR, tuple[FileChange, ...]]


def plural_ru(n: int, one: str, few: str, many: str) -> str:
    n10, n100 = n % 10, n % 100
    if n10 == 1 and n100 != 11:
        return one
    if 2 <= n10 <= 4 and not 12 <= n100 <= 14:
        return few
    return many


def _fmt_date(value: datetime) -> str:
    return value.strftime("%d.%m.%Y")


def _fmt_datetime(value: datetime) -> str:
    return value.strftime("%d.%m.%Y %H:%M")


def _repo_name(repo: str) -> str:
    return repo.split("/")[-1]


def digest_subject(repo: str, start: datetime, end: datetime) -> str:
    return f"Сводка {_repo_name(repo)}: {_fmt_date(start)}–{_fmt_date(end)}"


def group_prs(prs: list[MergedPR]) -> list[tuple[str, list[GroupEntry]]]:
    groups: dict[str, list[GroupEntry]] = {}
    for pr in prs:
        by_group: dict[str, list[FileChange]] = {}
        for change in pr.files:
            by_group.setdefault(group_key(change.path), []).append(change)
        if not by_group:
            by_group[OTHER_GROUP] = []
        for key, changes in by_group.items():
            groups.setdefault(key, []).append((pr, tuple(changes)))
    ordered = sorted(key for key in groups if key != OTHER_GROUP)
    if OTHER_GROUP in groups:
        ordered.append(OTHER_GROUP)
    return [(key, groups[key]) for key in ordered]


def _totals_sentence(prs: list[MergedPR]) -> str:
    n_prs = len(prs)
    n_authors = len({pr.author for pr in prs})
    n_files = len({change.path for pr in prs for change in pr.files})
    return (
        f"Всего: {n_prs} {plural_ru(n_prs, 'слитый PR', 'слитых PR', 'слитых PR')}, "
        f"{n_authors} {plural_ru(n_authors, 'участник', 'участника', 'участников')}, "
        f"{n_files} "
        f"{plural_ru(n_files, 'изменённый файл', 'изменённых файла', 'изменённых файлов')}."
    )


def _approvers_text(pr: MergedPR) -> str:
    return ", ".join(f"@{login}" for login in pr.approvers) or "—"


def render_text(
    prs: list[MergedPR], start: datetime, end: datetime, repo: str
) -> str:
    lines = [
        f"Сводка {_repo_name(repo)}",
        f"Период: {_fmt_datetime(start)} – {_fmt_datetime(end)} (UTC)",
        f"Репозиторий: https://github.com/{repo}",
        "",
    ]
    if not prs:
        lines.append("За неделю изменений нет.")
        return "\n".join(lines) + "\n"
    lines.append(_totals_sentence(prs))
    for key, entries in group_prs(prs):
        lines += ["", f"== {key} =="]
        for pr, changes in entries:
            lines.append(f"• #{pr.number} {pr.title} — {pr.url}")
            lines.append(
                f"  Автор: @{pr.author} · Одобрили: {_approvers_text(pr)}"
                f" · Слит: {_fmt_date(pr.merged_at)}"
            )
            for change in changes:
                lines.append(f"  – {STATUS_LABELS[change.status]}: {change.path}")
    return "\n".join(lines) + "\n"


def render_html(
    prs: list[MergedPR], start: datetime, end: datetime, repo: str
) -> str:
    esc = html.escape
    repo_url = f"https://github.com/{repo}"
    parts = [
        '<html><body style="font-family: sans-serif">',
        f"<h2>Сводка {esc(_repo_name(repo))}</h2>",
        f"<p>Период: {_fmt_datetime(start)} – {_fmt_datetime(end)} (UTC)<br>"
        f'Репозиторий: <a href="{esc(repo_url)}">{esc(repo_url)}</a></p>',
    ]
    if not prs:
        parts.append("<p>За неделю изменений нет.</p>")
    else:
        parts.append(f"<p>{esc(_totals_sentence(prs))}</p>")
        for key, entries in group_prs(prs):
            parts.append(f"<h3>{esc(key)}</h3><ul>")
            for pr, changes in entries:
                parts.append(
                    f'<li><a href="{esc(pr.url)}">#{pr.number} {esc(pr.title)}</a><br>'
                    f"Автор: @{esc(pr.author)} · Одобрили: {esc(_approvers_text(pr))}"
                    f" · Слит: {_fmt_date(pr.merged_at)}<ul>"
                )
                for change in changes:
                    parts.append(
                        f"<li>{STATUS_LABELS[change.status]}: "
                        f"<code>{esc(change.path)}</code></li>"
                    )
                parts.append("</ul></li>")
            parts.append("</ul>")
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/weekly_digest.py tests/test_weekly_digest.py
git commit -F - <<'EOF'
feat(digest): render the Russian digest as plain text and HTML

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01F5B6asG3P3jhnXALys1Z6x
EOF
```

---

### Task 5: Email message, SMTP send and CLI

**Files:**
- Modify: `scripts/weekly_digest.py` (append)
- Modify: `tests/test_weekly_digest.py` (append)

**Interfaces:**
- Consumes: everything from Tasks 2–4.
- Produces:
  - `build_message(prs, start, end, repo, sender: str, recipients: tuple[str, ...]) -> EmailMessage` (plain + HTML alternative)
  - `send_email(msg: EmailMessage, cfg: MailConfig) -> None` (`smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=30)`, login, `send_message`)
  - `parse_now(value: str | None) -> datetime`
  - `main(argv=None, env=None, api=None) -> int` — `--dry-run`, `--now ISO`; `env` defaults to `os.environ`; `api` defaults to `make_github_api(GITHUB_TOKEN)`. Raises `ConfigError` for missing config (mail config is validated **before** any API call unless `--dry-run`).
  - `python scripts/weekly_digest.py [--dry-run] [--now ISO]` as a script (exit code 2 + `error: ...` on stderr for `ConfigError`).

- [ ] **Step 1: Append the failing tests**

**Append to `tests/test_weekly_digest.py`:**

```python
# --- message, SMTP and CLI -------------------------------------------------


class FakeSMTP:
    instances: list[FakeSMTP] = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.logged_in = None
        self.sent = None
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def login(self, user, password):
        self.logged_in = (user, password)

    def send_message(self, msg, from_addr=None, to_addrs=None):
        self.sent = (msg, from_addr, to_addrs)


@pytest.fixture
def smtp(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr(wd.smtplib, "SMTP_SSL", FakeSMTP)
    return FakeSMTP


def test_build_message_has_headers_and_both_bodies():
    msg = wd.build_message(
        [make_pr()], START, END, REPO, "bot@yandex.ru", ("a@x.ru", "b@y.ru")
    )

    assert msg["Subject"] == "Сводка linguist-prompts: 13.09.2026–20.09.2026"
    assert msg["From"] == "bot@yandex.ru"
    assert msg["To"] == "a@x.ru, b@y.ru"
    plain = msg.get_body(preferencelist=("plain",)).get_content()
    html_body = msg.get_body(preferencelist=("html",)).get_content()
    assert "== russian/grammar ==" in plain
    assert "<h3>russian/grammar</h3>" in html_body


def test_send_email_logs_in_over_ssl_and_sends_to_all_recipients(smtp):
    cfg = wd.load_mail_config(GOOD_ENV)
    msg = wd.build_message([], START, END, REPO, cfg.sender, cfg.recipients)

    wd.send_email(msg, cfg)

    [conn] = smtp.instances
    assert (conn.host, conn.port) == ("smtp.yandex.ru", 465)
    assert conn.logged_in == ("bot@yandex.ru", "app-password")
    sent_msg, from_addr, to_addrs = conn.sent
    assert sent_msg is msg
    assert from_addr == "bot@yandex.ru"
    assert list(to_addrs) == ["a@x.ru", "b@y.ru"]


def test_parse_now_defaults_to_current_utc_time():
    before = datetime.now(UTC)
    result = wd.parse_now(None)
    assert before <= result <= datetime.now(UTC)


def test_parse_now_treats_naive_timestamps_as_utc():
    assert wd.parse_now("2026-09-20T18:05:00") == dt(2026, 9, 20, 18, 5)
    assert wd.parse_now("2026-09-20T21:05:00+03:00") == dt(2026, 9, 20, 18, 5)


def test_main_dry_run_prints_digest_and_never_touches_smtp(smtp, capsys):
    env = {"GITHUB_REPOSITORY": REPO}
    api = fake_api({list_path(1): []})

    code = wd.main(["--dry-run", "--now", "2026-09-20T18:05:00+00:00"], env=env, api=api)

    assert code == 0
    out = capsys.readouterr().out
    assert "Сводка linguist-prompts: 13.09.2026–20.09.2026" in out
    assert "За неделю изменений нет." in out
    assert smtp.instances == []


def test_main_sends_email_with_configured_recipients(smtp, capsys):
    env = {"GITHUB_REPOSITORY": REPO, **GOOD_ENV}
    api = fake_api({list_path(1): []})

    code = wd.main(["--now", "2026-09-20T18:05:00+00:00"], env=env, api=api)

    assert code == 0
    [conn] = smtp.instances
    msg, from_addr, to_addrs = conn.sent
    assert msg["Subject"] == "Сводка linguist-prompts: 13.09.2026–20.09.2026"
    assert list(to_addrs) == ["a@x.ru", "b@y.ru"]
    assert "Sent:" in capsys.readouterr().out


def test_main_fails_fast_on_missing_mail_config_before_calling_api(smtp):
    def api(path):
        raise AssertionError("API must not be called when config is invalid")

    with pytest.raises(wd.ConfigError, match="SMTP_HOST"):
        wd.main([], env={"GITHUB_REPOSITORY": REPO}, api=api)
    assert smtp.instances == []


def test_main_requires_github_repository():
    with pytest.raises(wd.ConfigError, match="GITHUB_REPOSITORY"):
        wd.main(["--dry-run"], env={}, api=fake_api({}))


def test_main_requires_github_token_when_no_api_is_injected():
    with pytest.raises(wd.ConfigError, match="GITHUB_TOKEN"):
        wd.main(["--dry-run"], env={"GITHUB_REPOSITORY": REPO})
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `python -m pytest -q`
Expected: the new tests FAIL with `AttributeError: module 'weekly_digest' has no attribute 'build_message'` (or `send_email`, `parse_now`, `main`).

- [ ] **Step 3: Append the implementation**

**Append to `scripts/weekly_digest.py`:**

```python


def build_message(
    prs: list[MergedPR],
    start: datetime,
    end: datetime,
    repo: str,
    sender: str,
    recipients: tuple[str, ...],
) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = digest_subject(repo, start, end)
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(render_text(prs, start, end, repo))
    msg.add_alternative(render_html(prs, start, end, repo), subtype="html")
    return msg


def send_email(msg: EmailMessage, cfg: MailConfig) -> None:
    with smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=30) as smtp:
        smtp.login(cfg.user, cfg.password)
        smtp.send_message(msg, from_addr=cfg.sender, to_addrs=list(cfg.recipients))


def parse_now(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send the weekly linguist-prompts digest."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the digest to stdout instead of emailing it",
    )
    parser.add_argument(
        "--now", help="ISO-8601 timestamp that overrides the clock (for testing)"
    )
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
    env: Mapping[str, str] | None = None,
    api: Api | None = None,
) -> int:
    args = parse_args(argv)
    env = os.environ if env is None else env

    repo = env.get("GITHUB_REPOSITORY")
    if not repo:
        raise ConfigError("Missing required environment variable: GITHUB_REPOSITORY")
    # Validate mail settings first so a misconfigured run fails before any API call.
    mail_cfg = None if args.dry_run else load_mail_config(env)
    if api is None:
        token = env.get("GITHUB_TOKEN")
        if not token:
            raise ConfigError("Missing required environment variable: GITHUB_TOKEN")
        api = make_github_api(token)

    start, end = digest_window(parse_now(args.now))
    prs = collect_merged_prs(api, repo, start, end)

    if mail_cfg is None:
        print(f"[dry run] Subject: {digest_subject(repo, start, end)}\n")
        print(render_text(prs, start, end, repo))
        return 0

    msg = build_message(prs, start, end, repo, mail_cfg.sender, mail_cfg.recipients)
    send_email(msg, mail_cfg)
    print(f"Sent: {msg['Subject']} -> {len(mail_cfg.recipients)} recipient(s)")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        sys.exit(main())
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 5: Smoke-test the script entry point locally (no network, no email)**

Run:
```bash
cd /c/Repositories/linguist-prompts
env -u GITHUB_REPOSITORY python scripts/weekly_digest.py --dry-run; echo "exit=$?"
```
Expected: stderr `error: Missing required environment variable: GITHUB_REPOSITORY` and `exit=2`.

- [ ] **Step 6: Commit**

```bash
git add scripts/weekly_digest.py tests/test_weekly_digest.py
git commit -F - <<'EOF'
feat(digest): build the email, send it over Yandex SMTP, add the CLI

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01F5B6asG3P3jhnXALys1Z6x
EOF
```

---

### Task 6: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/weekly-digest.yml`
- Modify: `tests/test_weekly_digest.py` (append)

**Interfaces:**
- Consumes: the CLI from Task 5 (`python scripts/weekly_digest.py [--dry-run]`) and the six secrets named in Global Constraints.
- Produces: workflow `weekly-digest.yml` (run by name in Task 7 via `gh workflow run weekly-digest.yml -f dry_run=…`).

- [ ] **Step 1: Append a guard test for the workflow's security-critical invariants**

**Append to `tests/test_weekly_digest.py`:**

```python
# --- workflow invariants ---------------------------------------------------

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "weekly-digest.yml"


def test_workflow_keeps_schedule_environment_and_least_privilege():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'cron: "0 18 * * 0"' in text
    assert "environment: digest" in text
    assert "contents: read" in text
    assert "pull-requests: read" in text
    assert "--dry-run" in text
    # Secrets must never be reachable from PR-triggered runs.
    assert "pull_request_target" not in text
    assert "pull_request:" not in text
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest -q tests/test_weekly_digest.py::test_workflow_keeps_schedule_environment_and_least_privilege`
Expected: FAIL with `FileNotFoundError` (the workflow does not exist yet).

- [ ] **Step 3: Create the workflow**

**Create `.github/workflows/weekly-digest.yml`:**

```yaml
name: Weekly digest

on:
  schedule:
    - cron: "0 18 * * 0"
  workflow_dispatch:
    inputs:
      dry_run:
        description: "Print the digest to the log instead of emailing it"
        type: boolean
        default: true

permissions:
  contents: read
  pull-requests: read

concurrency:
  group: weekly-digest
  cancel-in-progress: false

jobs:
  digest:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    environment: digest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Build and send the digest
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
          MAIL_FROM: ${{ secrets.MAIL_FROM }}
          MAIL_TO: ${{ secrets.MAIL_TO }}
          DRY_RUN: ${{ github.event_name == 'workflow_dispatch' && inputs.dry_run }}
        run: |
          if [ "$DRY_RUN" = "true" ]; then
            python scripts/weekly_digest.py --dry-run
          else
            python scripts/weekly_digest.py
          fi
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/weekly-digest.yml tests/test_weekly_digest.py
git commit -F - <<'EOF'
ci: add Sunday weekly-digest workflow with manual dry-run dispatch

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01F5B6asG3P3jhnXALys1Z6x
EOF
```

---

### Task 7: Publish, configure secrets and protection, verify (interactive)

**Run inline with the owner.** Steps 1, 3 and 8 need the owner (credentials, mailbox, collaborator logins). Step 2 is the first outward-facing action: **ask the owner for an explicit "go" before running it.**

**Files:** none (GitHub configuration only).

**Interfaces:**
- Consumes: the committed repo from Tasks 1–6; a Yandex mailbox with an app password; recipient addresses.
- Produces: public repo `DenisBaliuckij/linguist-prompts` with Environment `digest`, branch protection on `main`, a verified dry-run and a verified real test email.

- [ ] **Step 1: Pre-flight checks**

Run:
```bash
cd /c/Repositories/linguist-prompts
python -m pytest -q
git status -sb
git log --oneline
gh auth status
```
Expected: all tests pass; branch `main`, clean tree; 8 commits (spec, plan, Tasks 1–6); `gh` logged in as `DenisBaliuckij`. Check the `Token scopes` line of `gh auth status` contains `workflow`. If it does not, tell the owner to run `! gh auth refresh -s workflow` (pushing a workflow file is rejected without it).

- [ ] **Step 2: Create the public repo and push (ask the owner first)**

Run:
```bash
gh repo create DenisBaliuckij/linguist-prompts --public --source . --remote origin \
  --description "Промпты для лингвистов: совместная работа по языкам и темам" --push
gh repo view DenisBaliuckij/linguist-prompts --json visibility,defaultBranchRef --jq '.visibility + " " + .defaultBranchRef.name'
```
Expected: `PUBLIC main`.

- [ ] **Step 3: Create Environment `digest`, restricted to `main`**

Run:
```bash
gh api -X PUT repos/DenisBaliuckij/linguist-prompts/environments/digest --input - <<'EOF'
{"deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
EOF
gh api -X POST repos/DenisBaliuckij/linguist-prompts/environments/digest/deployment-branch-policies \
  -f name=main -f type=branch
gh api repos/DenisBaliuckij/linguist-prompts/environments/digest/deployment-branch-policies --jq '.branch_policies[].name'
```
Expected: the last command prints `main`.

- [ ] **Step 4: The owner sets the six secrets (needs the Yandex mailbox)**

Prerequisite (owner): a Yandex mailbox with "mail clients" access enabled and an app password of type "Mail". Then the owner types each command with the `!` prefix so values go straight to GitHub and never into the chat (each command prompts for the value):

```
! gh secret set SMTP_HOST -R DenisBaliuckij/linguist-prompts --env digest      # smtp.yandex.ru
! gh secret set SMTP_PORT -R DenisBaliuckij/linguist-prompts --env digest      # 465
! gh secret set SMTP_USER -R DenisBaliuckij/linguist-prompts --env digest      # the Yandex address
! gh secret set SMTP_PASSWORD -R DenisBaliuckij/linguist-prompts --env digest  # the app password
! gh secret set MAIL_FROM -R DenisBaliuckij/linguist-prompts --env digest      # same as SMTP_USER
! gh secret set MAIL_TO -R DenisBaliuckij/linguist-prompts --env digest        # recipient addresses, comma-separated
```

Verify (names only, values are never shown):
```bash
gh secret list -R DenisBaliuckij/linguist-prompts --env digest
```
Expected: the six names `MAIL_FROM MAIL_TO SMTP_HOST SMTP_PASSWORD SMTP_PORT SMTP_USER`.

- [ ] **Step 5: Dry-run dispatch**

Run:
```bash
gh workflow run weekly-digest.yml -R DenisBaliuckij/linguist-prompts --ref main -f dry_run=true
sleep 5
gh run list -R DenisBaliuckij/linguist-prompts --workflow weekly-digest.yml --limit 1
```
Then watch it: `gh run watch -R DenisBaliuckij/linguist-prompts $(gh run list -R DenisBaliuckij/linguist-prompts --workflow weekly-digest.yml --limit 1 --json databaseId --jq '.[0].databaseId') --exit-status`
Expected: run succeeds. Then `gh run view <id> -R DenisBaliuckij/linguist-prompts --log | grep -A6 "dry run"` shows `[dry run] Subject: Сводка linguist-prompts: …` and «За неделю изменений нет.» (the repo has no merged PRs yet).

- [ ] **Step 6: Real dispatch (sends the "no changes" email)**

Run the same dispatch with `-f dry_run=false` and watch it as in Step 5.
Expected: run succeeds; log ends with `Sent: Сводка linguist-prompts: … -> N recipient(s)`. Ask the owner to confirm the email arrived at **every** recipient (check spam folders for every recipient), that the subject and Russian text are correct, and that the HTML renders.

- [ ] **Step 7: Apply merge settings and branch protection (last — irreversible for pushes)**

Run:
```bash
gh api -X PATCH repos/DenisBaliuckij/linguist-prompts \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
  -F delete_branch_on_merge=true --jq '{squash: .allow_squash_merge, merge: .allow_merge_commit, rebase: .allow_rebase_merge, autodelete: .delete_branch_on_merge}'

gh api -X PUT repos/DenisBaliuckij/linguist-prompts/branches/main/protection --input - <<'EOF'
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF

gh api repos/DenisBaliuckij/linguist-prompts/branches/main/protection \
  --jq '{admins: .enforce_admins.enabled, approvals: .required_pull_request_reviews.required_approving_review_count, dismiss_stale: .required_pull_request_reviews.dismiss_stale_reviews, force_push: .allow_force_pushes.enabled, deletions: .allow_deletions.enabled}'
```
Expected: first output `{"squash":true,"merge":false,"rebase":false,"autodelete":true}`; last output `{"admins":true,"approvals":1,"dismiss_stale":true,"force_push":false,"deletions":false}`.

- [ ] **Step 8: Invite collaborators and hand over**

Ask the owner for the GitHub logins of the linguists, then for each login:
```bash
gh api -X PUT repos/DenisBaliuckij/linguist-prompts/collaborators/<login> -f permission=push
```
Expected: HTTP 201 (invitation sent). Tell the owner:
- The first PR they open will be blocked from merging until a second collaborator approves it (admin enforcement, no bypass).
- To change the workflow or script before a second collaborator exists, temporarily run `gh api -X DELETE repos/DenisBaliuckij/linguist-prompts/branches/main/protection/enforce_admins`, make the change, then re-enable with `gh api -X POST repos/DenisBaliuckij/linguist-prompts/branches/main/protection/enforce_admins`.
- After the first real merged PR, run a `dry_run=true` dispatch to eyeball a non-empty digest before the first Sunday send.
- Delete the leftover `C:\Repositories\linguist-prompts\.git.corrupt-backup` folder when convenient.

---

## Self-Review

**Spec coverage**

| Spec section | Task |
|---|---|
| Repo layout (README, CONTRIBUTING, LICENSE, seed subject, PR template) | 1 |
| Window (Sunday 18:00 UTC anchor, half-open, `--now`) | 2 (`digest_window`), 5 (`--now`) |
| Data collection (pagination, files, approvers, grouping, statuses) | 2 (`group_key`, `approvers_from_reviews`), 3 |
| Email (multipart, subject, totals, per-group blocks, empty week, `MAIL_TO` parsing, dry-run) | 2 (`parse_mail_to`), 4, 5 |
| Errors (fail loudly, no swallowing) | 2 (`ConfigError`), 5 (`main`, exit 2); API/SMTP exceptions propagate |
| Trigger/workflow (cron, dispatch `dry_run`, permissions, environment, timeout) | 6 |
| Secrets in Environment `digest` restricted to `main` | 7 (Steps 3–4) |
| Branch protection, squash-only, auto-delete, admin enforcement, escape hatch | 7 (Steps 7–8) |
| Testing (window, edges, grouping, approvers, rendering, escaping, parsing) | 2–5 |
| Acceptance (dry-run then real dispatch to both recipients) | 7 (Steps 5–6) |
| Bootstrap order (protection last) | Global Constraints, 7 |
| Known limitations (60-day disable) | 1 (README) |

**Placeholder scan:** no TBD/TODO; every code step contains the full code; the only runtime inputs are the owner's secret values and collaborator logins, which are supplied interactively by design.

**Type consistency:** `FileChange`, `MergedPR`, `MailConfig`, `Api`, `GroupEntry` are defined once (Tasks 2–4) and used with the same field names everywhere; `build_message(prs, start, end, repo, sender, recipients)` and `send_email(msg, cfg)` match their call sites in `main`; test helpers `review`, `pr_json`, `fake_api`, `list_path`, `make_pr`, `GOOD_ENV` are defined before use in file order.
