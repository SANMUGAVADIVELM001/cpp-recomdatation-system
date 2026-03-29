"""Codeforces public API client."""

import time
from typing import Dict, List, Optional, Tuple

import requests

from config import CODEFORCES_API_BASE, REQUEST_TIMEOUT
from src.models.problem import CodeforcesProblem, Submission
from src.models.user import CodeforcesUser


class CodeforcesAPIError(Exception):
    """Raised when the Codeforces API returns an error response."""


class CodeforcesClient:
    """Thin wrapper around the Codeforces REST API."""

    def __init__(self, base_url: str = CODEFORCES_API_BASE) -> None:
        self._base = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        url = f"{self._base}/{endpoint}"
        try:
            resp = self._session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise CodeforcesAPIError(f"HTTP error: {exc}") from exc
        data = resp.json()
        if data.get("status") != "OK":
            raise CodeforcesAPIError(data.get("comment", "Unknown API error"))
        return data.get("result", {})

    # ------------------------------------------------------------------
    # User profile
    # ------------------------------------------------------------------

    def get_user(self, handle: str) -> CodeforcesUser:
        """Fetch profile for a single handle."""
        result = self._get("user.info", {"handles": handle})
        if not result:
            raise CodeforcesAPIError(f"No data for handle '{handle}'")
        return CodeforcesUser.from_api(result[0])

    # ------------------------------------------------------------------
    # Submissions
    # ------------------------------------------------------------------

    def get_user_submissions(
        self, handle: str, count: int = 500
    ) -> List[Submission]:
        """Return the most recent *count* submissions for *handle*."""
        result = self._get(
            "user.status", {"handle": handle, "from": 1, "count": count}
        )
        submissions: List[Submission] = []
        for item in result:
            prob = item.get("problem", {})
            contest_id = prob.get("contestId")
            index = prob.get("index", "")
            problem_id = f"{contest_id}{index}" if contest_id else index
            submissions.append(
                Submission(
                    platform="codeforces",
                    problem_id=problem_id,
                    verdict=item.get("verdict", ""),
                    timestamp=item.get("creationTimeSeconds", 0),
                    language=item.get("programmingLanguage", ""),
                )
            )
        return submissions

    def get_accepted_problem_ids(self, handle: str) -> List[str]:
        """Return IDs of all accepted problems for *handle*."""
        submissions = self.get_user_submissions(handle, count=10000)
        return list(
            {s.problem_id for s in submissions if s.accepted}
        )

    # ------------------------------------------------------------------
    # Rating history
    # ------------------------------------------------------------------

    def get_rating_history(self, handle: str) -> List[Dict]:
        """Return rating history entries for *handle*."""
        result = self._get("user.rating", {"handle": handle})
        return [
            {
                "contest_id": entry["contestId"],
                "contest_name": entry["contestName"],
                "rank": entry["rank"],
                "old_rating": entry["oldRating"],
                "new_rating": entry["newRating"],
                "timestamp": entry["ratingUpdateTimeSeconds"],
            }
            for entry in result
        ]

    # ------------------------------------------------------------------
    # Problem set
    # ------------------------------------------------------------------

    def get_problem_set(
        self, tags: Optional[List[str]] = None
    ) -> Tuple[List[CodeforcesProblem], List[Dict]]:
        """Return the full problem set and per-problem statistics."""
        params: dict = {}
        if tags:
            params["tags"] = ";".join(tags)
        result = self._get("problemset.problems", params)
        problems = [
            CodeforcesProblem.from_api(p) for p in result.get("problems", [])
        ]
        stats = result.get("problemStatistics", [])
        # Attach solved counts
        stat_map = {
            f"{s.get('contestId')}{s.get('index')}": s.get("solvedCount", 0)
            for s in stats
        }
        for prob in problems:
            prob.solved_count = stat_map.get(prob.problem_id, 0)
        return problems, stats
