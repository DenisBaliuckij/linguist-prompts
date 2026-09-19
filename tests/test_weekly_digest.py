"""Tests for scripts/weekly_digest.py - no network, fixture data only."""

from __future__ import annotations

import smtplib
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


def test_render_html_escapes_every_untrusted_field():
    import html as _html

    HOSTILE = '"><img src=x onerror=alert(1)>&'
    hostile_repo = "acme/repo" + HOSTILE

    pr = wd.MergedPR(
        number=99,
        title="Normal title",
        url="https://x.test/" + HOSTILE,
        author="a" + HOSTILE,
        approvers=("b" + HOSTILE,),
        merged_at=dt(2026, 9, 15, 10, 0),
        files=(
            wd.FileChange('languages/g"<x>&/s"<y>&/p.md', "added"),
        ),
    )

    out = wd.render_html([pr], START, END, hostile_repo)

    # Verify escaped forms appear
    assert _html.escape("a" + HOSTILE) in out, "Author not escaped"
    assert _html.escape("b" + HOSTILE) in out, "Approver not escaped"
    assert _html.escape("https://x.test/" + HOSTILE) in out, "URL not escaped"
    assert _html.escape('g"<x>&/s"<y>&') in out, "Group key not escaped"
    assert _html.escape(hostile_repo) in out, "Repo name not escaped"
    assert _html.escape('languages/g"<x>&/s"<y>&/p.md') in out, "File path not escaped"

    # Verify escaped quote form appears
    assert "&quot;" in out, "Escaped quote not found"

    # Verify raw hostile substrings do NOT appear
    assert "<img" not in out, "Raw <img found"
    assert "<x>" not in out, "Raw <x> found"
    assert "<y>" not in out, "Raw <y> found"
    assert "<z>" not in out, "Raw <z> found"
    assert '"><img' not in out, 'Raw "><img found'


# --- message, SMTP and CLI -------------------------------------------------


class FakeSMTP:
    instances: list[FakeSMTP] = []
    send_result = None
    send_error = None

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
        if type(self).send_error:
            raise type(self).send_error
        self.sent = (msg, from_addr, to_addrs)
        return type(self).send_result or {}


@pytest.fixture
def smtp(monkeypatch):
    FakeSMTP.instances = []
    FakeSMTP.send_result = None
    FakeSMTP.send_error = None
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


def test_send_email_raises_when_some_recipients_are_refused(smtp):
    smtp.send_result = {"b@y.ru": (550, b"no such user")}
    cfg = wd.load_mail_config(GOOD_ENV)
    msg = wd.build_message([], START, END, REPO, cfg.sender, cfg.recipients)

    with pytest.raises(RuntimeError) as exc:
        wd.send_email(msg, cfg)

    assert "1 of 2" in str(exc.value)
    assert "b@y.ru" not in str(exc.value)
    assert "a@x.ru" not in str(exc.value)


def test_send_email_hides_addresses_when_smtp_refuses_all_recipients(smtp):
    smtp.send_error = smtplib.SMTPRecipientsRefused(
        {"a@x.ru": (550, b"x"), "b@y.ru": (550, b"y")}
    )
    cfg = wd.load_mail_config(GOOD_ENV)
    msg = wd.build_message([], START, END, REPO, cfg.sender, cfg.recipients)

    with pytest.raises(RuntimeError) as exc:
        wd.send_email(msg, cfg)

    assert "a@x.ru" not in str(exc.value)
    assert "b@y.ru" not in str(exc.value)
    assert exc.value.__suppress_context__ is True


def test_send_email_hides_sender_when_smtp_refuses_sender(smtp):
    smtp.send_error = smtplib.SMTPSenderRefused(550, b"denied", "bot@yandex.ru")
    cfg = wd.load_mail_config(GOOD_ENV)
    msg = wd.build_message([], START, END, REPO, cfg.sender, cfg.recipients)

    with pytest.raises(RuntimeError) as exc:
        wd.send_email(msg, cfg)

    assert "bot@yandex.ru" not in str(exc.value)
    assert exc.value.__suppress_context__ is True


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
