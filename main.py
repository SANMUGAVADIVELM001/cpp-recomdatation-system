"""CLI entry point for the AI-powered competitive programming recommendation system."""

import sys
from typing import Optional

import click
from tabulate import tabulate

from config import DEFAULT_RECOMMENDATION_COUNT
from src.api.codeforces import CodeforcesClient, CodeforcesAPIError
from src.api.leetcode import LeetCodeClient, LeetCodeAPIError
from src.analytics.performance import PerformanceAnalytics
from src.recommender.engine import RecommendationEngine
from src.storage.database import Database
from src.tracker.progress import ProgressTracker


# Shared objects (initialised once per invocation)
_db = Database()
_engine = RecommendationEngine()
_analytics = PerformanceAnalytics()
_tracker = ProgressTracker(_db)
_cf_client = CodeforcesClient()
_lc_client = LeetCodeClient()


@click.group()
def cli() -> None:
    """AI-powered competitive programming recommendation & analytics system."""


# ===========================================================================
# Codeforces commands
# ===========================================================================


@cli.group("cf")
def cf_group() -> None:
    """Commands for Codeforces."""


@cf_group.command("profile")
@click.argument("handle")
def cf_profile(handle: str) -> None:
    """Show Codeforces profile for HANDLE."""
    try:
        user = _cf_client.get_user(handle)
        rows = [
            ["Handle", user.handle],
            ["Rating", user.rating or "Unrated"],
            ["Max Rating", user.max_rating or "Unrated"],
            ["Rank", user.rank or "N/A"],
            ["Max Rank", user.max_rank or "N/A"],
            ["Contribution", user.contribution],
        ]
        click.echo(tabulate(rows, tablefmt="rounded_outline"))
    except CodeforcesAPIError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@cf_group.command("recommend")
@click.argument("handle")
@click.option(
    "--count", "-n", default=DEFAULT_RECOMMENDATION_COUNT,
    show_default=True, help="Number of problems to suggest."
)
def cf_recommend(handle: str, count: int) -> None:
    """Recommend Codeforces problems for HANDLE."""
    try:
        click.echo(f"Fetching data for '{handle}'…")
        user = _cf_client.get_user(handle)
        accepted_ids = set(_cf_client.get_accepted_problem_ids(handle))
        click.echo(f"  ✓ {len(accepted_ids)} accepted problems found.")

        problems, _ = _cf_client.get_problem_set()
        recommendations = _engine.recommend_codeforces(
            problems, accepted_ids, user.rating, n=count
        )
        if not recommendations:
            click.echo("No new recommendations found.")
            return

        rows = [
            [
                i + 1,
                p.name,
                p.rating or "?",
                ", ".join(p.tags[:3]) + ("…" if len(p.tags) > 3 else ""),
                p.url,
            ]
            for i, p in enumerate(recommendations)
        ]
        click.echo(
            tabulate(
                rows,
                headers=["#", "Problem", "Rating", "Tags", "URL"],
                tablefmt="rounded_outline",
            )
        )
    except CodeforcesAPIError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@cf_group.command("analytics")
@click.argument("handle")
def cf_analytics(handle: str) -> None:
    """Show performance analytics for a Codeforces HANDLE."""
    try:
        history = _cf_client.get_rating_history(handle)
        submissions = _cf_client.get_user_submissions(handle, count=10000)
        sub_dicts = [
            {
                "problem_id": s.problem_id,
                "verdict": s.verdict,
                "timestamp": s.timestamp,
            }
            for s in submissions
        ]

        summary = _analytics.cf_rating_summary(history)
        click.echo("\n── Rating Summary ──")
        for k, v in summary.items():
            click.echo(f"  {k.replace('_', ' ').title():25s} {v}")

        activity = _analytics.cf_submission_activity(sub_dicts, days=30)
        if activity:
            click.echo("\n── Submission Activity (last 30 days) ──")
            rows = [[d, c] for d, c in activity.items()]
            click.echo(tabulate(rows, headers=["Date", "Submissions"],
                                tablefmt="rounded_outline"))

        verdict_dist = _analytics.cf_verdict_distribution(sub_dicts)
        click.echo("\n── Verdict Distribution ──")
        for v, c in verdict_dist.items():
            click.echo(f"  {v:30s} {c}")

    except CodeforcesAPIError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@cf_group.command("streak")
@click.argument("handle")
def cf_streak(handle: str) -> None:
    """Show solving streak for a Codeforces HANDLE (uses cached data)."""
    current, longest = _tracker.calculate_streak("codeforces", handle)
    click.echo(f"Current streak : {current} day(s)")
    click.echo(f"Longest streak : {longest} day(s)")


# ===========================================================================
# LeetCode commands
# ===========================================================================


@cli.group("lc")
def lc_group() -> None:
    """Commands for LeetCode."""


@lc_group.command("profile")
@click.argument("username")
def lc_profile(username: str) -> None:
    """Show LeetCode profile for USERNAME."""
    try:
        user = _lc_client.get_user(username)
        rows = [
            ["Username", user.username],
            ["Easy Solved", user.easy_solved],
            ["Medium Solved", user.medium_solved],
            ["Hard Solved", user.hard_solved],
            ["Total Solved", user.total_solved],
            ["Acceptance Rate", f"{user.acceptance_rate}%"],
            ["Ranking", user.ranking or "N/A"],
        ]
        click.echo(tabulate(rows, tablefmt="rounded_outline"))
    except LeetCodeAPIError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@lc_group.command("recommend")
