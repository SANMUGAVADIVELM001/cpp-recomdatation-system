"""Tests for Codeforces API client (using mocked HTTP)."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.api.codeforces import CodeforcesAPIError, CodeforcesClient
from src.models.user import CodeforcesUser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def _error_response(json_data: dict) -> MagicMock:
    resp = _make_response(json_data)
    return resp


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------

class TestGetUser:
    def setup_method(self):
        self.client = CodeforcesClient()

    def test_returns_user_on_success(self):
        payload = {
            "status": "OK",
            "result": [
                {
                    "handle": "tourist",
                    "rating": 3979,
                    "maxRating": 3979,
                    "rank": "legendary grandmaster",
                    "maxRank": "legendary grandmaster",
                    "contribution": 65,
                    "friendOfCount": 1000,
                    "registrationTimeSeconds": 1285340960,
                }
            ],
        }
        with patch.object(self.client._session, "get", return_value=_make_response(payload)):
            user = self.client.get_user("tourist")

        assert isinstance(user, CodeforcesUser)
        assert user.handle == "tourist"
        assert user.rating == 3979

    def test_raises_on_api_error(self):
        payload = {"status": "FAILED", "comment": "handles: User with handle tourist not found"}
        with patch.object(self.client._session, "get", return_value=_make_response(payload)):
            with pytest.raises(CodeforcesAPIError):
                self.client.get_user("tourist")

    def test_raises_on_http_error(self):
        with patch.object(
            self.client._session, "get",
            side_effect=requests.ConnectionError("timeout")
        ):
            with pytest.raises(CodeforcesAPIError):
                self.client.get_user("tourist")


# ---------------------------------------------------------------------------
# get_user_submissions
# ---------------------------------------------------------------------------

class TestGetUserSubmissions:
    def setup_method(self):
        self.client = CodeforcesClient()

    def test_parses_submissions(self):
        payload = {
            "status": "OK",
            "result": [
                {
                    "id": 1,
                    "problem": {"contestId": 1, "index": "A", "name": "Test"},
                    "verdict": "OK",
                    "creationTimeSeconds": 1000000,
                    "programmingLanguage": "C++17",
                }
            ],
        }
        with patch.object(self.client._session, "get", return_value=_make_response(payload)):
            subs = self.client.get_user_submissions("handle")

        assert len(subs) == 1
        assert subs[0].problem_id == "1A"
        assert subs[0].accepted is True

    def test_accepted_ids_deduplicates(self):
        payload = {
            "status": "OK",
            "result": [
                {
                    "problem": {"contestId": 1, "index": "A"},
                    "verdict": "OK",
                    "creationTimeSeconds": 1,
                    "programmingLanguage": "C++",
                },
                {
                    "problem": {"contestId": 1, "index": "A"},
                    "verdict": "OK",
                    "creationTimeSeconds": 2,
                    "programmingLanguage": "C++",
                },
                {
                    "problem": {"contestId": 2, "index": "B"},
                    "verdict": "WRONG_ANSWER",
                    "creationTimeSeconds": 3,
                    "programmingLanguage": "C++",
                },
            ],
        }
        with patch.object(self.client._session, "get", return_value=_make_response(payload)):
            ids = self.client.get_accepted_problem_ids("handle")

        assert len(ids) == 1
        assert "1A" in ids


# ---------------------------------------------------------------------------
# get_problem_set
# ---------------------------------------------------------------------------

class TestGetProblemSet:
    def setup_method(self):
        self.client = CodeforcesClient()

    def test_attaches_solved_counts(self):
        payload = {
            "status": "OK",
            "result": {
                "problems": [
                    {"contestId": 1, "index": "A", "name": "P1",
                     "rating": 800, "tags": ["math"]},
                ],
                "problemStatistics": [
                    {"contestId": 1, "index": "A", "solvedCount": 42},
                ],
            },
        }
        with patch.object(self.client._session, "get", return_value=_make_response(payload)):
            problems, stats = self.client.get_problem_set()

        assert len(problems) == 1
        assert problems[0].solved_count == 42
        assert problems[0].tags == ["math"]
