# Architecture

Notes on Santa's module boundaries, interfaces, and the order I built things in — mostly
so I don't have to re-derive a decision six months from now when I've forgotten why I
made it. See [BACKLOG.md](./BACKLOG.md) for what I've deliberately deferred and
[TESTING.md](./TESTING.md) for how each piece gets verified.

## Design goals, in priority order

1. **Modular** — swapping one concern (scraper source, notification channel, LLM
   provider) must only touch that concern's module and its adapter. No other module,
   route, or worker should need to change.
2. **Testable in isolation** — every module boundary below is testable with a fake/stub
   implementation of its neighbors, without a live network call or a real LLM call.
3. **Scalable without a rewrite** — today's scale is a closed cohort (~3-5 users). The
   module boundaries and data model must not need to change shape when that grows;
   only the deployment/orchestration layer around them should.
4. **Staged agency** — the system starts with zero autonomous decision-making (Phase B),
   gains a planning Q&A agent (Phase A), and only much later gains an agent that can take
   real-world action on a user's behalf (Phase C). Each phase's design must not foreclose
   the next.

## Module map

```
talentscope/
  core/           # domain models + interfaces (Protocols/ABCs). Zero I/O, zero framework
                  # imports. Everything else depends on core/; core/ depends on nothing
                  # in this tree.
  sources/        # JobSource implementations — one file per external source.
  integrations/   # External identity/profile providers (GitHub API client,
                  # LinkedIn export parser) — fetch/parse only, same shape as
                  # sources/ but for enriching a user's profile, not job postings.
  analysis/       # Pure functions: skill extraction, trend computation, salary
                  # normalization. Given the same input, always the same output. No
                  # Flask, no DB session, no network call lives here.
  matching/       # Matches jobs against a user's stored preferences.
  notifications/  # Notifier implementations — one file per channel.
  ai/             # QAEngine interface; today one provider (Gemini). This is also
                  # where the Phase A planning agent will live later.
  auth/           # User auth (Flask-Login + bcrypt, per the original stack choice).
  web/            # Flask app: blueprints, routes, templates. Talks to the modules
                  # above through their interfaces only — never reimplements their
                  # logic inline.
  workers/        # Thin CLI entrypoints, one per pipeline stage (Phase B). Each is
                  # independently runnable and independently testable.
  db/             # SQLAlchemy models + Alembic migrations.
  tests/
    unit/         # core/, analysis/, matching/ — no DB, no network.
    integration/  # sources/ + db/, against fixtures — no live network.
    api/          # web/ Flask endpoints.
    e2e/          # Playwright, one full user journey.
```

**Dependency rule:** arrows only point toward `core/`. `web/` and `workers/` are the only
two things allowed to import from multiple modules and wire them together — they are
composition roots, not logic holders. If you find yourself writing an `if/else` on
business logic inside `web/routes/*.py` or `workers/run_*.py`, that logic belongs in
`analysis/`, `matching/`, or `sources/` instead.

## Interfaces (Phase B)

Each boundary below is a `typing.Protocol` (structural typing — implementations don't
need to inherit anything, just match the shape). This keeps `core/` free of concrete
dependencies.

```python
# core/interfaces.py

class JobSource(Protocol):
    name: str
    def fetch(self, since: datetime | None = None) -> list[JobPosting]: ...

class SkillExtractor(Protocol):
    def extract(self, text: str) -> list[str]: ...

class TrendAnalyzer(Protocol):
    def compute(self, jobs: list[JobPosting], period: DateRange) -> TrendReport: ...

class Matcher(Protocol):
    def match(self, prefs: UserPreferences, jobs: list[JobPosting]) -> list[MatchedJob]: ...

class Notifier(Protocol):
    channel: str
    def send(self, user: User, matches: list[MatchedJob]) -> DeliveryResult: ...

class QAEngine(Protocol):
    def answer(self, question: str, context: QueryContext) -> Answer: ...
```

- `sources/internshala.py` and `sources/remotive.py` each implement `JobSource`.
  `sources/registry.py` maps a config string (`"internshala"`, `"remotive"`) to an
  implementation — adding a third source (e.g. a LinkedIn connector, or a paid API) means
  adding one file and one registry line. Nothing in `analysis/`, `matching/`, `web/`, or
  `workers/` changes.
- `analysis/skill_extractor.py` implements `SkillExtractor`; `analysis/trends.py`
  implements `TrendAnalyzer`. Both take plain `JobPosting` data, not raw HTML/JSON — the
  `sources/` layer is responsible for normalizing into `JobPosting` before analysis ever
  sees it.
- `notifications/email_notifier.py` and `notifications/telegram_notifier.py` implement
  `Notifier`. `notifications/registry.py` maps a user's preferred channel(s) to
  implementation(s). Adding Slack/Discord later is one new file.
- `ai/providers/gemini.py` implements `QAEngine`. Swapping to a different provider
  (Claude, GPT, a local model) means writing one new file under `ai/providers/` and
  changing one config value — `web/` and everything else calls `QAEngine.answer()` and
  never imports `google.generativeai` directly.

## Data model (db/)

