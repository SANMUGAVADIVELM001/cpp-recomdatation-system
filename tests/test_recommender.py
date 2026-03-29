"""Tests for the recommendation engine."""

import pytest

from src.models.problem import CodeforcesProblem, LeetCodeProblem
from src.recommender.engine import RecommendationEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cf_problem(pid: str, rating: int, tags: list) -> CodeforcesProblem:
    contest_id = int(pid[:-1])
    index = pid[-1]
    return CodeforcesProblem(
        contest_id=contest_id,
        index=index,
        name=f"Problem {pid}",
        rating=rating,
        tags=tags,
    )


def _lc_problem(slug: str, difficulty: str, tags: list, ac_rate: float = 50.0) -> LeetCodeProblem:
    return LeetCodeProblem(
        title=slug.replace("-", " ").title(),
        title_slug=slug,
        difficulty=difficulty,
        tags=tags,
        ac_rate=ac_rate,
    )


# ---------------------------------------------------------------------------
# Codeforces recommendations
# ---------------------------------------------------------------------------

class TestCodeforcesRecommendations:
    def setup_method(self):
        self.engine = RecommendationEngine()

    def test_excludes_solved_problems(self):
        problems = [
            _cf_problem("1A", 800, ["math"]),
            _cf_problem("2A", 900, ["dp"]),
        ]
        recs = self.engine.recommend_codeforces(
            problems, accepted_ids={"1A"}, n=10
        )
        ids = [p.problem_id for p in recs]
        assert "1A" not in ids
        assert "2A" in ids

    def test_returns_at_most_n_problems(self):
        problems = [_cf_problem(f"{i}A", 800 + i * 100, ["math"]) for i in range(1, 20)]
        recs = self.engine.recommend_codeforces(problems, accepted_ids=set(), n=5)
        assert len(recs) <= 5

    def test_fallback_when_few_accepted(self):
        problems = [
            _cf_problem("1A", 800, ["math"]),
            _cf_problem("2A", 2000, ["graphs"]),
        ]
        recs = self.engine.recommend_codeforces(
            problems, accepted_ids=set(), current_rating=900, n=10
        )
        # Should prefer the problem in the rating band (800)
        assert recs[0].problem_id == "1A"

    def test_returns_empty_when_all_solved(self):
        problems = [_cf_problem("1A", 800, ["math"])]
        recs = self.engine.recommend_codeforces(
            problems, accepted_ids={"1A"}, n=5
        )
        assert recs == []

    def test_ml_recommend_uses_tags(self):
        # Solved many math problems → should recommend more math
        solved = [_cf_problem(f"{i}A", 1000, ["math"]) for i in range(1, 10)]
        math_unsolved = _cf_problem("20A", 1100, ["math"])
        dp_unsolved = _cf_problem("21A", 1100, ["dp", "graphs"])
        all_problems = solved + [math_unsolved, dp_unsolved]
        accepted_ids = {p.problem_id for p in solved}

        recs = self.engine.recommend_codeforces(
            all_problems, accepted_ids, current_rating=1000, n=2
        )
        # First recommendation should be math problem
        assert recs[0].problem_id == "20A"


# ---------------------------------------------------------------------------
# LeetCode recommendations
# ---------------------------------------------------------------------------

class TestLeetCodeRecommendations:
    def setup_method(self):
        self.engine = RecommendationEngine()

    def test_excludes_solved_problems(self):
        problems = [
            _lc_problem("two-sum", "Easy", ["Array"]),
            _lc_problem("three-sum", "Medium", ["Array"]),
        ]
        recs = self.engine.recommend_leetcode(
            problems, solved_slugs={"two-sum"}, n=10
        )
        slugs = [p.title_slug for p in recs]
        assert "two-sum" not in slugs
        assert "three-sum" in slugs

    def test_excludes_paid_only(self):
        problems = [
            _lc_problem("free-problem", "Easy", ["Array"]),
            LeetCodeProblem(
                title="Paid Problem", title_slug="paid-problem",
                difficulty="Easy", tags=["Array"], is_paid_only=True
            ),
        ]
        recs = self.engine.recommend_leetcode(problems, solved_slugs=set(), n=10)
        slugs = [p.title_slug for p in recs]
        assert "paid-problem" not in slugs

    def test_returns_at_most_n_problems(self):
        problems = [
            _lc_problem(f"problem-{i}", "Easy", ["Array"]) for i in range(20)
        ]
        recs = self.engine.recommend_leetcode(problems, solved_slugs=set(), n=5)
        assert len(recs) <= 5

    def test_fallback_with_difficulty_hint(self):
        problems = [
            _lc_problem("easy-one", "Easy", ["Array"], ac_rate=70.0),
            _lc_problem("hard-one", "Hard", ["DP"], ac_rate=20.0),
        ]
        recs = self.engine.recommend_leetcode(
            problems, solved_slugs=set(), current_difficulty=1, n=5
        )
        # Easy problem should come first when current_difficulty is Easy
        assert recs[0].title_slug == "easy-one"

    def test_ml_recommend_uses_tags(self):
        solved = [_lc_problem(f"array-problem-{i}", "Easy", ["Array", "Hash Table"])
                  for i in range(1, 8)]
        array_unsolved = _lc_problem("array-new", "Easy", ["Array"])
        dp_unsolved = _lc_problem("dp-new", "Medium", ["Dynamic Programming"])
        all_problems = solved + [array_unsolved, dp_unsolved]
        solved_slugs = {p.title_slug for p in solved}

        recs = self.engine.recommend_leetcode(
            all_problems, solved_slugs, current_difficulty=1, n=2
        )
        # Array-tagged problem should score higher
        assert recs[0].title_slug == "array-new"
