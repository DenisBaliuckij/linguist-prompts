# linguist-prompts — design

**Изменение 2026-09-20 / Change 2026-09-20:** delivery switched from SMTP email to a GitHub Issue (Microsoft disabled SMTP password sign-in for the planned Outlook mailbox); sections below that mention SMTP/secrets/Environment `digest` are superseded as follows:

- Decisions table rows "Digest delivery" and "Recipients", and the Trigger lines `environment: digest` and the permissions list: each run creates one GitHub Issue (label `digest`, title unchanged) with the workflow's `GITHUB_TOKEN`; permissions are `contents: read`, `pull-requests: read`, `issues: write`, and there is no `environment:`. Recipients are the logins in the Actions variable `DIGEST_NOTIFY` plus anyone watching the repo; GitHub's own mailer sends the notifications.
- Purpose sentence ("summarises the week's merged changes … in a Russian email") and the Schedule row ("an empty week still sends a 'no changes' email"): the digest is a Russian GitHub Issue, and an empty week still posts an issue saying «За неделю изменений нет.».
- "Email" section: the issue body is Markdown in Russian (first line `Для: @login1 @login2` only when `DIGEST_NOTIFY` is non-empty, then period, totals and one block per `language/subject`). Everything derived from PR titles, logins and paths is escaped so that it cannot @mention anyone, create `#N` or `GH-N` references, inject HTML or images, or autolink a URL. A body over 60,000 characters (GitHub rejects more than 65,536) is shortened: first the per-file lists are omitted, then trailing PRs are dropped with a notice, and the totals still count every PR. `--dry-run` prints the same title and body without posting.
- "Secrets — GitHub Environment `digest`" section (and the `MAIL_TO` parsing item under Testing): replaced by the optional plain Actions variable `DIGEST_NOTIFY` (GitHub logins separated by spaces, commas or semicolons). There are no SMTP secrets and no Environment.
- "Errors" section ("SMTP auth or send failures"): replaced by GitHub API errors, reported as `GitHub API <status> for <METHOD> <path>: <message>`, for example 410 when Issues are disabled or 422 for an invalid request.
- "Testing" acceptance line ("delivering to both recipients"): a real dispatch creates the issue and the notified users receive GitHub's email for it.
- Bootstrap order steps 2–3 (create Environment `digest`, set the six secrets) are dropped, and the paragraph "Steps 1–2 must precede step 4" is replaced: after the launch push, create the `digest` label, set the optional repo variable `DIGEST_NOTIFY`, confirm that Issues are enabled, run the dry-run dispatch and one real post, then apply branch protection (which must stay after the push, because admin enforcement blocks even the owner), then invite collaborators.
- Known limitation about new Yandex mailboxes is replaced by: recipients need GitHub accounts with email notifications turned on.

Date: 2026-09-19 · Owner: DenisBaliuckij · Status: awaiting review

## Purpose

A public GitHub repository where linguists collaboratively write, edit and
discuss prompts as Markdown files, organised per language and per language
subject. All changes reach `main` only through pull requests. Every Sunday a
pipeline summarises the week's merged changes (who changed what) in a Russian
email.

## Decisions (settled during brainstorming)

| Topic | Decision |
|---|---|
| Repo | `DenisBaliuckij/linguist-prompts`, public, default branch `main` |
| Layout | `languages/<lang>/<subject>/` containing `README.md` and `prompts.md` |
| Contributors | Direct collaborators with write access (invited by the owner) |
| Merge gate | PR required, 1 approving review, **enforced on admins too** |
| Automated PR checks | None (human review is the only gate) |
| Digest delivery | SMTP from GitHub Actions, Yandex mailbox |
| Digest content | Deterministic Russian template — no LLM, no external API |
| Schedule | Sundays 18:00 UTC; an empty week still sends a "no changes" email |
| Recipients | Two addresses, held only in the `MAIL_TO` secret (never committed) |
| License | CC-BY-4.0 |

## Repository layout

```
README.md                  # Russian, one-line English summary on top
CONTRIBUTING.md            # Russian: how to add a language/subject, PR flow
LICENSE                    # CC-BY-4.0
languages/russian/grammar/{README.md,prompts.md}   # seed example
.github/PULL_REQUEST_TEMPLATE.md   # what changed / why (for reviewers)
.github/workflows/weekly-digest.yml
scripts/weekly_digest.py           # stdlib only
tests/test_weekly_digest.py        # pytest, fixture JSON, no network
docs/superpowers/specs/            # this document
```

A new language or subject is just a new folder; nothing is registered anywhere.

## Branch protection and repo settings

Applied with `gh api` **after** the launch content is on `main` (see
Bootstrap order).

- `main`: pull request required, 1 approving review, dismiss stale approvals
  on new commits, `enforce_admins: true`, no force-push, no deletion.
