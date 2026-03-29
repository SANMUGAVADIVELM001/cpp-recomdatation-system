"""Data models for problems."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CodeforcesProblem:
    """Represents a single Codeforces problem."""

    contest_id: Optional[int]
    index: str
    name: str
    rating: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    solved_count: int = 0

    @property
    def problem_id(self) -> str:
        if self.contest_id:
            return f"{self.contest_id}{self.index}"
        return self.index

    @property
    def url(self) -> str:
        if self.contest_id:
            return (
                f"https://codeforces.com/problemset/problem/"
                f"{self.contest_id}/{self.index}"
            )
        return ""

    @classmethod
    def from_api(cls, data: dict) -> "CodeforcesProblem":
        return cls(
            contest_id=data.get("contestId"),
            index=data["index"],
            name=data["name"],
            rating=data.get("rating"),
            tags=data.get("tags", []),
            solved_count=data.get("solvedCount", 0),
        )


@dataclass
class LeetCodeProblem:
    """Represents a single LeetCode problem."""

    title: str
    title_slug: str
    difficulty: str  # Easy / Medium / Hard
    tags: List[str] = field(default_factory=list)
    ac_rate: float = 0.0
    is_paid_only: bool = False

    # Numeric difficulty mapping used for comparison
    _DIFFICULTY_MAP = {"Easy": 1, "Medium": 2, "Hard": 3}

    @property
    def difficulty_level(self) -> int:
        return self._DIFFICULTY_MAP.get(self.difficulty, 0)

    @property
    def url(self) -> str:
        return f"https://leetcode.com/problems/{self.title_slug}/"

    @classmethod
    def from_api(cls, data: dict) -> "LeetCodeProblem":
        tags = [t["name"] for t in data.get("topicTags", [])]
        return cls(
            title=data["title"],
            title_slug=data["titleSlug"],
            difficulty=data["difficulty"],
            tags=tags,
            ac_rate=data.get("acRate", 0.0),
            is_paid_only=data.get("paidOnly", False),
        )


@dataclass
class Submission:
    """Represents a single submission (Codeforces or LeetCode)."""

    platform: str  # "codeforces" | "leetcode"
    problem_id: str
    verdict: str  # "OK" / "Accepted" / etc.
    timestamp: int  # Unix timestamp
    language: str = ""

    @property
    def accepted(self) -> bool:
        return self.verdict in ("OK", "Accepted")
