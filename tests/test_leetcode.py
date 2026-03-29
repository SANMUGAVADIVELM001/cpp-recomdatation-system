"""Tests for LeetCode API client (using mocked HTTP)."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.api.leetcode import LeetCodeAPIError, LeetCodeClient
from src.models.user import LeetCodeUser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------

class TestGetUser:
    def setup_method(self):
        self.client = LeetCodeClient()

    def _user_payload(self):
        return {
            "data": {
                "matchedUser": {
                    "username": "alice",
                    "profile": {"ranking": 1234, "reputation": 50, "contributionPoints": 10},
                    "submitStats": {
                        "acSubmissionNum": [
                            {"difficulty": "All", "count": 150},
                            {"difficulty": "Easy", "count": 80},
                            {"difficulty": "Medium", "count": 60},
                            {"difficulty": "Hard", "count": 10},
                        ],
                        "totalSubmissionNum": [
                            {"difficulty": "All", "count": 200},
                        ],
                    },
                }
            }
        }

    def test_returns_user(self):
        with patch.object(self.client._session, "post",
                          return_value=_make_response(self._user_payload())):
            user = self.client.get_user("alice")

        assert isinstance(user, LeetCodeUser)
        assert user.username == "alice"
        assert user.easy_solved == 80
        assert user.medium_solved == 60
        assert user.hard_solved == 10
        assert user.total_solved == 150

    def test_raises_when_not_found(self):
        payload = {"data": {"matchedUser": None}}
        with patch.object(self.client._session, "post",
                          return_value=_make_response(payload)):
            with pytest.raises(LeetCodeAPIError):
                self.client.get_user("nobody")

    def test_raises_on_graphql_errors(self):
        payload = {"errors": [{"message": "Some error"}]}
        with patch.object(self.client._session, "post",
                          return_value=_make_response(payload)):
            with pytest.raises(LeetCodeAPIError):
                self.client.get_user("alice")

    def test_raises_on_http_error(self):
        with patch.object(
            self.client._session, "post",
            side_effect=requests.ConnectionError("timeout")
        ):
            with pytest.raises(LeetCodeAPIError):
                self.client.get_user("alice")


# ---------------------------------------------------------------------------
# get_solved_problems
# ---------------------------------------------------------------------------

class TestGetSolvedProblems:
    def setup_method(self):
        self.client = LeetCodeClient()

    def test_returns_unique_slugs(self):
        payload = {
            "data": {
                "recentAcSubmissionList": [
                    {"titleSlug": "two-sum"},
                    {"titleSlug": "two-sum"},
                    {"titleSlug": "reverse-linked-list"},
                ]
            }
        }
        with patch.object(self.client._session, "post",
                          return_value=_make_response(payload)):
            slugs = self.client.get_solved_problems("alice")

        assert set(slugs) == {"two-sum", "reverse-linked-list"}


# ---------------------------------------------------------------------------
# get_problem_list
# ---------------------------------------------------------------------------

class TestGetProblemList:
    def setup_method(self):
        self.client = LeetCodeClient()

    def test_parses_problems(self):
        payload = {
            "data": {
                "problemsetQuestionList": {
                    "total": 1,
                    "questions": [
                        {
                            "title": "Two Sum",
                            "titleSlug": "two-sum",
                            "difficulty": "Easy",
                            "acRate": 49.5,
                            "paidOnly": False,
                            "topicTags": [{"name": "Array"}, {"name": "Hash Table"}],
                        }
                    ],
                }
            }
        }
        with patch.object(self.client._session, "post",
                          return_value=_make_response(payload)):
            problems = self.client.get_problem_list()

        assert len(problems) == 1
        assert problems[0].title == "Two Sum"
        assert problems[0].difficulty == "Easy"
        assert "Array" in problems[0].tags
