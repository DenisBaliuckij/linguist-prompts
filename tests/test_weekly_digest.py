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
