"""LeetCode GraphQL API client."""

from typing import Dict, List, Optional

import requests

from config import LEETCODE_GRAPHQL_URL, REQUEST_TIMEOUT
from src.models.problem import LeetCodeProblem, Submission
from src.models.user import LeetCodeUser


class LeetCodeAPIError(Exception):
    """Raised when the LeetCode API returns an error."""


class LeetCodeClient:
    """Thin wrapper around the LeetCode GraphQL API."""

    def __init__(self, graphql_url: str = LEETCODE_GRAPHQL_URL) -> None:
        self._url = graphql_url
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Content-Type": "application/json",
                "Referer": "https://leetcode.com",
            }
        )

    def _query(self, payload: dict) -> dict:
        try:
            resp = self._session.post(
                self._url, json=payload, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise LeetCodeAPIError(f"HTTP error: {exc}") from exc
        data = resp.json()
        if "errors" in data:
            raise LeetCodeAPIError(str(data["errors"]))
        return data.get("data", {})

    # ------------------------------------------------------------------
    # User profile
    # ------------------------------------------------------------------

    def get_user(self, username: str) -> LeetCodeUser:
        """Fetch profile and submission statistics for *username*."""
        payload = {
            "query": """
            query getUserProfile($username: String!) {
                matchedUser(username: $username) {
                    username
                    profile {
                        ranking
                        reputation
                        contributionPoints: starRating
                    }
                    submitStats: submitStatsGlobal {
                        acSubmissionNum {
                            difficulty
                            count
                        }
                        totalSubmissionNum {
                            difficulty
                            count
                        }
                    }
                }
            }
            """,
            "variables": {"username": username},
        }
        data = self._query(payload)
        user_data = data.get("matchedUser")
        if not user_data:
            raise LeetCodeAPIError(f"User '{username}' not found")
        stats = user_data.get("submitStats", {})
        profile = user_data.get("profile", {})
        return LeetCodeUser.from_api(username, stats, profile)

    # ------------------------------------------------------------------
    # Solved problems
    # ------------------------------------------------------------------

    def get_solved_problems(self, username: str) -> List[str]:
        """Return title slugs of all accepted problems for *username*."""
        payload = {
            "query": """
            query recentAcSubmissions($username: String!, $limit: Int!) {
                recentAcSubmissionList(username: $username, limit: $limit) {
                    titleSlug
                }
            }
            """,
            "variables": {"username": username, "limit": 1000},
        }
        data = self._query(payload)
        submissions = data.get("recentAcSubmissionList") or []
        return list({s["titleSlug"] for s in submissions})

    # ------------------------------------------------------------------
    # Problem list
    # ------------------------------------------------------------------

    def get_problem_list(
        self,
        difficulty: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 500,
        skip: int = 0,
    ) -> List[LeetCodeProblem]:
        """Return problems filtered by optional *difficulty* and *tags*."""
        filters: dict = {}
        if difficulty:
            filters["difficulty"] = difficulty.upper()
        if tags:
            filters["tags"] = tags

        payload = {
            "query": """
            query problemsetQuestionList(
                $categorySlug: String,
                $limit: Int,
                $skip: Int,
                $filters: QuestionListFilterInput
            ) {
                problemsetQuestionList: questionList(
                    categorySlug: $categorySlug
                    limit: $limit
                    skip: $skip
                    filters: $filters
                ) {
                    total: totalNum
                    questions: data {
                        title
                        titleSlug
                        difficulty
                        acRate
                        paidOnly: isPaidOnly
                        topicTags {
                            name
                        }
                    }
                }
            }
            """,
            "variables": {
                "categorySlug": "",
                "limit": limit,
                "skip": skip,
                "filters": filters,
            },
        }
        data = self._query(payload)
        questions = (
            data.get("problemsetQuestionList", {}).get("questions") or []
        )
        return [LeetCodeProblem.from_api(q) for q in questions]

    # ------------------------------------------------------------------
    # Topic tags
    # ------------------------------------------------------------------

    def get_topic_tags(self) -> List[Dict]:
        """Return available topic tags."""
        payload = {
            "query": """
            query {
                topics {
                    slug
                    name
                }
            }
            """
        }
        try:
            data = self._query(payload)
            return data.get("topics") or []
        except LeetCodeAPIError:
            return []
