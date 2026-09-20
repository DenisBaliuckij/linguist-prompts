"""Tests for scripts/weekly_digest.py - no network, fixture data only."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
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


# --- parse_notify ----------------------------------------------------------


def test_parse_notify_splits_on_whitespace_commas_and_semicolons():
    assert wd.parse_notify("alice bob,carol;dave\n eve\t,;frank") == (
        "alice",
        "bob",
        "carol",
        "dave",
        "eve",
        "frank",
    )


def test_parse_notify_strips_one_leading_at_sign():
    assert wd.parse_notify("@alice, @bob-1 carol") == ("alice", "bob-1", "carol")


def test_parse_notify_removes_duplicates_keeping_first_position():
    assert wd.parse_notify("bob @alice, alice;bob carol") == ("bob", "alice", "carol")


@pytest.mark.parametrize("value", ["", "   ", " ; , ", "@", " @ ; @ "])
def test_parse_notify_empty_means_nobody(value):
    assert wd.parse_notify(value) == ()


def test_parse_notify_accepts_the_longest_valid_login():
    assert wd.parse_notify("a" * 39) == ("a" * 39,)


@pytest.mark.parametrize(
    "bad",
    [
        "ali_ce",
        "-alice",
        "alice/bob",
        "@@alice",
        "bob[bot]",
        "alice.smith",
        "a" * 40,
        "\u0430lice",  # Cyrillic a
        "ali\u200bce",  # zero-width space
        "alice\u00e9",
    ],
)
def test_parse_notify_rejects_invalid_logins_without_echoing_them(bad):
    with pytest.raises(wd.ConfigError) as exc:
        wd.parse_notify(f"carol {bad}")
    assert str(exc.value) == "DIGEST_NOTIFY contains an invalid GitHub login"
    assert bad not in str(exc.value)
    assert "carol" not in str(exc.value)


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


def test_collect_merged_prs_tolerates_null_user():
    pr = pr_json(7, "2026-09-15T10:00:00Z")
    pr["user"] = None
    routes = {
        list_path(1): [pr],
        files_path(7): [file_json("README.md")],
        reviews_path(7): [],
    }

    prs = wd.collect_merged_prs(fake_api(routes), REPO, START, END)

    assert prs[0].author == "ghost"


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


# --- Markdown escaping -----------------------------------------------------

ZW = "\u200b"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("plain текст 123", "plain текст 123"),
        ("a\nb\t\tc\r\nd", "a b c d"),
        ("a & b", "a &amp; b"),
        ("&#64;x &lt;b&gt;", "&amp;\\#64;x &amp;lt;b&amp;gt;"),
        (
            "\\ ` * _ [ ] < > ( ) # ~ | !",
            "\\\\ \\` \\* \\_ \\[ \\] \\< \\> \\( \\) \\# \\~ \\| \\!",
        ),
        ("@everyone", f"@{ZW}everyone"),
        ("a@b.example", f"a@{ZW}b.example"),
        ("http://evil.example", f"http:{ZW}//evil.example"),
        ("www.evil.example WWW.EVIL.EXAMPLE", f"www{ZW}.evil.example WWW{ZW}.EVIL.EXAMPLE"),
    ],
)
def test_md_text(raw, expected):
    assert wd.md_text(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("languages/a/b.md", "`languages/a/b.md`"),
        ("a`b``c", "`a'b''c`"),
        ("a\nb\r\nc\td", "`a b c d`"),
        ("@x <y> #1 [z](u)", "`@x <y> #1 [z](u)`"),
    ],
)
def test_md_code(raw, expected):
    assert wd.md_code(raw) == expected


# --- render_markdown -------------------------------------------------------

REPO_LINK = f"[репозиторий](https://github.com/{REPO})"
PERIOD_LINE = f"**Период:** 13.09.2026 18:00 – 20.09.2026 18:00 (UTC) · {REPO_LINK}"


def test_render_markdown_normal_week_exact_layout():
    body = wd.render_markdown([make_pr()], START, END, REPO)

    assert body == (
        f"{PERIOD_LINE}\n"
        "\n"
        "**Всего:** 1 слитый PR, 1 участник, 1 изменённый файл.\n"
        "\n"
        "### russian/grammar\n"
        f"- [\\#12 Добавить примеры падежей](https://github.com/{REPO}/pull/12)\n"
        "  Автор: [alice](https://github.com/alice)"
        " · Одобрили: [bob](https://github.com/bob) · Слит: 15.09.2026\n"
        "    - добавлен: `languages/russian/grammar/prompts.md`\n"
    )


def test_render_markdown_lists_every_approver_as_a_link():
    body = wd.render_markdown([make_pr(approvers=("bob", "carol"))], START, END, REPO)
    assert (
        "Одобрили: [bob](https://github.com/bob), [carol](https://github.com/carol)"
        " · Слит:"
    ) in body


def test_render_markdown_multiple_groups_in_order_with_other_last():
    pr = make_pr(
        files=[
            wd.FileChange("languages/russian/grammar/prompts.md", "modified"),
            wd.FileChange("languages/english/idioms/prompts.md", "added"),
            wd.FileChange("README.md", "modified"),
        ]
    )

    body = wd.render_markdown([pr], START, END, REPO)

    assert (
        body.index("### english/idioms")
        < body.index("### russian/grammar")
        < body.index("### Прочее")
    )
    assert "**Всего:** 1 слитый PR, 1 участник, 3 изменённых файла." in body
    assert "    - изменён: `languages/russian/grammar/prompts.md`" in body
    assert "    - добавлен: `languages/english/idioms/prompts.md`" in body
    assert "    - изменён: `README.md`" in body


def test_render_markdown_lists_prs_of_a_group_in_given_order():
    prs = [make_pr(number=3), make_pr(number=1)]
    body = wd.render_markdown(prs, START, END, REPO)
    assert body.index("\\#3 ") < body.index("\\#1 ")
    assert body.count("### russian/grammar") == 1


def test_render_markdown_totals_count_unique_authors_and_files():
    prs = [make_pr(number=1), make_pr(number=2)]  # same author, same file
    body = wd.render_markdown(prs, START, END, REPO)
    assert "**Всего:** 2 слитых PR, 1 участник, 1 изменённый файл." in body


@pytest.mark.parametrize(
    "count, expected",
    [
        (1, "1 слитый PR, 1 участник, 1 изменённый файл."),
        (2, "2 слитых PR, 2 участника, 2 изменённых файла."),
        (5, "5 слитых PR, 5 участников, 5 изменённых файлов."),
        (21, "21 слитый PR, 21 участник, 21 изменённый файл."),
    ],
)
def test_render_markdown_totals_use_russian_plurals(count, expected):
    prs = [
        make_pr(
            number=i + 1,
            author=f"user{i}",
            files=[wd.FileChange(f"README{i}.md", "modified")],
        )
        for i in range(count)
    ]
    body = wd.render_markdown(prs, START, END, REPO)
    assert f"**Всего:** {expected}" in body


def test_render_markdown_without_approvers_shows_dash():
    body = wd.render_markdown([make_pr(approvers=())], START, END, REPO)
    assert "Одобрили: — · Слит: 15.09.2026" in body


def test_render_markdown_pr_without_files_is_still_listed():
    body = wd.render_markdown([make_pr(files=[])], START, END, REPO)
    assert body.endswith(
        "### Прочее\n"
        f"- [\\#12 Добавить примеры падежей](https://github.com/{REPO}/pull/12)\n"
        "  Автор: [alice](https://github.com/alice)"
        " · Одобрили: [bob](https://github.com/bob) · Слит: 15.09.2026\n"
    )


def test_render_markdown_empty_week():
    body = wd.render_markdown([], START, END, REPO)
    assert body == f"{PERIOD_LINE}\n\nЗа неделю изменений нет.\n"
    assert "Всего" not in body


def test_render_markdown_has_no_mention_line_without_notify():
    body = wd.render_markdown([make_pr()], START, END, REPO)
    assert body.startswith("**Период:**")
    assert "Для:" not in body
    assert "@" not in body, "logins must be linked, never @mentioned"


def test_render_markdown_mention_line_is_first_and_only_place_with_at_signs():
    body = wd.render_markdown(
        [make_pr()], START, END, REPO, notify=("carol", "dave-1")
    )
    lines = body.split("\n")
    assert lines[0] == "Для: @carol @dave-1"
    assert lines[1] == ""
    assert lines[2].startswith("**Период:**")
    assert "@" not in "\n".join(lines[1:])
    assert body.count("@") == 2


def test_render_markdown_mention_line_on_empty_week():
    body = wd.render_markdown([], START, END, REPO, notify=("carol",))
    assert body == f"Для: @carol\n\n{PERIOD_LINE}\n\nЗа неделю изменений нет.\n"


@pytest.mark.parametrize(
    "bad", ["everyone\n@here", "bad login", "a" * 40, "@carol", "carol]", ""]
)
def test_render_markdown_rejects_unvalidated_notify_logins(bad):
    with pytest.raises(wd.ConfigError):
        wd.render_markdown([], START, END, REPO, notify=("carol", bad))


# --- render_markdown: untrusted text ---------------------------------------

HOSTILE_TITLE = (
    "@everyone #123 [x](http://evil.example) <img src=x> a_b*c `tick` "
    "www.evil.example"
)
HOSTILE_AUTHOR = "eve) [pwn](http://evil.example) @everyone"
HOSTILE_APPROVER = "bob\n@everyone <b>"
HOSTILE_GROUPED_PATH = "languages/@team/#7 <b>@all/prompts.md"
HOSTILE_OTHER_PATH = "docs/a`b@everyone <img src=x> #9.md"


def strip_code_spans(text: str) -> str:
    return re.sub(r"(?<!\\)`[^`\n]*`", "", text)


@pytest.fixture
def hostile_body():
    pr = make_pr(
        number=12,
        title=HOSTILE_TITLE,
        author=HOSTILE_AUTHOR,
        approvers=("carol", HOSTILE_APPROVER),
        files=[
            wd.FileChange(HOSTILE_GROUPED_PATH, "added"),
            wd.FileChange(HOSTILE_OTHER_PATH, "modified"),
        ],
    )
    return wd.render_markdown([pr], START, END, REPO, notify=("carol", "dave"))


def test_hostile_mention_line_is_the_only_line_with_a_live_mention(hostile_body):
    lines = hostile_body.split("\n")
    assert lines[0] == "Для: @carol @dave"
    rest = strip_code_spans("\n".join(lines[1:]))
    assert not re.search(r"@\w", rest), "live @mention outside the first line"
    assert "@" + ZW + "everyone" in rest, "@ in untrusted text must be neutralised"


def test_hostile_title_is_escaped_completely(hostile_body):
    expected = (
        f"\\#12 @{ZW}everyone \\#123 \\[x\\]\\(http:{ZW}//evil.example\\) "
        f"\\<img src=x\\> a\\_b\\*c \\`tick\\` www{ZW}.evil.example"
    )
    assert f"- [{expected}](https://github.com/{REPO}/pull/12)\n" in hostile_body, (
        "PR title was not escaped"
    )


def test_hostile_text_creates_no_cross_reference(hostile_body):
    rest = strip_code_spans(hostile_body)
    assert not re.search(r"(?<!\\)#\d", rest), "unescaped #<number> reference"


def test_hostile_text_creates_no_html(hostile_body):
    rest = strip_code_spans(hostile_body)
    assert not re.search(r"(?<!\\)<", rest), "raw '<' outside a code span"
    assert not re.search(r"(?<!\\)!\[", rest), "image syntax outside a code span"


def test_hostile_text_creates_no_unintended_links(hostile_body):
    destinations = re.findall(r"(?<!\\)\]\(([^)]*)\)", hostile_body)
    # The PR touches two groups, so it (and its valid approver) is listed twice.
    assert sorted(destinations) == sorted(
        [
            f"https://github.com/{REPO}",
            f"https://github.com/{REPO}/pull/12",
            f"https://github.com/{REPO}/pull/12",
            "https://github.com/carol",
            "https://github.com/carol",
        ]
    ), "unexpected link destinations"
    assert hostile_body.count("://") == len(destinations), (
        "a URL is left in a form that autolinks"
    )
    assert "http://" not in hostile_body.replace(f"http:{ZW}//", "")
    assert not re.search(r"(?i)www\.", hostile_body), "www. autolink not neutralised"


def test_hostile_author_is_escaped_and_not_linked(hostile_body):
    assert (
        f"Автор: eve\\) \\[pwn\\]\\(http:{ZW}//evil.example\\) @{ZW}everyone ·"
        in hostile_body
    ), "author login was not escaped"


def test_hostile_approver_is_escaped_and_valid_approver_is_linked(hostile_body):
    assert (
        f"Одобрили: [carol](https://github.com/carol), bob @{ZW}everyone \\<b\\> ·"
        in hostile_body
    ), "approver login was not escaped"


def test_hostile_group_key_heading_is_escaped(hostile_body):
    assert f"\n### @{ZW}team/\\#7 \\<b\\>@{ZW}all\n" in hostile_body, (
        "group key heading was not escaped"
    )
    assert "\n### Прочее\n" in hostile_body


def test_hostile_file_paths_stay_inside_code_spans(hostile_body):
    assert f"\n    - добавлен: `{HOSTILE_GROUPED_PATH}`\n" in hostile_body, (
        "grouped path is not a plain code span"
    )
    assert "\n    - изменён: `docs/a'b@everyone <img src=x> #9.md`\n" in hostile_body, (
        "backtick in a path must not end the code span"
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/pull/12",
        "http://github.com/acme/linguist-prompts/pull/12",
        "https://github.com.evil.example/pull/12",
        "https://github.com/x/pull/1) [p](http://evil.example)",
        "https://github.com/x/pull/1 title",
        "https://github.com/x/pull/1\n@everyone",
        "https://github.com/x/<b>",
        "javascript:alert(1)",
        "",
    ],
)
def test_pr_url_outside_github_is_not_linked(url):
    pr = make_pr()
    pr = wd.MergedPR(**{**pr.__dict__, "url": url})

    body = wd.render_markdown([pr], START, END, REPO)

    assert "- \\#12 Добавить примеры падежей\n" in body, "PR must render as plain text"
    assert re.findall(r"(?<!\\)\]\(([^)]*)\)", body) == [
        f"https://github.com/{REPO}",
        "https://github.com/alice",
        "https://github.com/bob",
    ]
    assert "evil" not in body


@pytest.mark.parametrize(
    "login",
    ["bob[bot]", "-x", "a_b", "x" * 40, "x\n", "x y", "ali\u200bce"],
)
def test_invalid_logins_are_rendered_unlinked(login):
    body = wd.render_markdown([make_pr(author=login, approvers=())], START, END, REPO)
    assert "https://github.com/" + login not in body
    assert f"Автор: {wd.md_text(login)} ·" in body
    assert body.count("https://github.com/") == 2  # repo link and PR link only


@pytest.mark.parametrize(
    "repo", ["a/b) [x](http://evil.example)", "a b/c", "just-a-name"]
)
def test_odd_repository_value_is_not_linked(repo):
    body = wd.render_markdown([], START, END, repo)
    assert "](" not in body
    assert "http://" not in body


# --- issue delivery --------------------------------------------------------


class FakeHTTPResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, *args):
        return self.payload


def fake_poster(response=None):
    calls = []

    def post(path, payload):
        calls.append((path, payload))
        return (
            {"html_url": f"https://github.com/{REPO}/issues/7", "number": 7}
            if response is None
            else response
        )

    post.calls = calls
    return post


def test_create_issue_posts_title_body_and_default_label():
    post = fake_poster()

    issue = wd.create_issue(post, REPO, "Заголовок", "Тело\n")

    assert post.calls == [
        (
            f"/repos/{REPO}/issues",
            {"title": "Заголовок", "body": "Тело\n", "labels": ["digest"]},
        )
    ]
    assert issue == {"html_url": f"https://github.com/{REPO}/issues/7", "number": 7}


def test_create_issue_accepts_custom_labels():
    post = fake_poster()
    wd.create_issue(post, REPO, "t", "b", labels=("digest", "weekly"))
    assert post.calls[0][1]["labels"] == ["digest", "weekly"]


def test_make_github_poster_posts_json_with_auth_and_parses_response(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout=None):
        seen["url"] = request.full_url
        seen["method"] = request.get_method()
        seen["data"] = request.data
        seen["headers"] = {k.lower(): v for k, v in request.header_items()}
        seen["timeout"] = timeout
        return FakeHTTPResponse(b'{"html_url": "https://github.com/a/b/issues/1"}')

    monkeypatch.setattr(wd.urllib.request, "urlopen", fake_urlopen)
    payload = {"title": "Сводка", "body": "тело", "labels": ["digest"]}

    result = wd.make_github_poster("tok")("/repos/a/b/issues", payload)

    assert result == {"html_url": "https://github.com/a/b/issues/1"}
    assert seen["url"] == "https://api.github.com/repos/a/b/issues"
    assert seen["method"] == "POST"
    assert isinstance(seen["data"], bytes)
    assert json.loads(seen["data"].decode("utf-8")) == payload
    assert seen["timeout"] == 30
    headers = seen["headers"]
    assert headers["content-type"] == "application/json"
    assert headers["authorization"] == "Bearer tok"
    assert headers["accept"] == "application/vnd.github+json"
    assert headers["x-github-api-version"] == "2022-11-28"
    assert headers["user-agent"] == "linguist-prompts-weekly-digest"


def test_make_github_poster_lets_http_errors_propagate(monkeypatch):
    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(wd.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(urllib.error.HTTPError):
        wd.make_github_poster("tok")("/repos/a/b/issues", {})


def test_parse_now_defaults_to_current_utc_time():
    before = datetime.now(UTC)
    result = wd.parse_now(None)
    assert before <= result <= datetime.now(UTC)


def test_parse_now_treats_naive_timestamps_as_utc():
    assert wd.parse_now("2026-09-20T18:05:00") == dt(2026, 9, 20, 18, 5)
    assert wd.parse_now("2026-09-20T21:05:00+03:00") == dt(2026, 9, 20, 18, 5)


# --- CLI -------------------------------------------------------------------

NOW = "2026-09-20T18:05:00+00:00"
TITLE = "Сводка linguist-prompts: 13.09.2026–20.09.2026"
SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "weekly_digest.py"


def week_api():
    return fake_api(
        {
            list_path(1): [pr_json(12, "2026-09-15T10:00:00Z")],
            files_path(12): [
                file_json("languages/russian/grammar/prompts.md", "added")
            ],
            reviews_path(12): [review("bob", "APPROVED", "2026-09-15T09:00:00Z")],
        }
    )


def forbidden_api(path):
    raise AssertionError(f"the API must not be called, got {path}")


def test_main_dry_run_prints_title_and_body_and_never_posts(capsys):
    env = {"GITHUB_REPOSITORY": REPO, "DIGEST_NOTIFY": "@carol"}
    post = fake_poster()

    code = wd.main(["--dry-run", "--now", NOW], env=env, api=week_api(), post=post)

    assert code == 0
    body = wd.render_markdown(
        [make_pr(number=12, title="PR 12", approvers=("bob",))],
        START,
        END,
        REPO,
        notify=("carol",),
    )
    assert capsys.readouterr().out == f"[dry run] Title: {TITLE}\n\n{body}"
    assert body.startswith("Для: @carol\n\n**Период:**")
    assert post.calls == []


def test_main_dry_run_needs_no_token_when_api_is_injected(capsys):
    code = wd.main(
        ["--dry-run", "--now", NOW],
        env={"GITHUB_REPOSITORY": REPO},
        api=fake_api({list_path(1): []}),
    )
    assert code == 0
    assert "За неделю изменений нет." in capsys.readouterr().out


def test_main_posts_exactly_one_issue_with_title_label_and_body(capsys):
    env = {"GITHUB_REPOSITORY": REPO, "DIGEST_NOTIFY": "carol, @dave"}
    post = fake_poster()

    code = wd.main(["--now", NOW], env=env, api=week_api(), post=post)

    assert code == 0
    [(path, payload)] = post.calls
    assert path == f"/repos/{REPO}/issues"
    assert payload["title"] == TITLE
    assert payload["labels"] == ["digest"]
    assert set(payload) == {"title", "body", "labels"}
    body = payload["body"]
    assert body.split("\n")[0] == "Для: @carol @dave"
    assert f"[\\#12 PR 12](https://github.com/{REPO}/pull/12)" in body
    assert "**Всего:** 1 слитый PR, 1 участник, 1 изменённый файл." in body
    assert f"Posted: https://github.com/{REPO}/issues/7" in capsys.readouterr().out


def test_main_posts_an_issue_for_an_empty_week_without_mention_line():
    env = {"GITHUB_REPOSITORY": REPO}
    post = fake_poster()

    code = wd.main(["--now", NOW], env=env, api=fake_api({list_path(1): []}), post=post)

    assert code == 0
    [(_, payload)] = post.calls
    assert payload["title"] == TITLE
    assert payload["body"] == f"{PERIOD_LINE}\n\nЗа неделю изменений нет.\n"


def test_main_requires_github_repository():
    with pytest.raises(wd.ConfigError, match="GITHUB_REPOSITORY"):
        wd.main(["--dry-run"], env={}, api=forbidden_api)


def test_main_requires_github_token_when_no_api_is_injected():
    with pytest.raises(wd.ConfigError, match="GITHUB_TOKEN"):
        wd.main(["--dry-run"], env={"GITHUB_REPOSITORY": REPO})


def test_main_fails_before_any_api_call_when_posting_without_a_token():
    with pytest.raises(wd.ConfigError, match="GITHUB_TOKEN"):
        wd.main(["--now", NOW], env={"GITHUB_REPOSITORY": REPO}, api=forbidden_api)


@pytest.mark.parametrize("dry_run", [True, False])
@pytest.mark.parametrize("notify", ["bad_login", "carol @@dave", "carol,-x"])
def test_main_fails_fast_on_invalid_notify_before_any_network_call(dry_run, notify):
    env = {"GITHUB_REPOSITORY": REPO, "DIGEST_NOTIFY": notify}
    post = fake_poster()
    argv = ["--now", NOW] + (["--dry-run"] if dry_run else [])

    with pytest.raises(wd.ConfigError, match="DIGEST_NOTIFY"):
        wd.main(argv, env=env, api=forbidden_api, post=post)

    assert post.calls == []


def test_main_with_default_clients_uses_token_and_never_prints_it(monkeypatch, capsys):
    token = "ghs_SECRET_TOKEN_VALUE"
    requests = []

    def fake_urlopen(request, timeout=None):
        requests.append(request)
        if request.get_method() == "POST":
            return FakeHTTPResponse(
                b'{"html_url": "https://github.com/acme/linguist-prompts/issues/9"}'
            )
        return FakeHTTPResponse(b"[]")

    monkeypatch.setattr(wd.urllib.request, "urlopen", fake_urlopen)
    env = {
        "GITHUB_REPOSITORY": REPO,
        "GITHUB_TOKEN": token,
        "DIGEST_NOTIFY": "carol",
    }

    code = wd.main(["--now", NOW], env=env)

    assert code == 0
    assert [r.get_method() for r in requests] == ["GET", "POST"]
    assert requests[1].full_url == f"https://api.github.com/repos/{REPO}/issues"
    assert all(r.get_header("Authorization") == f"Bearer {token}" for r in requests)
    sent = json.loads(requests[1].data.decode("utf-8"))
    assert sent["title"] == TITLE
    assert sent["labels"] == ["digest"]
    assert sent["body"].startswith("Для: @carol\n\n")
    captured = capsys.readouterr()
    assert "Posted: https://github.com/acme/linguist-prompts/issues/9" in captured.out
    assert token not in captured.out + captured.err
    assert token not in sent["body"]


def test_main_output_never_contains_the_token_in_dry_run(capsys):
    token = "ghs_SECRET_TOKEN_VALUE"
    env = {"GITHUB_REPOSITORY": REPO, "GITHUB_TOKEN": token}

    wd.main(["--dry-run", "--now", NOW], env=env, api=week_api())

    captured = capsys.readouterr()
    assert token not in captured.out + captured.err


def test_main_lets_post_failures_propagate():
    def failing_post(path, payload):
        raise urllib.error.HTTPError(path, 403, "Forbidden", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        wd.main(
            ["--now", NOW],
            env={"GITHUB_REPOSITORY": REPO},
            api=fake_api({list_path(1): []}),
            post=failing_post,
        )


def test_script_exits_with_2_and_error_line_on_config_error():
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("GITHUB_REPOSITORY", "GITHUB_TOKEN", "DIGEST_NOTIFY")
    }

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )

    assert result.returncode == 2
    assert result.stderr.startswith("error: ")
    assert "GITHUB_REPOSITORY" in result.stderr


# --- workflow invariants ---------------------------------------------------

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "weekly-digest.yml"


def workflow_problems(text: str) -> list[str]:
    """Check workflow structural invariants. Return list of problem strings (empty = all good)."""
    # Strip full-line comments
    lines = text.split("\n")
    content_lines = [
        line for line in lines if not line.strip().startswith("#")
    ]
    content = "\n".join(content_lines)

    problems = []

    # Check: on: block exists and has only schedule and workflow_dispatch triggers
    if not re.search(r"^on:\s*$", content, re.MULTILINE):
        problems.append("on: block not found")
    else:
        # Extract section from on: until next top-level key (no indent)
        on_section = re.search(
            r"^on:\s*\n((?:(?!^\S).*\n)*)",
            content, re.MULTILINE
        )
        if on_section:
            on_block = on_section.group(1)
            # Find all trigger keys (2-space indent + word + colon)
            triggers = set(
                re.findall(r"^  (\w+):", on_block, re.MULTILINE)
            )
            if triggers != {"schedule", "workflow_dispatch"}:
                problems.append(
                    f"Triggers must be exactly schedule and workflow_dispatch, got: {triggers}"
                )

    # Check: cron line at correct indent
    if not re.search(r"^    - cron: \"0 18 \* \* 0\"$", content, re.MULTILINE):
        problems.append('Cron line must be "    - cron: "0 18 * * 0""')

    # Check: dry_run input has type: boolean and default: true
    dry_run_section = re.search(
        r"^      dry_run:\n((?:        \w+:.*\n)*)",
        content, re.MULTILINE
    )
    if dry_run_section:
        dry_run_block = dry_run_section.group(1)
        if "type: boolean" not in dry_run_block:
            problems.append("dry_run input must have type: boolean")
        if "default: true" not in dry_run_block:
            problems.append("dry_run input must have default: true")
    else:
        problems.append("dry_run input block not found")

    # Check: top-level permissions block is exactly contents: read,
    # pull-requests: read and issues: write
    if not re.search(r"^permissions:\s*$", content, re.MULTILINE):
        problems.append("Top-level permissions: block not found")
    else:
        perms_section = re.search(
            r"^permissions:\s*\n((?:(?!^\S).*\n)*)",
            content, re.MULTILINE
        )
        if perms_section:
            perms = [
                line.strip() for line in perms_section.group(1).split("\n")
                if line.strip()
            ]
            wanted = ["contents: read", "pull-requests: read", "issues: write"]
            for entry in wanted:
                if entry not in perms:
                    problems.append(f"permissions must include {entry}")
            extra = [entry for entry in perms if entry not in wanted]
            if extra:
                problems.append(f"permissions has unexpected entries: {extra}")

    # Check: no job-level permissions block
    if re.search(r"^\s{4}permissions:", content, re.MULTILINE):
        problems.append("Job-level permissions: blocks are not allowed")

    # Check: no environment: key anywhere (no secrets live in an Environment)
    if re.search(r"^\s*environment:", content, re.MULTILINE):
        problems.append("environment: is not allowed (the digest needs no Environment)")

    # Check: timeout-minutes: 10 at job indent (4 spaces)
    if not re.search(r"^    timeout-minutes: 10$", content, re.MULTILINE):
        problems.append("Job must have 'timeout-minutes: 10' at 4-space indent")

    # Check: exact DRY_RUN expression
    if not re.search(
        r"^\s{10}DRY_RUN: \$\{\{ github\.event_name == 'workflow_dispatch' && inputs\.dry_run \}\}$",
        content, re.MULTILINE
    ):
        problems.append(
            'DRY_RUN must be: ${{ github.event_name == \'workflow_dispatch\' && inputs.dry_run }}'
        )

    # Check: run block contains required strings and no ${{ interpolation
    run_section = re.search(
        r"^\s{8}run: \|\n((?:(?!^\S).*\n)*)",
        content, re.MULTILINE
    )
    if run_section:
        run_block = run_section.group(1)
        # The then-branch must be the dry run and the else-branch the plain send.
        branch_re = r"\s*" + r"\s+".join(
            re.escape(token)
            for token in (
                "if", "[", '"$DRY_RUN"', "=", '"true"', "];", "then",
                "python", "scripts/weekly_digest.py", "--dry-run",
                "else",
                "python", "scripts/weekly_digest.py",
                "fi",
            )
        ) + r"\s*"
        if not re.fullmatch(branch_re, run_block):
            problems.append(
                'run block must be exactly: if [ "$DRY_RUN" = "true" ]; then '
                "python scripts/weekly_digest.py --dry-run; else "
                "python scripts/weekly_digest.py; fi (then/else branches pinned)"
            )
        if "${{" in run_block:
            problems.append("found ${{ in run block")
    else:
        problems.append("run: | block not found")

    # Check: ${{ only appears inside the step's env: mapping, and only for the
    # token, the notify variable and the DRY_RUN expression
    env_section = re.search(
        r"^\s{8}env:\n((?: {10,}.*\n)*)",
        content, re.MULTILINE
    )
    if env_section:
        env_block = env_section.group(1)
        if "${{" in content.replace(env_block, "", 1):
            problems.append("found ${{ outside the env: mapping")
        allowed = {
            "secrets.GITHUB_TOKEN",
            "vars.DIGEST_NOTIFY",
            "github.event_name == 'workflow_dispatch' && inputs.dry_run",
        }
        for expression in re.findall(r"\$\{\{\s*(.*?)\s*\}\}", env_block):
            if expression not in allowed:
                problems.append(
                    f"env references a disallowed expression: {expression}"
                )
        for name, source in (
            ("GITHUB_TOKEN", "secrets.GITHUB_TOKEN"),
            ("DIGEST_NOTIFY", "vars.DIGEST_NOTIFY"),
        ):
            if f"          {name}: ${{{{ {source} }}}}\n" not in env_block:
                problems.append(f"env must set {name} as ${{{{ {source} }}}}")
    else:
        problems.append("env: block not found in step")

    # Check: the checkout step must not persist the token in .git/config
    checkout_section = re.search(
        r"^      - uses: actions/checkout@[^\n]*\n((?:(?: {8,}.*)?\n)*)",
        content, re.MULTILINE
    )
    if not checkout_section or not re.search(
        r"^ {10}persist-credentials: false$", checkout_section.group(1), re.MULTILINE
    ):
        problems.append("checkout step must set persist-credentials: false")

    return problems


def test_workflow_invariants_hold():
    text = WORKFLOW.read_text(encoding="utf-8")
    problems = workflow_problems(text)
    assert problems == [], f"Workflow has problems:\n" + "\n".join(problems)


@pytest.mark.parametrize(
    "old,new,fragment",
    [
        ("default: true", "default: false", "default: true"),
        ('    - cron: "0 18 * * 0"', '    - cron: "0 19 * * 0"', "cron"),
        ("  workflow_dispatch:", "  pull_request:\n  workflow_dispatch:", "pull_request"),
        ("  contents: read", "  contents: write", "contents: read"),
        ("  issues: write", "  issues: read", "issues: write"),
        ("  issues: write\n", "", "issues: write"),
        ("  issues: write\n", "  issues: write\n  actions: read\n", "unexpected"),
        (
            "    timeout-minutes: 10\n",
            "    timeout-minutes: 10\n    permissions:\n      contents: read\n",
            "permissions",
        ),
        (
            "    timeout-minutes: 10\n",
            "    timeout-minutes: 10\n    environment: digest\n",
            "environment",
        ),
        (
            "          DRY_RUN: ${{ github.event_name",
            "          EXTRA: ${{ secrets.SOMETHING }}\n"
            "          DRY_RUN: ${{ github.event_name",
            "secrets.SOMETHING",
        ),
        (
            "          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}\n",
            "          GITHUB_TOKEN: ${{ secrets.OTHER_TOKEN }}\n",
            "secrets.OTHER_TOKEN",
        ),
        (
            "          DIGEST_NOTIFY: ${{ vars.DIGEST_NOTIFY }}\n",
            "          DIGEST_NOTIFY: ${{ secrets.DIGEST_NOTIFY }}\n",
            "secrets.DIGEST_NOTIFY",
        ),
        ("          DIGEST_NOTIFY: ${{ vars.DIGEST_NOTIFY }}\n", "", "DIGEST_NOTIFY"),
        (
            'python-version: "3.12"',
            "python-version: ${{ secrets.SOMETHING }}",
            "outside",
        ),
        (
            "DRY_RUN: ${{ github.event_name == 'workflow_dispatch' && inputs.dry_run }}",
            "DRY_RUN: ${{ github.event_name == 'workflow_dispatch' || inputs.dry_run }}",
            "DRY_RUN",
        ),
        ('    - cron: "0 18 * * 0"', '    # - cron: "0 18 * * 0"', "cron"),
        (
            "            python scripts/weekly_digest.py --dry-run",
            "            python scripts/weekly_digest.py --dry-run ${{ github.event.inputs.x }}",
            "${{ in run",
        ),
        (  # swap: send in the then-branch, dry run in the else-branch
            "then\n"
            "            python scripts/weekly_digest.py --dry-run\n"
            "          else\n"
            "            python scripts/weekly_digest.py\n",
            "then\n"
            "            python scripts/weekly_digest.py\n"
            "          else\n"
            "            python scripts/weekly_digest.py --dry-run\n",
            "then/else",
        ),
        (  # delete the else-branch
            "          else\n            python scripts/weekly_digest.py\n",
            "",
            "then/else",
        ),
        (
            "        with:\n          persist-credentials: false\n",
            "",
            "persist-credentials",
        ),
    ],
)
def test_workflow_guard_catches_regressions(old, new, fragment):
    text = WORKFLOW.read_text(encoding="utf-8")

    # Verify the original string exists (no false negatives)
    assert old in text, f"Original string not found in workflow: {old}"

    # Apply mutation
    mutated = text.replace(old, new, 1)
    assert mutated != text, f"Mutation is a no-op: {old!r} -> {new!r}"

    # Get problems from mutated workflow
    problems = workflow_problems(mutated)

    # Mutation must be caught
    assert problems, f"Mutation not caught: {old} -> {new}"

    # Problem description must relate to what changed
    assert any(
        fragment.lower() in p.lower() for p in problems
    ), f"No problem mentions {fragment!r}. Problems: {problems}"


def test_workflow_harmless_comment_does_not_cause_false_positive():
    text = WORKFLOW.read_text(encoding="utf-8")

    # Add a harmless comment that mentions things the guard checks
    harmless = text + "\n# note: we never use pull_request: or environment: staging here\n"

    # The guard should still pass
    problems = workflow_problems(harmless)
    assert problems == [], f"Harmless comment caused false positive: {problems}"
