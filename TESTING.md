# Testing strategy

The test suite is the centerpiece of this project (see [README.md](./README.md#why-this-project-exists)
for why). This document defines the four test layers, what belongs in each, how the
module boundaries in [ARCHITECTURE.md](./ARCHITECTURE.md) make each layer possible to
test in isolation, and the CI gate.

## The four layers

| Layer | What it covers | Depends on | Tools |
|---|---|---|---|
| **Unit** | `core/`, `analysis/`, `matching/` — pure functions and domain logic | Nothing external | `pytest`, plain asserts |
| **Integration** | `sources/` against saved fixtures, `db/` against SQLite in-memory | SQLite, fixture files | `pytest`, SQLite |
| **API** | Every Flask endpoint in `web/`: status code, JSON schema, auth | Flask test client, fake service implementations | `pytest-flask`, `jsonschema` |
| **E2E** | One full user journey: signup → set preferences → see matched jobs | Full stack, headless browser | `pytest`, Selenium headless |

Coverage target: **≥70%**, enforced in CI via `pytest --cov-fail-under=70`. This was the
original target and isn't being revised — it's a reasonable bar for a solo/small-cohort
project without being a vanity number.

## Why the module boundaries matter for testability

Each interface in `core/interfaces.py` (`JobSource`, `SkillExtractor`, `TrendAnalyzer`,
`Matcher`, `Notifier`, `QAEngine`) exists specifically so every layer above can be tested
against a **fake implementation** of its neighbors instead of the real thing:

- **`analysis/` and `matching/` unit tests** never touch a database or the network —
  they're pure functions over `JobPosting`/`UserPreferences` objects constructed directly
  in the test. This is what makes them fast and what makes them safely reusable as Phase
  A's agent tools later (see ARCHITECTURE.md's Phase A section) — a tool an LLM agent can
  call needs to be exactly this kind of deterministic, side-effect-free function.
- **`web/` API tests** inject a fake `QAEngine`, fake `Notifier`, and a test DB session
  instead of hitting Gemini, sending real email/Telegram messages, or requiring live
  Internshala access. A route handler test asserts "given this fake matcher's output, the
  endpoint returns this JSON" — it is not also (accidentally) an integration test of the
  matcher itself.
- **`sources/` integration tests** run against HTML/JSON fixtures committed to
  `tests/fixtures/`, never live network. This is unchanged from the original plan and is
  worth restating: it keeps CI deterministic and independent of Internshala's uptime or
  layout, and a broken fixture test is a real signal ("the scraper's selectors no longer
  match saved real-world HTML") rather than noise from a flaky external site.

## Fixture strategy

- `tests/fixtures/internshala/*.html` — saved real listing + detail pages, one per
  distinct page layout worth covering (paginated listing, a listing with no salary
  shown, a listing with multiple skill tags, etc).
- `tests/fixtures/remotive/*.json` — saved API responses, including at least one
  malformed/partial response to test the source's error handling.
- Fixtures are committed to the repo (not generated at test time) so CI never depends on
  live network access, and so a fixture update is a deliberate, reviewable diff when
  Internshala's markup changes.

## CI gate

GitHub Actions runs on every push and PR:

1. `ruff` lint + `black --check` — fails fast on style issues before running tests.
2. `pytest` — all four layers, `--cov-fail-under=70`.
3. Merge to `main` is blocked unless this workflow passes.

This gate exists from PR #1 in the [build sequence](./ARCHITECTURE.md#build-sequence-incremental-prs)
(even before there's much to test), so the discipline is never something added
retroactively.

## Testing the AI layer (Phase A design note)

Not built yet, but the testing shape should be decided alongside the architecture so
Phase A doesn't need a testing-strategy retrofit:

- **Phase B (current single-query `QAEngine`):** API tests inject a fake `QAEngine` that
  returns a canned `Answer`. One separate, explicitly-marked live-Gemini smoke test
  (excluded from the default CI run, or run less frequently) checks the real integration
  still works, since LLM output isn't deterministic enough for a strict assertion.
- **Phase A (planning agent, later):** the same fake-vs-live split applies, but adds a
  layer in between — since the agent's tool calls (`get_jobs`, `get_trends`,
  `compare_periods`, etc.) are the same deterministic functions from `analysis/`/
  `matching/`, they're testable exactly as they are in Phase B. What's new to test is the
  **planning loop itself**: given a fixed sequence of fake tool responses, does the agent
  produce a reasonable final answer, and does it stop instead of looping indefinitely?
  This calls for golden-transcript tests (fixed tool-call sequence in, expected shape of
  final answer out) rather than asserting exact LLM wording — the assertions target
  *which tools got called and in what order*, not the prose Gemini generates.

## Testing Phase C (not built — for future reference)

Out of scope to design in detail now (see [BACKLOG.md](./BACKLOG.md)), but noted here so
future work doesn't have to rediscover the constraint: any test involving an `Action`
that has a real-world side effect (an actual application submission, an actual message to
a recruiter) must never run against a real target in CI, the same way `sources/` tests
never hit live Internshala. That almost certainly means the approval layer itself needs a
fake "external world" to execute against in tests, decided when Phase C is actually
scoped.