Core tables, replacing the CSV-based storage from the original prototype:

- `jobs` — normalized postings from all sources (`source`, `title`, `company`,
  `location`, `salary_raw`, `salary_numeric`, `skills`, `link`, `posted_at`, `scraped_at`).
  Unique constraint on a normalized key (title+company+location+source) for dedup.
- `users`, `user_preferences` (skills, locations, min stipend, preferred channels)
- `matches` — which jobs were matched to which user, and when (so re-runs don't
  re-notify for the same job).
- `notifications_sent` — delivery log per channel, with status (sent/failed), for
  debugging and for future dedup/rate-limiting logic.
- `action_log` — **created now, unused until Phase C.** Records any automated
  system-initiated action with a `proposed_at` / `approved_at` / `executed_at` /
  `status` shape. Nothing writes meaningful rows here in Phase B beyond notification
  sends (which double as the first "actions" in the log) — but the table exists so
  Phase C's approval layer has a substrate to build on rather than needing a schema
  migration plus a retrofit of an audit trail.

SQLAlchemy + Alembic, Postgres in production / SQLite in tests. Originally planned as
MySQL, revised when picking a free-forever deployment target: Render's only managed
database is Postgres, and Neon's free Postgres tier (scale-to-zero compute, no 30-day
expiry) is what backs production. SQLAlchemy makes this a driver + connection-string
change (`psycopg`), not a rewrite — no ORM code depends on a MySQL-specific feature.

## Orchestration: is a job/event queue needed now?

**No — not for Phase B.** At cohort scale (a handful of users, a scrape running a few
times a day), the cost of a queue (Redis/Celery or similar infra to run, monitor, and
keep alive) outweighs what it buys. Instead:

- Each pipeline stage is a **separate CLI entrypoint** under `workers/`:
  `run_scrape.py`, `run_analyze.py`, `run_match.py`, `run_notify.py`. Each is a thin
  script that wires together a `JobSource` (or several), calls into `analysis/` or
  `matching/` or `notifications/`, and exits. Each is runnable and testable completely
  independently of the others — `run_notify.py` can be invoked against a fixture DB
  without ever running a scrape.
- **APScheduler**, running in-process inside the Flask app (or a tiny separate
  scheduler process — see open question below), triggers these stages in sequence on a
  cron-like schedule. This is orchestration, not business logic — it just shells out to
  (or imports and calls) each worker in order.
