"""Weekly digest of merged pull requests, posted as a GitHub issue in Russian.

Stdlib only. Run by .github/workflows/weekly-digest.yml every Sunday 18:00 UTC.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

GITHUB_API = "https://api.github.com"
OTHER_GROUP = "Прочее"
DIGEST_WEEKDAY = 6  # Sunday, as returned by datetime.weekday()
DIGEST_HOUR_UTC = 18

DIGEST_LABEL = "digest"

_GROUP_RE = re.compile(r"^languages/([^/]+)/([^/]+)/")
_LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_REPO_RE = re.compile(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+")
_GITHUB_URL_RE = re.compile(r"https://github\.com/[A-Za-z0-9._~%/-]+")
_MD_SPECIAL_RE = re.compile(r"[\\`*_\[\]<>()#~|!]")
_WWW_RE = re.compile(r"(www)\.", re.IGNORECASE)
_ZWSP = "\u200b"


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


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


def parse_notify(value: str) -> tuple[str, ...]:
    """Split DIGEST_NOTIFY into unique, validated GitHub logins (no leading @)."""
    logins: list[str] = []
    for part in re.split(r"[\s,;]+", value):
        login = part.removeprefix("@")
        if not login:
            continue
        if not _LOGIN_RE.fullmatch(login):
            raise ConfigError("DIGEST_NOTIFY contains an invalid GitHub login")
        if login not in logins:
            logins.append(login)
    return tuple(logins)


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


Poster = Callable[[str, dict[str, Any]], Any]


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "linguist-prompts-weekly-digest",
    }


def make_github_api(token: str) -> Api:
    def api(path: str) -> Any:
        request = urllib.request.Request(
            GITHUB_API + path, headers=_github_headers(token)
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    return api


def make_github_poster(token: str) -> Poster:
    def post(path: str, payload: dict[str, Any]) -> Any:
        request = urllib.request.Request(
            GITHUB_API + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={**_github_headers(token), "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    return post


def create_issue(
    post: Poster,
    repo: str,
    title: str,
    body: str,
    labels: tuple[str, ...] = (DIGEST_LABEL,),
) -> dict[str, Any]:
    return post(
        f"/repos/{repo}/issues",
        {"title": title, "body": body, "labels": list(labels)},
    )


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


def md_text(value: str) -> str:
    """Make untrusted plain text safe to embed in Markdown.

    The result renders as the original text but can neither ping anyone, nor
    cross-reference an issue, nor inject HTML, an image or a link.
    """
    value = re.sub(r"[\r\n\t]+", " ", value)
    value = value.replace("&", "&amp;")
    value = _MD_SPECIAL_RE.sub(lambda m: "\\" + m[0], value)
    value = value.replace("@", "@" + _ZWSP)
    value = value.replace("://", ":" + _ZWSP + "//")
    return _WWW_RE.sub(lambda m: m[1] + _ZWSP + ".", value)


def md_code(value: str) -> str:
    """Wrap untrusted text in a Markdown code span that it cannot break out of."""
    return "`" + re.sub(r"[\r\n\t]+", " ", value).replace("`", "'") + "`"


def _md_login(login: str) -> str:
    if _LOGIN_RE.fullmatch(login):
        return f"[{login}](https://github.com/{login})"
    return md_text(login)


def _md_link(text: str, url: str) -> str:
    if _GITHUB_URL_RE.fullmatch(url):
        return f"[{text}]({url})"
    return text


def _approvers_markdown(pr: MergedPR) -> str:
    return ", ".join(_md_login(login) for login in pr.approvers) or "—"


def render_markdown(
    prs: list[MergedPR],
    start: datetime,
    end: datetime,
    repo: str,
    notify: tuple[str, ...] = (),
) -> str:
    """Render the digest as the Markdown body of a GitHub issue.

    The `Для: @login ...` line is the only place a real @mention is emitted,
    and only for logins that pass validation. Everything derived from pull
    requests (titles, logins, paths, group keys) is escaped.
    """
    lines: list[str] = []
    if notify:
        if not all(_LOGIN_RE.fullmatch(login) for login in notify):
            raise ConfigError("DIGEST_NOTIFY contains an invalid GitHub login")
        lines += ["Для: " + " ".join(f"@{login}" for login in notify), ""]
    if _REPO_RE.fullmatch(repo):
        repo_text = _md_link("репозиторий", f"https://github.com/{repo}")
    else:
        repo_text = md_text(repo)
    lines.append(
        f"**Период:** {_fmt_datetime(start)} – {_fmt_datetime(end)} (UTC)"
        f" · {repo_text}"
    )
    lines.append("")
    if not prs:
        lines.append("За неделю изменений нет.")
        return "\n".join(lines) + "\n"
    lines.append(_totals_sentence(prs).replace("Всего:", "**Всего:**", 1))
    for key, entries in group_prs(prs):
        lines += ["", f"### {md_text(key)}"]
        for pr, changes in entries:
            heading = md_text(f"#{pr.number} {pr.title}")
            lines.append(f"- {_md_link(heading, pr.url)}")
            lines.append(
                f"  Автор: {_md_login(pr.author)} · Одобрили: {_approvers_markdown(pr)}"
                f" · Слит: {_fmt_date(pr.merged_at)}"
            )
            for change in changes:
                lines.append(
                    f"    - {STATUS_LABELS[change.status]}: {md_code(change.path)}"
                )
    return "\n".join(lines) + "\n"


def parse_now(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Post the weekly linguist-prompts digest as a GitHub issue."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the digest to stdout instead of posting the issue",
    )
    parser.add_argument(
        "--now", help="ISO-8601 timestamp that overrides the clock (for testing)"
    )
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
    env: Mapping[str, str] | None = None,
    api: Api | None = None,
    post: Poster | None = None,
) -> int:
    args = parse_args(argv)
    env = os.environ if env is None else env

    repo = env.get("GITHUB_REPOSITORY")
    if not repo:
        raise ConfigError("Missing required environment variable: GITHUB_REPOSITORY")
    # Validate all configuration first so a misconfigured run fails before any
    # network call.
    notify = parse_notify(env.get("DIGEST_NOTIFY", ""))
    token = env.get("GITHUB_TOKEN")
    needs_token = api is None or (post is None and not args.dry_run)
    if needs_token and not token:
        raise ConfigError("Missing required environment variable: GITHUB_TOKEN")
    if api is None:
        api = make_github_api(token)
    if post is None and not args.dry_run:
        post = make_github_poster(token)

    start, end = digest_window(parse_now(args.now))
    prs = collect_merged_prs(api, repo, start, end)
    title = digest_subject(repo, start, end)
    body = render_markdown(prs, start, end, repo, notify)

    if args.dry_run:
        print(f"[dry run] Title: {title}\n")
        print(body, end="")
        return 0

    issue = create_issue(post, repo, title, body)
    print(f"Posted: {issue.get('html_url', '(no URL in the response)')}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        sys.exit(main())
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