@click.argument("username")
@click.option(
    "--count", "-n", default=DEFAULT_RECOMMENDATION_COUNT,
    show_default=True, help="Number of problems to suggest."
)
@click.option(
    "--difficulty", "-d",
    type=click.Choice(["Easy", "Medium", "Hard"], case_sensitive=False),
    default=None, help="Target difficulty level."
)
def lc_recommend(username: str, count: int, difficulty: Optional[str]) -> None:
    """Recommend LeetCode problems for USERNAME."""
    try:
        click.echo(f"Fetching data for '{username}'…")
        user = _lc_client.get_user(username)
        solved = set(_lc_client.get_solved_problems(username))
        click.echo(f"  ✓ {len(solved)} solved problems found.")

        problems = _lc_client.get_problem_list(limit=500)
        diff_level: Optional[int] = None
        if difficulty:
            diff_map = {"Easy": 1, "Medium": 2, "Hard": 3}
            diff_level = diff_map[difficulty.capitalize()]
        elif user.total_solved > 0:
            # Estimate current difficulty from solved distribution
            if user.hard_solved > user.medium_solved * 0.5:
                diff_level = 3
            elif user.medium_solved > user.easy_solved * 0.3:
                diff_level = 2
            else:
                diff_level = 1

        recommendations = _engine.recommend_leetcode(
            problems, solved, current_difficulty=diff_level, n=count
        )
        if not recommendations:
            click.echo("No new recommendations found.")
            return

        rows = [
            [
                i + 1,
                p.title,
                p.difficulty,
                ", ".join(p.tags[:3]) + ("…" if len(p.tags) > 3 else ""),
                f"{p.ac_rate:.1f}%",
                p.url,
            ]
            for i, p in enumerate(recommendations)
        ]
        click.echo(
            tabulate(
                rows,
                headers=["#", "Problem", "Difficulty", "Tags", "AC Rate", "URL"],
                tablefmt="rounded_outline",
            )
        )
    except LeetCodeAPIError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@lc_group.command("analytics")
@click.argument("username")
def lc_analytics(username: str) -> None:
    """Show performance analytics for a LeetCode USERNAME."""
    try:
        user = _lc_client.get_user(username)
        solved_slugs = _lc_client.get_solved_problems(username)
        problems = _lc_client.get_problem_list(limit=500)

        breakdown = _analytics.lc_difficulty_breakdown(solved_slugs, problems)
        click.echo("\n── Difficulty Breakdown ──")
        for diff, cnt in breakdown.items():
            click.echo(f"  {diff:10s} {cnt}")

        tag_dist = _analytics.lc_tag_distribution(solved_slugs, problems)
        click.echo("\n── Top 10 Topics ──")
        top = list(tag_dist.items())[:10]
        for tag, cnt in top:
            click.echo(f"  {tag:30s} {cnt}")

        insight = _analytics.lc_acceptance_rate_insight(solved_slugs, problems)
        click.echo(
            f"\n── Acceptance Rate Insight ──\n"
            f"  Solved: {insight['solved_count']}, "
            f"Avg AC Rate: {insight['avg_ac_rate']}%"
        )

    except LeetCodeAPIError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


# ===========================================================================
# Progress / goal commands
# ===========================================================================


@cli.group("goal")
def goal_group() -> None:
    """Commands for managing learning goals."""


@goal_group.command("add")
@click.option("--platform", "-p", required=True,
              type=click.Choice(["codeforces", "leetcode"]))
@click.option("--username", "-u", required=True)
@click.option("--type", "goal_type", required=True,
              help="Goal type, e.g. 'problems_solved'.")
@click.option("--target", "-t", required=True, type=int)
@click.option("--end-date", default=None, help="YYYY-MM-DD deadline.")
def add_goal(
    platform: str, username: str, goal_type: str, target: int,
    end_date: Optional[str]
) -> None:
    """Add a learning goal."""
    goal_id = _tracker.add_goal(platform, username, goal_type, target,
                                end_date=end_date)
    click.echo(f"Goal #{goal_id} added.")


@goal_group.command("list")
@click.option("--platform", "-p", required=True,
              type=click.Choice(["codeforces", "leetcode"]))
@click.option("--username", "-u", required=True)
def list_goals(platform: str, username: str) -> None:
    """List goals for a user."""
    goals = _tracker.get_goals(platform, username)
    if not goals:
        click.echo("No goals found.")
        return
    rows = [
        [g["id"], g["goal_type"], g["target"],
         g["start_date"], g["end_date"] or "–",
         "✓" if g["completed"] else "○"]
        for g in goals
    ]
    click.echo(
        tabulate(rows,
                 headers=["ID", "Type", "Target", "Start", "End", "Done"],
                 tablefmt="rounded_outline")
    )


@goal_group.command("complete")
@click.argument("goal_id", type=int)
def complete_goal(goal_id: int) -> None:
    """Mark goal GOAL_ID as completed."""
    _tracker.complete_goal(goal_id)
    click.echo(f"Goal #{goal_id} marked as completed.")


if __name__ == "__main__":
    cli()