- No required status checks.
- Merge method: squash only; automatically delete head branches after merge.
- Consequence: until a second collaborator exists, the owner cannot merge
  their own PRs. Documented escape hatch for pipeline maintenance: temporarily
  disable admin enforcement with
  `gh api -X DELETE repos/DenisBaliuckij/linguist-prompts/branches/main/protection/enforce_admins`,
  make the change, re-enable with `-X POST`.

## Weekly digest

### Trigger — `.github/workflows/weekly-digest.yml`

- `schedule: cron "0 18 * * 0"` and `workflow_dispatch` with a boolean
  `dry_run` input (default `true`). Scheduled runs are never dry.
- `permissions: contents: read, pull-requests: read`.
- `environment: digest` (see Secrets). `timeout-minutes: 10`.
- Steps: checkout, run `python3 scripts/weekly_digest.py`. No dependencies to
  install.

### Window

`end` = the most recent Sunday 18:00 UTC that is ≤ now; `start` = `end` − 7
days. The interval is half-open `[start, end)`. Anchoring to the calendar
instead of "now" means a delayed cron run can neither miss nor double-count a
PR. `--now <ISO>` overrides the clock for tests.

### Data collection (GitHub REST API, `GITHUB_TOKEN`)

1. List closed PRs sorted by `updated` descending, paginated; stop once a
   page's PRs are all `updated_at < start`; keep those with
   `merged_at ∈ [start, end)`.
2. For each: `GET /pulls/{n}/files` (paginated) and `GET /pulls/{n}/reviews`;
   approvers = users whose latest review state is `APPROVED`.
3. Map each changed file path to a group `language/subject` when it matches
   `languages/<lang>/<subject>/...`, else to "Прочее" (outside `languages/`).
   Keep status per file: added / modified / removed / renamed.

### Email

- `multipart/alternative`, plain text + HTML, UTF-8, HTML-escaped.
- Subject: `Сводка linguist-prompts: DD.MM.YYYY–DD.MM.YYYY`.
- Body: totals (PRs merged, contributors, files changed), then one block per
  `language/subject` listing each PR (`#n title`, link, author, approvers,
  merge date) and the files touched with their status. Contributors are shown
  as `@login`.
- Empty week: short «За неделю изменений нет» message with the same subject
  and the repo link.
- Recipients come from `MAIL_TO` (comma- or semicolon-separated).
- `--dry-run` (or `dry_run=true`): print subject and text body to the log, do
  not connect to SMTP.

### Secrets — GitHub Environment `digest`

`SMTP_HOST` (`smtp.yandex.ru`), `SMTP_PORT` (`465`, implicit SSL), `SMTP_USER`,
`SMTP_PASSWORD` (a Yandex **app password**), `MAIL_FROM` (must equal
`SMTP_USER`; Yandex rejects other From addresses), `MAIL_TO`.

They live in an Environment restricted to deployment branch `main`, not in
plain repo secrets. Reason: `workflow_dispatch` can run on any branch, and
every collaborator has write access, so a workflow edited on a feature branch
could otherwise read repo secrets. An environment limited to `main` closes
that, and only reviewed code can ever see the SMTP password. Secrets are
entered by the owner with `gh secret set <NAME> --env digest -R
DenisBaliuckij/linguist-prompts`, never pasted into chat or committed.

### Errors

Missing secrets, API errors, SMTP auth or send failures raise and fail the
job with a clear message; GitHub then notifies the owner of the failed run.
Nothing is swallowed and there is no silent retry.

## Testing

- `pytest`, stdlib only, fixture JSON for the API responses, no network.
- Cover: window computation (before/after/exactly at Sunday 18:00, week
  boundaries), half-open interval edges, path→group mapping, latest-review
  approver logic, Russian rendering (normal week, empty week, HTML escaping),
  `MAIL_TO` parsing.
- Acceptance: after secrets are set — one `dry_run=true` dispatch, then one
  real dispatch delivering to both recipients.

## Bootstrap order (required by admin enforcement)

1. Create the public repo; push the complete launch content (skeleton, script,
   tests, workflow, this spec) straight to `main`.
2. Create Environment `digest` (branch policy: `main`).
3. Owner sets the six secrets (needs the Yandex mailbox and app password).
4. Apply branch protection and merge-method settings.
5. Dry-run dispatch, then real test send.
6. Invite collaborators.

Steps 1–2 must precede step 4: once protection with admin enforcement is on,
even the owner cannot push to `main`.

## Known limitations

- GitHub disables scheduled workflows in a public repo after 60 days without
  repository activity; the digest would then stop silently. Noted in the
  README; no keep-alive job (kept minimal).
- Digest lists merged PRs only; open discussions and comments are not
  summarised.
- New Yandex mailboxes can be rate-limited or flagged; a two-recipient weekly
  message is far below any limit, but the first delivery to each recipient should
  be checked (including spam folders).

## Out of scope

Structure linting, LLM-written summaries, a keep-alive workflow, per-language
CODEOWNERS, translation of prompts.
