"""Learning progress tracker.

Tracks daily solving streaks, topic mastery, and goal progress across
Codeforces and LeetCode.
"""

from collections import Counter
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from src.storage.database import Database


class ProgressTracker:
    """Track and report learning progress for a user."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Daily log
    # ------------------------------------------------------------------

    def record_daily_activity(
        self,
        platform: str,
        username: str,
        solved_count: int,
        activity_date: Optional[date] = None,
    ) -> None:
        """Record *solved_count* problems solved on *activity_date*."""
        d = activity_date or date.today()
        self._db.log_daily_solved(platform, username, str(d), solved_count)

    def get_daily_activity(
        self, platform: str, username: str
    ) -> List[Dict]:
        """Return chronological daily solving activity."""
        return self._db.get_daily_log(platform, username)

    # ------------------------------------------------------------------
    # Streak calculation
    # ------------------------------------------------------------------

    def calculate_streak(
        self, platform: str, username: str
    ) -> Tuple[int, int]:
        """Return (current_streak, longest_streak) in days."""
        logs = self._db.get_daily_log(platform, username)
        if not logs:
            return (0, 0)

        active_days = {
            row["date"] for row in logs if row["solved"] > 0
        }
        if not active_days:
            return (0, 0)

        today = date.today()
        # Current streak: consecutive days ending today (or yesterday)
        current = 0
        check = today
        while str(check) in active_days:
            current += 1
            check -= timedelta(days=1)
        if current == 0:
            # Try starting from yesterday
            check = today - timedelta(days=1)
            while str(check) in active_days:
                current += 1
                check -= timedelta(days=1)

        # Longest streak
        sorted_days = sorted(active_days)
        longest = 1
        run = 1
        for i in range(1, len(sorted_days)):
            prev = date.fromisoformat(sorted_days[i - 1])
            curr = date.fromisoformat(sorted_days[i])
            if (curr - prev).days == 1:
                run += 1
                longest = max(longest, run)
            else:
                run = 1

        return (current, longest)

    # ------------------------------------------------------------------
    # Goals
    # ------------------------------------------------------------------

    def add_goal(
        self,
        platform: str,
        username: str,
        goal_type: str,
        target: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> int:
        """Add a new progress goal.  Returns the goal ID."""
        sd = start_date or str(date.today())
        return self._db.add_goal(
            platform, username, goal_type, target, sd, end_date
        )

    def get_goals(self, platform: str, username: str) -> List[Dict]:
        """Return all goals for the given platform/user."""
        return self._db.get_goals(platform, username)

    def complete_goal(self, goal_id: int) -> None:
        """Mark a goal as completed."""
        self._db.mark_goal_completed(goal_id)

    def evaluate_goals(
        self,
        platform: str,
        username: str,
        current_solved: int,
    ) -> List[Dict]:
        """Check which goals have been met and mark them complete."""
        goals = self._db.get_goals(platform, username)
        results = []
        for g in goals:
            if g["completed"]:
                results.append({**g, "status": "completed"})
                continue
            if current_solved >= g["target"]:
                self._db.mark_goal_completed(g["id"])
                results.append({**g, "status": "newly_completed"})
            else:
                progress = round(current_solved / g["target"] * 100, 1)
                results.append({**g, "status": "in_progress", "progress_pct": progress})
        return results

    # ------------------------------------------------------------------
    # Topic mastery
    # ------------------------------------------------------------------

    def topic_mastery(
        self, tag_distribution: Dict[str, int], top_n: int = 10
    ) -> List[Dict]:
        """Return top-*n* mastered topics with solved counts.

        A topic is considered 'mastered' once >= 10 problems are solved in it.
        """
        MASTERY_THRESHOLD = 10
        sorted_tags = sorted(
            tag_distribution.items(), key=lambda x: x[1], reverse=True
        )[:top_n]
        return [
            {
                "topic": tag,
                "solved": count,
                "mastered": count >= MASTERY_THRESHOLD,
            }
            for tag, count in sorted_tags
        ]

    # ------------------------------------------------------------------
    # Weekly summary
    # ------------------------------------------------------------------

    def weekly_summary(
        self, platform: str, username: str
    ) -> Dict:
        """Return solved counts for each of the last 7 days."""
        logs = self._db.get_daily_log(platform, username)
        log_map = {row["date"]: row["solved"] for row in logs}
        today = date.today()
        result = {}
        for i in range(6, -1, -1):
            d = str(today - timedelta(days=i))
            result[d] = log_map.get(d, 0)
        return result
