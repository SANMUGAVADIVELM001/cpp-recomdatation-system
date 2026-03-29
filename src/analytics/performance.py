"""Performance analytics for Codeforces and LeetCode."""

from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from src.models.problem import CodeforcesProblem, LeetCodeProblem


class PerformanceAnalytics:
    """Compute statistics and insights from submission / rating data."""

    # ------------------------------------------------------------------
    # Codeforces analytics
    # ------------------------------------------------------------------

    def cf_rating_summary(
        self, history: List[Dict]
    ) -> Dict:
        """Return summary statistics from a user's rating history."""
        if not history:
            return {"contests": 0, "current_rating": None, "peak_rating": None,
                    "lowest_rating": None, "avg_delta": None}
        ratings = [e["new_rating"] for e in history]
        deltas = [e["new_rating"] - e["old_rating"] for e in history]
        return {
            "contests": len(history),
            "current_rating": ratings[-1],
            "peak_rating": max(ratings),
            "lowest_rating": min(ratings),
            "avg_delta": round(sum(deltas) / len(deltas), 2),
            "positive_rounds": sum(1 for d in deltas if d > 0),
            "negative_rounds": sum(1 for d in deltas if d < 0),
        }

    def cf_tag_distribution(
        self, submissions: List[Dict], problems: List[CodeforcesProblem]
    ) -> Dict[str, int]:
        """Return count of accepted problems per tag."""
        prob_map = {p.problem_id: p for p in problems}
        accepted_ids = {
            s["problem_id"] for s in submissions if s["verdict"] == "OK"
        }
        tag_counter: Counter = Counter()
        for pid in accepted_ids:
            prob = prob_map.get(pid)
            if prob:
                tag_counter.update(prob.tags)
        return dict(tag_counter.most_common())

    def cf_difficulty_distribution(
        self,
        submissions: List[Dict],
        problems: List[CodeforcesProblem],
    ) -> Dict[str, int]:
        """Return accepted problem counts bucketed by rating band."""
        prob_map = {p.problem_id: p for p in problems}
        accepted_ids = {
            s["problem_id"] for s in submissions if s["verdict"] == "OK"
        }
        buckets: Counter = Counter()
        for pid in accepted_ids:
            prob = prob_map.get(pid)
            if prob and prob.rating is not None:
                band = (prob.rating // 100) * 100
                buckets[f"{band}-{band + 99}"] += 1
            elif prob:
                buckets["Unrated"] += 1
        return dict(sorted(buckets.items()))

    def cf_submission_activity(
        self, submissions: List[Dict], days: int = 30
    ) -> Dict[str, int]:
        """Return daily submission counts for the last *days* days."""
        now = datetime.now(tz=timezone.utc).timestamp()
        cutoff = now - days * 86400
        recent = [s for s in submissions if s["timestamp"] >= cutoff]
        day_counter: Counter = Counter()
        for s in recent:
            day = datetime.fromtimestamp(
                s["timestamp"], tz=timezone.utc
            ).strftime("%Y-%m-%d")
            day_counter[day] += 1
        return dict(sorted(day_counter.items()))

    def cf_verdict_distribution(
        self, submissions: List[Dict]
    ) -> Dict[str, int]:
        """Return count per verdict type."""
        counter: Counter = Counter(s["verdict"] for s in submissions)
        return dict(counter.most_common())

    # ------------------------------------------------------------------
    # LeetCode analytics
    # ------------------------------------------------------------------

    def lc_difficulty_breakdown(
        self, solved_slugs: List[str], problems: List[LeetCodeProblem]
    ) -> Dict[str, int]:
        """Return solved count per difficulty level."""
        slug_set = set(solved_slugs)
        solved = [p for p in problems if p.title_slug in slug_set]
        counter: Counter = Counter(p.difficulty for p in solved)
        return {"Easy": counter["Easy"], "Medium": counter["Medium"],
                "Hard": counter["Hard"]}

    def lc_tag_distribution(
        self, solved_slugs: List[str], problems: List[LeetCodeProblem]
    ) -> Dict[str, int]:
        """Return solved count per topic tag."""
        slug_set = set(solved_slugs)
        solved = [p for p in problems if p.title_slug in slug_set]
        counter: Counter = Counter()
        for p in solved:
            counter.update(p.tags)
        return dict(counter.most_common())

    def lc_acceptance_rate_insight(
        self, solved_slugs: List[str], problems: List[LeetCodeProblem]
    ) -> Dict:
        """Return insight on average acceptance rate of solved problems."""
        slug_set = set(solved_slugs)
        solved = [p for p in problems if p.title_slug in slug_set and p.ac_rate > 0]
        if not solved:
            return {"solved_count": 0, "avg_ac_rate": None}
        avg = round(sum(p.ac_rate for p in solved) / len(solved), 2)
        return {"solved_count": len(solved), "avg_ac_rate": avg}

    # ------------------------------------------------------------------
    # Combined analytics
    # ------------------------------------------------------------------

    def combined_profile_summary(
        self,
        cf_rating: Optional[int],
        cf_accepted_count: int,
        lc_easy: int,
        lc_medium: int,
        lc_hard: int,
    ) -> Dict:
        """High-level combined summary across both platforms."""
        lc_total = lc_easy + lc_medium + lc_hard
        lc_weighted = lc_easy * 1 + lc_medium * 2 + lc_hard * 3
        return {
            "codeforces_rating": cf_rating,
            "codeforces_accepted": cf_accepted_count,
            "leetcode_total_solved": lc_total,
            "leetcode_easy": lc_easy,
            "leetcode_medium": lc_medium,
            "leetcode_hard": lc_hard,
            "leetcode_weighted_score": lc_weighted,
        }
