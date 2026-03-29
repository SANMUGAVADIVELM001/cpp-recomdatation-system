"""Tests for performance analytics."""

from src.analytics.performance import PerformanceAnalytics
from src.models.problem import CodeforcesProblem, LeetCodeProblem


def _cf_problem(pid: str, rating: int, tags: list) -> CodeforcesProblem:
    contest_id = int(pid[:-1])
    index = pid[-1]
    return CodeforcesProblem(
        contest_id=contest_id, index=index, name=pid,
        rating=rating, tags=tags
    )


def _lc_problem(slug: str, diff: str, tags: list, ac: float = 50.0) -> LeetCodeProblem:
    return LeetCodeProblem(title=slug, title_slug=slug, difficulty=diff,
                           tags=tags, ac_rate=ac)


class TestCFRatingSummary:
    def setup_method(self):
        self.analytics = PerformanceAnalytics()

    def test_empty_history(self):
        result = self.analytics.cf_rating_summary([])
        assert result["contests"] == 0
        assert result["current_rating"] is None

    def test_single_contest(self):
        history = [{
            "contest_id": 1, "contest_name": "X", "rank": 100,
            "old_rating": 1500, "new_rating": 1550, "timestamp": 1000
        }]
        result = self.analytics.cf_rating_summary(history)
        assert result["contests"] == 1
        assert result["current_rating"] == 1550
        assert result["peak_rating"] == 1550
        assert result["avg_delta"] == 50.0

    def test_multiple_contests(self):
        history = [
            {"contest_id": 1, "old_rating": 1000, "new_rating": 1100, "rank": 1,
             "contest_name": "A", "timestamp": 1},
            {"contest_id": 2, "old_rating": 1100, "new_rating": 1050, "rank": 10,
             "contest_name": "B", "timestamp": 2},
        ]
        result = self.analytics.cf_rating_summary(history)
        assert result["current_rating"] == 1050
        assert result["peak_rating"] == 1100
        assert result["positive_rounds"] == 1
        assert result["negative_rounds"] == 1


class TestCFTagDistribution:
    def setup_method(self):
        self.analytics = PerformanceAnalytics()

    def test_counts_tags_for_accepted(self):
        problems = [
            _cf_problem("1A", 800, ["math", "greedy"]),
            _cf_problem("2A", 900, ["dp"]),
        ]
        submissions = [
            {"problem_id": "1A", "verdict": "OK", "timestamp": 1},
            {"problem_id": "2A", "verdict": "WRONG_ANSWER", "timestamp": 2},
        ]
        dist = self.analytics.cf_tag_distribution(submissions, problems)
        assert dist.get("math") == 1
        assert dist.get("greedy") == 1
        assert "dp" not in dist


class TestCFDifficultyDistribution:
    def setup_method(self):
        self.analytics = PerformanceAnalytics()

    def test_buckets_by_rating(self):
        problems = [
            _cf_problem("1A", 800, []),
            _cf_problem("2A", 1200, []),
        ]
        submissions = [
            {"problem_id": "1A", "verdict": "OK", "timestamp": 1},
            {"problem_id": "2A", "verdict": "OK", "timestamp": 2},
        ]
        dist = self.analytics.cf_difficulty_distribution(submissions, problems)
        assert dist.get("800-899") == 1
        assert dist.get("1200-1299") == 1


class TestLCDifficultyBreakdown:
    def setup_method(self):
        self.analytics = PerformanceAnalytics()

    def test_counts_by_difficulty(self):
        problems = [
            _lc_problem("p1", "Easy", []),
            _lc_problem("p2", "Easy", []),
            _lc_problem("p3", "Medium", []),
            _lc_problem("p4", "Hard", []),
        ]
        solved = ["p1", "p2", "p3"]
        breakdown = self.analytics.lc_difficulty_breakdown(solved, problems)
        assert breakdown["Easy"] == 2
        assert breakdown["Medium"] == 1
        assert breakdown["Hard"] == 0


class TestLCTagDistribution:
    def setup_method(self):
        self.analytics = PerformanceAnalytics()

    def test_counts_tags(self):
        problems = [
            _lc_problem("p1", "Easy", ["Array", "Hash Table"]),
            _lc_problem("p2", "Easy", ["Array"]),
        ]
        dist = self.analytics.lc_tag_distribution(["p1", "p2"], problems)
        assert dist["Array"] == 2
        assert dist["Hash Table"] == 1


class TestCombinedProfileSummary:
    def setup_method(self):
        self.analytics = PerformanceAnalytics()

    def test_combined_summary(self):
        result = self.analytics.combined_profile_summary(
            cf_rating=1800, cf_accepted_count=200,
            lc_easy=50, lc_medium=30, lc_hard=10
        )
        assert result["codeforces_rating"] == 1800
        assert result["leetcode_total_solved"] == 90
        assert result["leetcode_weighted_score"] == 50 * 1 + 30 * 2 + 10 * 3
