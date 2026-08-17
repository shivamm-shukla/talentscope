# Backlog

Parking lot for everything intentionally deferred — not forgotten, not accidental scope
cuts. Each item notes *why* it's deferred and what would trigger picking it up.

## Phase C — action-taking agents (design-only for now)

The biggest deferred item. I'm not touching this until Phase A is done and I've actually
sat down and designed it properly — see the phased roadmap in
[ARCHITECTURE.md](./ARCHITECTURE.md#phase-c--action-taking-agents-not-building-this-yet).

What it eventually covers:
- Auto-apply to a matched internship on the user's behalf.
- Auto-message a recruiter (e.g. a templated follow-up after applying).
- Any other action that changes real-world state outside Santa's own database.

Why it's deferred: this requires a trust/safety/approval design that doesn't exist yet —
at minimum: explicit per-action user consent (not a blanket "yes, act for me" toggle),
a review/undo window before an action is irreversible, rate limiting to prevent
account bans on the target sites, and clear liability/ToS considerations for automating
actions against third-party platforms (Internshala's terms, recruiter platforms) that
haven't been reviewed. None of that should be designed under time pressure while also
building Phase A.

What Phase B already does to keep this option open, so picking it up later doesn't
require reopening `sources/`, `notifications/`, or `web/`:
- All outbound side effects route through a narrow `Notifier`-shaped interface, not ad
  hoc calls scattered through the codebase.
- An `action_log` table exists from day one, even though only notification sends
  populate it until Phase C.
- The Phase A agent's toolset is read-only by construction (query tools only) — there is
  no code path in Phase A that can be repurposed into an action by accident.

Trigger to pick this up: after Phase A has been live long enough to trust its judgment on
*what* to recommend, and after the approval/trust layer has had a dedicated design pass
(not squeezed into a sprint alongside other work).

## v2 items carried over from the original README

These were called out as intentional v1 cuts and remain deferred, unchanged by this
rebuild:

- Public open signups (stays closed-cohort until the core pipeline has proven reliable).
- Mobile app.
- Sources beyond Internshala + Remotive. Note: the module boundary
  (`JobSource` in `core/interfaces.py`) makes adding a source a contained change
  whenever this is picked up — see ARCHITECTURE.md's source-swap example.
- Payments or premium tiers.
- SMS / push notifications. Same note as sources above — this is a new `Notifier`
  implementation, not a restructure, whenever it's picked up.

## Referral finder — dropped, not deferred

Considered as part of the scout feature roadmap alongside the application tracker,
ghost-job detection, company briefs, response-rate tracking, and deadline reminders —
all of which shipped. Referral finder didn't, and isn't parked as "later," because
there's no usable data source for it today: no followers/connections data exists
anywhere in this codebase (`integrations/github/client.py` only calls the repos
endpoint, never `/followers`/`/following`; LinkedIn import never parses a
Connections.csv), and even with that data, "who works at company X" isn't reliably
derivable from a public GitHub profile's employer field. Revisit only if a real
employer-affiliation data source appears — not worth a scoped-down/hedged version in
the meantime.

## Deadline countdown — resolved (was previously a "needs investigation" item)

Earlier planning flagged that `jobs.expires_at` is a synthetic retention estimate
(`posted_at + 45/60 days`), not a real deadline, and explicitly held off building a
countdown against it. That investigation is done: Remotive has no deadline field at
all (checked live); Internshala's *detail* page does, via a JobPosting JSON-LD
`validThrough` field (confirmed against 50 live postings — 39 had a parseable
deadline). Shipped as `jobs.deadline_at` (Internshala-only, always `NULL` for
Remotive) plus a one-time reminder per tracked application within a 3-day window —
see ARCHITECTURE.md's data model section.

## Infrastructure items deferred by design, not oversight

- **Job/event queue (Celery+Redis, RQ, or similar).** Deferred per
  [ARCHITECTURE.md's orchestration section](./ARCHITECTURE.md#orchestration-is-a-jobevent-queue-needed-now) —
  APScheduler + independently-runnable workers is sufficient at cohort scale. Revisit
  when scrape/analyze volume outgrows a single scheduled run, or when Phase A needs
  non-blocking multi-step tool calls from a web request.
- **Splitting `workers/` into separately-deployed processes**, or moving `ai/` behind its
  own service. Not needed while running on Render at cohort scale; the module boundaries
  make this a deployment change later, not a code restructure.

## Open design questions surfaced during planning

Carried from ARCHITECTURE.md's open questions so they don't get lost:

- Scheduler process topology — resolved: separate process
  (`workers/scheduler.py`). See ARCHITECTURE.md's resolved implementation decisions.
