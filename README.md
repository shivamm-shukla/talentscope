<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="web/static/assets/logo-dark.svg">
  <img src="web/static/assets/logo.svg" width="72" height="72" alt="Santa logo">
</picture>

# Santa

### **Your career, sorted before you ask.**

**[talentscope-pisc.onrender.com](https://talentscope-pisc.onrender.com/)** — live, closed-cohort signups

[![CI](https://github.com/shivamm-shukla/talentscope/actions/workflows/ci.yml/badge.svg)](https://github.com/shivamm-shukla/talentscope/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)

</div>

---

Santa is a proactive AI career companion for CS/BCA students — the site surfaces
what you need, instead of making you search for it. **santa scout**, this codebase,
is the first product: internship/job discovery, matched and delivered by email or
Telegram. Built with a full SDET-grade test suite and CI pipeline. (Repo is still
named `talentscope` after the pre-rebrand project name; the product was also briefly
called "Internai" before settling on Santa.)

---

## Status

🚧 **Active development.** Built with a production-grade architecture, full test pyramid, and CI/CD from day one. See the [roadmap](#roadmap) for current progress.

The project is intentionally built like it has real users — full auth, real notifications, deployed publicly — but is being validated with a closed cohort (myself + 2-3 batchmates) before opening signups.

---

## Product vision

**Santa** is the umbrella brand for a proactive AI career companion for CS/BCA
students — the site should tell students what they need to know, not make them go
searching for it. **santa scout** (this codebase) is the first product: internship
and job discovery. Planned siblings, not yet built:

| Product | What it does | Status |
|---|---|---|
| **santa scout** | Internship/job discovery: scrape, classify, match, alert | 🟢 Live |
| **santa prep** | AI mock-interview trainer | ⚪ Planned |
| **santa desk** | Calendar, email & meeting management agent | ⚪ Planned |
| **santa vaani** | Voice & call companion (reminders, check-ins) | ⚪ Planned |

Scope for santa scout is deliberately narrow: **CS/BCA/computer-related-course
students only** (not every field), and postings whose application window has
already lapsed are never stored or shown — both decisions trade coverage for
signal quality and lower scraping/storage cost.

---

## Engineering principles

Three non-negotiables that shape every module in this codebase:

1. **No untested scrapers.** Source adapters are tested against saved HTML/JSON
   fixtures — a layout change on the source site should never fail silently.
2. **Real storage, not CSVs.** Postgres in production, SQLAlchemy models, Alembic
   migrations — queryable, concurrent-write-safe from the start.
3. **CI-gated merges.** Nothing reaches `main` without tests passing and coverage
   holding the line (see [CI gate](#project-conventions)).

The product value is for students; the engineering rigor is for me.

---

## What it does

### For users (CS/BCA students)

- **Web app** (`/`, `/app`) — signup, preferences, and a proactive matches feed, with light/dark theme
- **Daily-curated internship/job feed** scraped from Internshala (Playwright) and Remotive API, filtered to CS/BCA-relevant postings only
- **Classification** of every posting into listing type (internship/job), work mode (remote/onsite/hybrid), pay type, duration, and target year — so the feed reads like a briefing, not a search-results page
- **Retention policy** — postings past their estimated application window are never stored or shown
- **Personalised alerts** via email and Telegram, matched against user-set skills, location, and stipend preferences
- **Natural-language Q&A** (API today, no dedicated page yet) — ask "What skills are trending for ML interns in Bangalore?" and get a grounded answer powered by Google Gemini over the live job database

Not yet exposed: a market-trends dashboard (skill/city/stipend trends) — the
analysis logic exists in `analysis/trends.py` but no route surfaces it yet.

### For me (the engineer)

- A real codebase demonstrating SDET fundamentals end-to-end: unit, integration, API contract, and Playwright E2E tests
- A CI pipeline that gates merges on tests passing
- Structured JSON logging suitable for log-analysis tooling
- A deployable Flask app with Postgres persistence and Alembic migrations

---

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Internshala │     │   Remotive   │     │    Gemini    │
│ (Playwright)  │     │    (REST)    │     │     (AI)     │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────┬───────────┘                    │
                ▼                                │
        ┌───────────────┐                        │
        │   Analyzer    │                        │
        │ (skill ext.,  │                        │
        │  trends, NLP) │                        │
        └───────┬───────┘                        │
                ▼                                │
        ┌───────────────┐      ┌─────────────────▼──┐
        │    Postgres   │◄─────┤   Flask Web App     │
        │ (jobs, users, │      │ (auth, dashboard,   │
        │  preferences) │      │  REST API, Q&A)     │
        └───────┬───────┘      └──────────┬─────────┘
                │                         │
                ▼                         ▼
        ┌───────────────┐         ┌──────────────┐
        │   Notifier    │         │   Browser    │
        │ Email │ Telegram│        │   (user)     │
        └───────────────┘         └──────────────┘
```

A more detailed walkthrough of design decisions lives in [`ARCHITECTURE.md`](./ARCHITECTURE.md).

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11 | Familiarity + ecosystem |
| Web | Flask + Jinja templates | Server-rendered pages calling the same JSON API the Flask backend exposes |
| ORM | SQLAlchemy + Alembic | Same code runs against Postgres (prod) and SQLite (tests) |
| DB | Postgres (Neon, free) / SQLite (test) | Free-forever managed Postgres; tests stay fast |
| Scraping | Playwright + pytest-playwright | Handles dynamic Internshala pages |
| Scheduling | APScheduler | In-process, no separate worker needed for v1 |
| Auth | Flask-Login + bcrypt | Standard, well-understood |
| Email | Flask-Mail (Gmail SMTP) | Free tier, sufficient for cohort scale |
| Telegram | python-telegram-bot | Free, students already use it |
| AI | google-generativeai (Gemini) | Free tier sufficient for Q&A |
| Testing | pytest, pytest-cov, pytest-flask, factory_boy, jsonschema | Industry-standard test stack |
| CI | GitHub Actions | Free for public repos, runs on every push |
| Logging | structlog (JSON) | Queryable logs — relevant to SDET log-analysis skills |
| Deployment | Render (web) + Neon (DB) + GitHub Actions (cron pipeline) | Free-forever stack for solo/cohort use |

---

## Testing strategy

The test suite is the centerpiece of this project. Tests live in `tests/` and are organised into four layers:

| Layer | What it covers | Tools |
|---|---|---|
| **Unit** | Pure functions: skill extractor, salary normaliser, match logic | `pytest`, mocks |
| **Integration** | Scraper → DB pipeline against saved HTML fixtures (no live network) | `pytest`, SQLite in-memory |
| **API** | Every Flask endpoint: status code, JSON schema, auth | `pytest-flask`, `jsonschema` |
| **E2E (Playwright)** | One full user journey: signup → set preferences → see matched jobs | `pytest`, Playwright headless |

**Why fixtures, not live scraping in tests:** the scraper is tested against saved Internshala HTML files committed to `tests/fixtures/`. This keeps CI deterministic, fast, and independent of Internshala's uptime — the same principle used in production SDET teams.

**Coverage target:** ≥70% (enforced in CI via `pytest --cov-fail-under=70`).

Full test strategy and rationale: [`TESTING.md`](./TESTING.md).

---

## Roadmap

### v1 — In progress

- [x] Project setup, repo, README, architecture doc
- [x] SQLite/MySQL schema + SQLAlchemy models + Alembic migrations
- [x] GitHub Actions CI pipeline
- [x] Playwright scraper (Internshala) with Page Object Model
- [x] Remotive API client
- [x] Skill extractor + analyzer (trend computation)
- [x] Flask auth + user preferences
- [x] Email notifier
- [x] Telegram notifier
- [x] APScheduler pipeline wiring (separate process; scrape → analyze → match → notify)
- [x] Gemini Q&A endpoint
- [x] pytest suite: unit, integration, API (E2E still pending)
- [x] ≥70% coverage (99% on covered modules as of the AI Q&A endpoint)
- [x] Structured JSON logging
- [x] Render deployment (code/config ready — see "Deploying" below for the manual account-setup steps)
- [x] Web UI (landing, signup/login, preferences, matches feed) with light/dark theme
- [x] CS/BCA relevance filter + listing taxonomy (work mode, pay type, duration, target year) at ingestion
- [x] Expiry-based retention (don't store/list postings past their application window)

### Explicitly out of scope for v1

These are intentional cuts — not forgotten features. Parking lot for v2 in [`BACKLOG.md`](./BACKLOG.md).

- Public open signups (closed cohort during v1)
- Mobile app
- Sources beyond Internshala + Remotive
- Resume matching / application tracking
- Payments or premium tiers
- SMS / push notifications

---

## Running locally

```bash
# Clone and set up
git clone https://github.com/shivamm-shukla/talentscope.git
cd talentscope
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]

# Configure
cp .env.example .env
# edit .env with DB URL, Gmail credentials, Telegram token, Gemini API key

# Migrate (defaults to the local SQLite file if DATABASE_URL is unset)
alembic upgrade head

# Run tests
pytest

# Run app
flask --app web.app run
```

---

## Deploying

Free-forever stack for solo/cohort use: **Render** (web app) + **Neon** (Postgres,
free tier — chosen over Render's own free Postgres because that one expires after 30
days) + **GitHub Actions** (cron pipeline, instead of Render's paid-tier-only
background workers/cron jobs).

1. **Neon** — create a free project at [neon.tech](https://neon.tech), copy its
   connection string (`postgresql://...`).
2. **Render** — create a Web Service from this repo using the included
   [`render.yaml`](./render.yaml) blueprint ("New from Blueprint"). It builds with
   `pip install .`, runs `alembic upgrade head` before each start, and serves via
   `gunicorn wsgi:app`. Set these env vars in the Render dashboard (`sync: false` in
   the blueprint means Render prompts for them instead of storing a value itself):
   - `DATABASE_URL` — the Neon connection string from step 1
   - `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/)
   - `GEMINI_MODEL` — optional, defaults to `gemini-flash-latest`
3. **GitHub Actions** — add these as repo secrets (Settings → Secrets and variables →
   Actions) so [`.github/workflows/pipeline.yml`](./.github/workflows/pipeline.yml) can
   run the scrape/analyze/match/notify pipeline on its 2-hour cron:
   - `DATABASE_URL` — same Neon connection string
   - `SMTP_SENDER`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` — for
     users with `email` in their preferred channels
   - `TELEGRAM_BOT_TOKEN` — for users with `telegram` in their preferred channels

The web service only serves auth/preferences/matches/Q&A — it never runs the scrape
pipeline itself, so Render's free-tier idle sleep has no effect on data freshness.

---

## Project conventions

- **Branching:** `feature/*` → `dev` → `main`, all merges via PR
- **Commits:** Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`)
- **CI gate:** All tests must pass + coverage ≥70% before merge to `main`
- **Code style:** `black` formatter, `ruff` linter (enforced in CI)

---

## License

All rights reserved — see [LICENSE](LICENSE). Source is public for viewing, not for reuse.

---

## About

Built and maintained by [Shivam Shukla](https://github.com/shivamm-shukla).
