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
                author=(pr.get("user") or {}).get("login", "ghost"),
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
        try:
            refused = smtp.send_message(
                msg, from_addr=cfg.sender, to_addrs=list(cfg.recipients)
            )
        except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused):
            raise RuntimeError(
                "SMTP server refused the sender or all recipients; "
                "check MAIL_FROM and MAIL_TO"
            ) from None
    if refused:
        raise RuntimeError(
            f"SMTP server refused {len(refused)} of {len(cfg.recipients)} "
            "recipients; check MAIL_TO"
        )


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
