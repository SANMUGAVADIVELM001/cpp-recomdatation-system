"""AI-powered problem recommendation engine.

Uses a content-based filtering approach backed by TF-IDF tag vectors and
nearest-neighbour search.  When a user has fewer than MIN_SOLVED_FOR_ML
accepted problems the engine falls back to a simpler difficulty-band filter.
"""

from typing import List, Optional, Set

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import (
    DEFAULT_RECOMMENDATION_COUNT,
    MAX_RECOMMENDATION_COUNT,
    MIN_SOLVED_FOR_ML,
    RATING_BAND,
)
from src.models.problem import CodeforcesProblem, LeetCodeProblem


class RecommendationEngine:
    """Content-based recommendation engine for competitive programming problems."""

    # ------------------------------------------------------------------
    # Codeforces recommendations
    # ------------------------------------------------------------------

    def recommend_codeforces(
        self,
        all_problems: List[CodeforcesProblem],
        accepted_ids: Set[str],
        current_rating: Optional[int] = None,
        n: int = DEFAULT_RECOMMENDATION_COUNT,
    ) -> List[CodeforcesProblem]:
        """Return up to *n* Codeforces problems the user should try next.

        Strategy
        --------
        1. Exclude already-solved problems.
        2. Build a TF-IDF matrix over problem tags.
        3. Compute average tag vector for solved problems.
        4. Rank unsolved problems by cosine similarity to that centroid.
        5. If a rating is available, boost problems within ±RATING_BAND of the
           user's current rating (penalise the rest).
        6. Fall back to a simple difficulty-band filter when not enough data.
        """
        n = min(n, MAX_RECOMMENDATION_COUNT)
        unsolved = [p for p in all_problems if p.problem_id not in accepted_ids]
        if not unsolved:
            return []

        if len(accepted_ids) < MIN_SOLVED_FOR_ML:
            return self._fallback_cf(unsolved, current_rating, n)

        solved_problems = [p for p in all_problems if p.problem_id in accepted_ids]
        return self._ml_recommend_cf(
            solved_problems, unsolved, current_rating, n
        )

    def _fallback_cf(
        self,
        unsolved: List[CodeforcesProblem],
        current_rating: Optional[int],
        n: int,
    ) -> List[CodeforcesProblem]:
        if current_rating is None:
            return unsolved[:n]
        lo, hi = current_rating - RATING_BAND, current_rating + RATING_BAND
        in_band = [
            p
            for p in unsolved
            if p.rating is not None and lo <= p.rating <= hi
        ]
        if not in_band:
            in_band = unsolved
        return sorted(in_band, key=lambda p: p.solved_count, reverse=True)[:n]

    def _ml_recommend_cf(
        self,
        solved: List[CodeforcesProblem],
        unsolved: List[CodeforcesProblem],
        current_rating: Optional[int],
        n: int,
    ) -> List[CodeforcesProblem]:
        # Build tag corpus
        def tags_str(p: CodeforcesProblem) -> str:
            return " ".join(p.tags) if p.tags else "none"

        corpus = [tags_str(p) for p in solved] + [tags_str(p) for p in unsolved]
        vectorizer = TfidfVectorizer()
        tfidf = vectorizer.fit_transform(corpus)

        solved_vecs = tfidf[: len(solved)]
        unsolved_vecs = tfidf[len(solved) :]

        centroid = np.asarray(solved_vecs.mean(axis=0))
        sims = cosine_similarity(centroid, unsolved_vecs).flatten()

        # Optional: apply rating proximity bonus
        if current_rating is not None:
            for i, p in enumerate(unsolved):
                if p.rating is not None:
                    distance = abs(p.rating - current_rating)
                    bonus = max(0.0, 1.0 - distance / (2 * RATING_BAND))
                    sims[i] = 0.6 * sims[i] + 0.4 * bonus

        indices = np.argsort(sims)[::-1][:n]
        return [unsolved[i] for i in indices]

    # ------------------------------------------------------------------
    # LeetCode recommendations
    # ------------------------------------------------------------------

    def recommend_leetcode(
        self,
        all_problems: List[LeetCodeProblem],
        solved_slugs: Set[str],
        current_difficulty: Optional[int] = None,
        n: int = DEFAULT_RECOMMENDATION_COUNT,
    ) -> List[LeetCodeProblem]:
        """Return up to *n* LeetCode problems the user should try next.

        *current_difficulty* is 1 (Easy), 2 (Medium), or 3 (Hard).
        """
        n = min(n, MAX_RECOMMENDATION_COUNT)
        unsolved = [
            p
            for p in all_problems
            if p.title_slug not in solved_slugs and not p.is_paid_only
        ]
        if not unsolved:
            return []

        if len(solved_slugs) < MIN_SOLVED_FOR_ML:
            return self._fallback_lc(unsolved, current_difficulty, n)

        solved_problems = [
            p for p in all_problems if p.title_slug in solved_slugs
        ]
        return self._ml_recommend_lc(
            solved_problems, unsolved, current_difficulty, n
        )

    def _fallback_lc(
        self,
        unsolved: List[LeetCodeProblem],
        current_difficulty: Optional[int],
        n: int,
    ) -> List[LeetCodeProblem]:
        if current_difficulty is None:
            return sorted(unsolved, key=lambda p: p.ac_rate, reverse=True)[:n]
        # Suggest same or next difficulty level
        targets = {current_difficulty, min(current_difficulty + 1, 3)}
        filtered = [p for p in unsolved if p.difficulty_level in targets]
        if not filtered:
            filtered = unsolved
        return sorted(filtered, key=lambda p: p.ac_rate, reverse=True)[:n]

    def _ml_recommend_lc(
        self,
        solved: List[LeetCodeProblem],
        unsolved: List[LeetCodeProblem],
        current_difficulty: Optional[int],
        n: int,
    ) -> List[LeetCodeProblem]:
        def tags_str(p: LeetCodeProblem) -> str:
            return " ".join(p.tags) if p.tags else "none"

        corpus = [tags_str(p) for p in solved] + [tags_str(p) for p in unsolved]
        vectorizer = TfidfVectorizer()
        tfidf = vectorizer.fit_transform(corpus)

        solved_vecs = tfidf[: len(solved)]
        unsolved_vecs = tfidf[len(solved) :]

        centroid = np.asarray(solved_vecs.mean(axis=0))
        sims = cosine_similarity(centroid, unsolved_vecs).flatten()

        # Difficulty proximity bonus
        if current_difficulty is not None:
            for i, p in enumerate(unsolved):
                diff_dist = abs(p.difficulty_level - current_difficulty)
                bonus = 1.0 if diff_dist == 0 else (0.5 if diff_dist == 1 else 0.0)
                sims[i] = 0.7 * sims[i] + 0.3 * bonus

        indices = np.argsort(sims)[::-1][:n]
        return [unsolved[i] for i in indices]