- Because failure is isolated per stage (a scrape failure doesn't corrupt analysis, a
  notify failure doesn't re-trigger a scrape), this gets most of the reliability benefit
  of a queue without the operational cost.

**When to revisit:** introduce a real queue (Celery+Redis, RQ, or a managed equivalent)
when either becomes true:
1. Scrape/analyze volume grows past what a single scheduled run can finish before the
   next one starts, or needs to run concurrently across multiple sources at real
   throughput.
2. Phase A's planning agent needs to kick off multi-step, potentially slow tool-calling
   work from a web request without blocking the HTTP response (e.g. "compare three time
   periods" taking tens of seconds).

Because the workers are already separate, independently-invokable units by the end of
Phase B, that migration is a **change to what triggers them** (a queue consumer instead
of APScheduler calling them in sequence), not a rewrite of what they do.

## Phase A — planning Q&A agent (next up)

Today's Q&A ("ask Gemini a fixed question against the live DB") becomes an agent that
decides its own steps: pulling multiple data slices, comparing time periods, checking
several sources before answering.

**The seam Phase B must leave clean:** `analysis/` and `matching/` functions must be
plain, well-typed, importable functions — never logic embedded inside a Flask route
handler or inside `ai/providers/gemini.py` itself. When Phase A is built, the agent's
tool layer wraps those *same* functions as callable tools:

```python
# ai/tools.py (Phase A — not built yet)
TOOLS = {
    "get_jobs": analysis.get_jobs,           # already exists from Phase B
    "get_trends": analysis.trends.compute,   # already exists from Phase B
    "compare_periods": analysis.trends.compare,  # already exists from Phase B
    "get_user_matches": matching.matcher.match,  # already exists from Phase B
}
```

`QAEngine.answer()` in Phase A becomes an agentic loop (plan → call tool(s) → observe →
repeat → answer) instead of a single prompt-and-response, but the *interface visible to
`web/`* — `QAEngine.answer(question, context) -> Answer` — does not change. The web layer
that calls it is untouched. Only `ai/` changes shape internally, plus new tool
definitions that are thin wrappers around code that already exists by the end of Phase B.

This is why Phase B insists on business logic living in `analysis/`/`matching/` rather
than inline in routes: it's the same logic Phase A needs to expose as tools, and
duplicating it there would mean two implementations to keep in sync.

## Phase C — action-taking agents (not building this yet)

Auto-apply, auto-message-a-recruiter, and similar actions need a trust/safety/approval
layer that doesn't exist yet, and I'm not building it until Phase A has earned some
trust. What Phase B needs to leave open for later:

- **All outbound, real-world-visible actions already go through a narrow interface.**
  Notifications already go through `Notifier.send()`, not scattered `smtp.send()`/bot-API
  calls. When Phase C adds new action types (submit an application, send a message on a
  user's behalf), they get their own `Action` interface, structurally the same shape —
  `propose()` returns something that must be explicitly approved before an `execute()` is
  ever called. Because Phase B already centralizes side effects behind interfaces rather
  than performing them ad hoc, adding an approval gate in front of that interface later is
  a wrapper/decorator, not a rewrite of every call site.
- **The `action_log` table exists from day one** (see Data model above), even though
  in Phase B it only logs notification sends. Phase C's approval workflow (propose →
  user/system approves → execute → log outcome) reuses that table's shape rather than
  needing a new audit system bolted on retroactively.
- **No autonomy beyond notification-sending is implemented in Phase B or Phase A.** The
  Phase A agent only ever answers questions — it does not send messages, apply to jobs,
  or take any action a user didn't directly trigger. That boundary is enforced by which
  tools exist (`ai/tools.py` in Phase A only contains read-only query tools), not by a
  runtime check — there is nothing to gate because there is nothing that acts.

Full design of the approval/trust layer itself is deferred to when Phase C is actually
scheduled — see [BACKLOG.md](./BACKLOG.md).

## Deployment view

Single Flask service + single scheduler process (or in-process APScheduler within the
same Flask process, TBD — see open question below), MySQL, deployed to Render, matching
the original README's choices. This is intentionally boring at cohort scale. The module
boundaries above are what make it possible to later split `workers/` into separately
deployed processes, or move `ai/` behind its own service, without the change touching
`web/`, `db/`, or the data model.

## Build sequence (incremental PRs)

Ordered so each PR is independently mergeable, keeps CI green, and never leaves the repo
in a state where a previous PR's tests are broken by a later one.

1. **Repo scaffold + CI skeleton** ✅ — `core/` package with empty interface
   definitions, `db/` with SQLAlchemy setup (no tables yet), pytest config, GitHub
   Actions workflow that runs `pytest` + `ruff` + `black --check` on an empty/near-empty
   test suite so the gate exists before there's much to gate.
2. **Data model** ✅ — `db/models.py` (jobs, users, user_preferences, matches,
   notifications_sent, action_log) + first Alembic migration. Unit tests for model
   constraints (dedup key, cascades).
3. **`sources/` — Internshala + Remotive adapters** ✅ implementing `JobSource`, plus
   `tests/fixtures/` of saved HTML/JSON and integration tests against them (no live
   network in CI). `workers/run_scrape.py` entrypoint.
4. **`analysis/`** ✅ — skill extractor, salary normalizer, trend computation as pure
   functions with unit tests. `workers/run_analyze.py` entrypoint normalizes stored
   jobs' stipends and backfills skills from title text when a source provides none.
5. **`matching/`** ✅ — matcher + unit tests. `workers/run_match.py` entrypoint.
6. **`auth/` + `web/` skeleton** ✅ — Flask-Login, signup/login, user preferences CRUD,
   API tests for each endpoint.
7. **`notifications/`** ✅ — email (stdlib `smtplib`) + Telegram (stdlib `urllib`
   against the Bot API) notifiers implementing `Notifier`, with a fake notifier used in
   tests (no real sends in CI). `workers/run_notify.py` entrypoint.
8. **APScheduler wiring** ✅ — `workers/scheduler.py` runs stages 3/4/5/7 in sequence as
   a separate process (see resolved scheduler topology decision below); this is the
   first PR where the full pipeline runs end-to-end.
9. **`ai/` — Gemini `QAEngine`** ✅ — `ai/providers/gemini.py` + `ai/registry.py`,
   single-query `/qa` endpoint, API tests with a fake `QAEngine` for deterministic
   tests plus one gated live-Gemini smoke test (`tests/integration/test_gemini_live.py`,
   skipped unless `GEMINI_API_KEY` is set, excluded from the default run via the `live`
   pytest marker).
10. **E2E test** — signup → set preferences → see matched jobs, Playwright headless,
    against the full stack from steps 2-9.
11. **Structured logging + deploy to Render** — matches original README's ops goals.

Phase A (agent) and Phase C (approval layer) are separate roadmap items after this
sequence lands — see [BACKLOG.md](./BACKLOG.md).

## Open questions

## Resolved implementation decisions

- **Internshala scraping: Playwright.** Its locator auto-waiting and browser context isolation make dynamic-page scraping and the eventual E2E suite more deterministic in CI. Use Chromium initially; install its browser binary explicitly in CI. `requests`+`BeautifulSoup` is not the primary adapter for this JS-rendered source.
- **Scheduler process topology: separate process.** `workers/scheduler.py` runs
  APScheduler's `BlockingScheduler` as its own standalone entrypoint (`PIPELINE_CRON`,
  `PIPELINE_SOURCES`, `DATABASE_URL` env vars), not inside the Flask app. Isolates a
  stuck scrape/notify run from web uptime and vice versa, at the cost of one more
  process to deploy/monitor on Render. It runs each pipeline stage (scrape → analyze →
  match → notify) in its own transaction and its own try/except, so one stage's failure
  doesn't block the rest — same per-stage isolation as everywhere else in this pipeline.
