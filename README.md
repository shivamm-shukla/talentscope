# TalentScope

> An internship intelligence tool for students — scrapes job boards, sends matched alerts, and surfaces skill/market trends. Built with a full SDET-grade test suite and CI pipeline.

[![CI](https://img.shields.io/badge/CI-pending-lightgrey.svg)](https://github.com/shivamm-shukla/talentscope/actions)
[![Coverage](https://img.shields.io/badge/coverage-pending-lightgrey.svg)](#)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## Status

🚧 **Active development.** This is a rebuild of [JobTrendTracker](https://github.com/shivamm-shukla) with a production-grade architecture, full test pyramid, and CI/CD. See the [roadmap](#roadmap) for current progress.

The project is intentionally built like it has real users — full auth, real notifications, deployed publicly — but is being validated with a closed cohort (myself + 2-3 batchmates) before opening signups.

---

## Why this project exists

JobTrendTracker (v1) solved the problem but had three weaknesses I wanted to fix in a rebuild:

1. **No automated tests.** Scrapers and APIs need test suites — without them, every Internshala layout change is a silent failure.
2. **CSV-based storage.** Doesn't scale, can't be queried, breaks on concurrent writes.
3. **No CI.** Bugs only got caught when something visibly broke in production.

TalentScope addresses each of these explicitly. The product value is for students; the engineering rigor is for me.

---

## What it does

### For users (students looking for internships)

- **Daily-curated internship feed** scraped from Internshala (Playwright) and Remotive API
- **Personalised alerts** via email and Telegram, matched against user-set skills, location, and stipend preferences
- **Market trends dashboard** — which skills are rising, which cities are hiring, stipend distributions
- **Natural-language Q&A** — ask "What skills are trending for ML interns in Bangalore?" and get a grounded answer powered by Google Gemini over the live job database

### For me (the engineer)

- A real codebase demonstrating SDET fundamentals end-to-end: unit, integration, API contract, and Playwright E2E tests
- A CI pipeline that gates merges on tests passing
- Structured JSON logging suitable for log-analysis tooling
- A deployable Flask app with MySQL persistence and Alembic migrations

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
        │     MySQL     │◄─────┤   Flask Web App     │
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
| Web | Flask | Lightweight, well-tested, matches scope |
| ORM | SQLAlchemy + Alembic | Same code runs against MySQL (prod) and SQLite (tests) |
| DB | MySQL 8 / SQLite (test) | Production-realistic; tests stay fast |
| Scraping | Playwright + pytest-playwright | Handles dynamic Internshala pages |
| Scheduling | APScheduler | In-process, no separate worker needed for v1 |
| Auth | Flask-Login + bcrypt | Standard, well-understood |
| Email | Flask-Mail (Gmail SMTP) | Free tier, sufficient for cohort scale |
| Telegram | python-telegram-bot | Free, students already use it |
| AI | google-generativeai (Gemini) | Free tier sufficient for Q&A |
| Testing | pytest, pytest-cov, pytest-flask, factory_boy, jsonschema | Industry-standard test stack |
| CI | GitHub Actions | Free for public repos, runs on every push |
| Logging | structlog (JSON) | Queryable logs — relevant to SDET log-analysis skills |
| Deployment | Render | Free tier, MySQL add-on available |

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
- [ ] MySQL schema + SQLAlchemy models + Alembic migrations
- [ ] GitHub Actions CI pipeline
- [ ] Playwright scraper (Internshala) with Page Object Model
- [ ] Remotive API client
- [ ] Skill extractor + analyzer
- [ ] Flask auth + user preferences
- [ ] Email notifier
- [ ] Telegram notifier
- [ ] Gemini Q&A endpoint
- [ ] pytest suite: unit, integration, API, E2E
- [ ] ≥70% coverage
- [ ] Structured JSON logging
- [ ] Render deployment

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

> Setup instructions will be finalised once the core skeleton is committed. The intended developer experience:

```bash
# Clone and set up
git clone https://github.com/shivamm-shukla/talentscope.git
cd talentscope
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# Configure
cp .env.example .env
# edit .env with DB URL, Gmail credentials, Telegram token, Gemini API key

# Migrate
alembic upgrade head

# Run tests
pytest

# Run app
flask --app talentscope run
```

---

## Project conventions

- **Branching:** `feature/*` → `dev` → `main`, all merges via PR
- **Commits:** Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`)
- **CI gate:** All tests must pass + coverage ≥70% before merge to `main`
- **Code style:** `black` formatter, `ruff` linter (enforced in CI)

---

## License

MIT — see [LICENSE](LICENSE).

---

## About

Built by [Shivam Shukla](https://github.com/shivamm-shukla) as a deliberate exercise in production-grade software engineering and SDET practice. Feedback and code review welcome via GitHub issues.
