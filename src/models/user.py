"""Data models for users."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CodeforcesUser:
    """Represents a Codeforces user profile."""

    handle: str
    rating: Optional[int] = None
    max_rating: Optional[int] = None
    rank: Optional[str] = None
    max_rank: Optional[str] = None
    contribution: int = 0
    friend_of_count: int = 0
    registered_at: Optional[int] = None  # Unix timestamp

    @classmethod
    def from_api(cls, data: dict) -> "CodeforcesUser":
        return cls(
            handle=data["handle"],
            rating=data.get("rating"),
            max_rating=data.get("maxRating"),
            rank=data.get("rank"),
            max_rank=data.get("maxRank"),
            contribution=data.get("contribution", 0),
            friend_of_count=data.get("friendOfCount", 0),
            registered_at=data.get("registrationTimeSeconds"),
        )


@dataclass
class LeetCodeUser:
    """Represents a LeetCode user profile."""

    username: str
    easy_solved: int = 0
    medium_solved: int = 0
    hard_solved: int = 0
    total_solved: int = 0
    acceptance_rate: float = 0.0
    ranking: Optional[int] = None
    contribution_points: int = 0
    reputation: int = 0

    @classmethod
    def from_api(cls, username: str, stats: dict, profile: dict) -> "LeetCodeUser":
        solved = stats.get("acSubmissionNum", [])
        easy = next((s["count"] for s in solved if s["difficulty"] == "Easy"), 0)
        medium = next((s["count"] for s in solved if s["difficulty"] == "Medium"), 0)
        hard = next((s["count"] for s in solved if s["difficulty"] == "Hard"), 0)
        total = next((s["count"] for s in solved if s["difficulty"] == "All"), 0)
        total_sub = stats.get("totalSubmissionNum", [])
        total_sub_count = next(
            (s["count"] for s in total_sub if s["difficulty"] == "All"), 1
        )
        acceptance = round(total / max(total_sub_count, 1) * 100, 2) if total else 0.0
        return cls(
            username=username,
            easy_solved=easy,
            medium_solved=medium,
            hard_solved=hard,
            total_solved=total,
            acceptance_rate=acceptance,
            ranking=profile.get("ranking"),
            contribution_points=profile.get("contributionPoints", 0),
            reputation=profile.get("reputation", 0),
        )
