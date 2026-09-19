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
