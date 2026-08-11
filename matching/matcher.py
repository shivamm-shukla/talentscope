"""Deterministic matching between normalized jobs and user preferences."""

from core.models import JobPosting, MatchedJob, UserPreferences


def _normalized(values: tuple[str, ...]) -> set[str]:
    return {value.casefold().strip() for value in values if value.strip()}


def match_jobs(
    preferences: UserPreferences, jobs: list[JobPosting]
) -> list[MatchedJob]:
    """Return jobs ranked by skills, location, and stipend evidence."""
    desired_skills = _normalized(preferences.skills)
    desired_locations = _normalized(preferences.locations)
    matches: list[MatchedJob] = []

    for job in jobs:
        reasons: list[str] = []
        score = 0.0
        job_skills = _normalized(job.skills)
        common_skills = desired_skills & job_skills
        if desired_skills and common_skills:
            score += 0.6 * len(common_skills) / len(desired_skills)
            reasons.append("skills: " + ", ".join(sorted(common_skills)))

        location_matches = (
            not desired_locations or job.location.casefold() in desired_locations
        )
        if location_matches:
            score += 0.25
            if desired_locations:
                reasons.append(f"location: {job.location}")

        stipend_matches = (
            preferences.minimum_stipend is None
            or job.salary_numeric is None
            or job.salary_numeric >= preferences.minimum_stipend
        )
        if stipend_matches:
            score += 0.15
            if (
                preferences.minimum_stipend is not None
                and job.salary_numeric is not None
            ):
                reasons.append("stipend meets minimum")

        if score > 0 and location_matches and stipend_matches:
            matches.append(
                MatchedJob(job=job, score=round(score, 3), reasons=tuple(reasons))
            )

    return sorted(matches, key=lambda match: (-match.score, match.job.title.casefold()))
