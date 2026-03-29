"""Tests for the progress tracker."""

import os
import tempfile
from datetime import date, timedelta

import pytest

from src.storage.database import Database
from src.tracker.progress import ProgressTracker


@pytest.fixture()
def tracker():
    """Return a ProgressTracker backed by a temporary in-memory database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = Database(db_path)
    t = ProgressTracker(db)
    yield t
    os.unlink(db_path)


# ---------------------------------------------------------------------------
# Daily activity & streak
# ---------------------------------------------------------------------------

class TestStreak:
    def test_no_activity_returns_zero(self, tracker):
        current, longest = tracker.calculate_streak("codeforces", "user1")
        assert current == 0
        assert longest == 0

    def test_single_day_streak(self, tracker):
        tracker.record_daily_activity("codeforces", "user1", 3,
                                      activity_date=date.today())
        current, longest = tracker.calculate_streak("codeforces", "user1")
        assert current == 1
        assert longest == 1

    def test_consecutive_days_streak(self, tracker):
        today = date.today()
        for delta in range(3):
            tracker.record_daily_activity(
                "codeforces", "user1", 2,
                activity_date=today - timedelta(days=delta)
            )
        current, longest = tracker.calculate_streak("codeforces", "user1")
        assert current == 3
        assert longest == 3

    def test_broken_streak(self, tracker):
        today = date.today()
        # Days: today, yesterday, gap, 3 days ago
        for delta in [0, 1, 3]:
            tracker.record_daily_activity(
                "codeforces", "user1", 1,
                activity_date=today - timedelta(days=delta)
            )
        current, longest = tracker.calculate_streak("codeforces", "user1")
        assert current == 2  # today + yesterday
        assert longest == 2


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------

class TestGoals:
    def test_add_and_list_goals(self, tracker):
        goal_id = tracker.add_goal("leetcode", "user2", "problems_solved", 100)
        goals = tracker.get_goals("leetcode", "user2")
        assert len(goals) == 1
        assert goals[0]["id"] == goal_id
        assert goals[0]["target"] == 100
        assert goals[0]["completed"] == 0

    def test_complete_goal(self, tracker):
        goal_id = tracker.add_goal("leetcode", "user2", "problems_solved", 50)
        tracker.complete_goal(goal_id)
        goals = tracker.get_goals("leetcode", "user2")
        assert goals[0]["completed"] == 1

    def test_evaluate_goals_marks_completed(self, tracker):
        tracker.add_goal("leetcode", "user3", "problems_solved", 10)
        results = tracker.evaluate_goals("leetcode", "user3", current_solved=15)
        assert results[0]["status"] == "newly_completed"

    def test_evaluate_goals_shows_progress(self, tracker):
        tracker.add_goal("leetcode", "user3", "problems_solved", 100)
        results = tracker.evaluate_goals("leetcode", "user3", current_solved=40)
        assert results[0]["status"] == "in_progress"
        assert results[0]["progress_pct"] == 40.0


# ---------------------------------------------------------------------------
# Topic mastery
# ---------------------------------------------------------------------------

class TestTopicMastery:
    def test_mastered_when_above_threshold(self, tracker):
        dist = {"Array": 15, "DP": 5, "Graph": 12}
        mastery = tracker.topic_mastery(dist, top_n=3)
        by_topic = {m["topic"]: m for m in mastery}
        assert by_topic["Array"]["mastered"] is True
        assert by_topic["Graph"]["mastered"] is True
        assert by_topic["DP"]["mastered"] is False

    def test_respects_top_n(self, tracker):
        dist = {f"topic_{i}": i for i in range(20)}
        mastery = tracker.topic_mastery(dist, top_n=5)
        assert len(mastery) == 5


# ---------------------------------------------------------------------------
# Weekly summary
# ---------------------------------------------------------------------------

class TestWeeklySummary:
    def test_returns_seven_days(self, tracker):
        summary = tracker.weekly_summary("leetcode", "user4")
        assert len(summary) == 7

    def test_reflects_recorded_activity(self, tracker):
        today = date.today()
        tracker.record_daily_activity("leetcode", "user4", 5, activity_date=today)
        summary = tracker.weekly_summary("leetcode", "user4")
        assert summary[str(today)] == 5
