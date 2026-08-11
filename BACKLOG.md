# Backlog

Parking lot for everything intentionally deferred — not forgotten, not accidental scope
cuts. Each item notes *why* it's deferred and what would trigger picking it up.

## Phase C — action-taking agents (design-only for now)

The biggest deferred item. Explicitly: **do not build any part of this until Phase A is
done and this section has been expanded into a real design**, per the project's phased
roadmap in [ARCHITECTURE.md](./ARCHITECTURE.md#phase-c--action-taking-agents-design-now-do-not-build).

What it eventually covers:
- Auto-apply to a matched internship on the user's behalf.
- Auto-message a recruiter (e.g. a templated follow-up after applying).
- Any other action that changes real-world state outside TalentScope's own database.

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
- Resume matching / application tracking.
- Payments or premium tiers.
- SMS / push notifications. Same note as sources above — this is a new `Notifier`
  implementation, not a restructure, whenever it's picked up.

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

- Scheduler process topology — in-process APScheduler inside the Flask app vs. a small
  separate scheduler process. Needs a decision before build sequence step 8.
