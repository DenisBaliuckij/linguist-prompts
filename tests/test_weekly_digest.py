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
