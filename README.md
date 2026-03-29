# cpp-recomdatation-system

AI-powered competitive programming recommendation and analytics system that integrates **Codeforces** and **LeetCode** to provide personalized problem suggestions, performance insights, and learning progress tracking.

---

## Features

| Feature | Description |
|---|---|
| **Personalized recommendations** | Content-based ML engine (TF-IDF + cosine similarity) suggests problems matching your solved history and difficulty level |
| **Codeforces integration** | Fetch user profiles, submission history, rating history, and the full problem set via the public REST API |
| **LeetCode integration** | Fetch user profiles, solved problems, and the problem catalogue via the GraphQL API |
| **Performance analytics** | Rating trend analysis, tag/difficulty distribution, submission activity heat-map, verdict breakdown |
| **Progress tracking** | Daily solving streaks, topic mastery, weekly summaries, and goal management with progress evaluation |
| **Local caching** | SQLite database caches API data to minimise repeated requests |
| **CLI interface** | `cprec` command with sub-commands for profiles, recommendations, analytics, and goals |

---

## Project Structure

```
cpp-recomdatation-system/
├── main.py                     # CLI entry point
├── config.py                   # Central configuration
├── requirements.txt
├── setup.py
├── src/
│   ├── api/
│   │   ├── codeforces.py       # Codeforces REST API client
│   │   └── leetcode.py         # LeetCode GraphQL API client
│   ├── models/
│   │   ├── user.py             # CodeforcesUser / LeetCodeUser dataclasses
│   │   └── problem.py          # CodeforcesProblem / LeetCodeProblem / Submission
│   ├── recommender/
│   │   └── engine.py           # AI recommendation engine
│   ├── analytics/
│   │   └── performance.py      # Performance analytics
│   ├── tracker/
│   │   └── progress.py         # Streak, goals, weekly summary
│   └── storage/
│       └── database.py         # SQLite-backed local storage
└── tests/
    ├── test_codeforces.py
    ├── test_leetcode.py
    ├── test_recommender.py
    ├── test_analytics.py
    └── test_tracker.py
```

---

## Recommendation Algorithm

The engine uses **content-based filtering**:

1. Represent each problem as a TF-IDF vector of its topic tags.
2. Compute the centroid of the user's solved-problem vectors.
3. Rank unsolved problems by cosine similarity to the centroid.
4. Apply an optional **difficulty proximity bonus** (Codeforces rating band / LeetCode difficulty level).
5. Fall back to a simple difficulty-band filter when fewer than 5 problems have been solved.

---

## Installation

```bash
pip install -r requirements.txt
# Optional: install as a CLI tool
pip install -e .
```

## Configuration

Copy `.env.example` to `.env` (or set environment variables directly):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_PATH` | `cprec.db` | Path to the SQLite database |

---

## Usage

### Codeforces

```bash
# Show profile
python main.py cf profile tourist

# Get 10 personalised problem recommendations
python main.py cf recommend tourist --count 10

# Show performance analytics
python main.py cf analytics tourist

# Show solving streak (from cached data)
python main.py cf streak tourist
```

### LeetCode

```bash
# Show profile
python main.py lc profile alice

# Get recommendations at Medium difficulty
python main.py lc recommend alice --difficulty Medium --count 10

# Show performance analytics
python main.py lc analytics alice
```

### Goals

```bash
# Add a goal: solve 100 LeetCode problems
python main.py goal add -p leetcode -u alice --type problems_solved -t 100

# List goals
python main.py goal list -p leetcode -u alice

# Mark a goal complete
python main.py goal complete 1
```

---

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

All 42 tests cover the API clients (mocked), recommendation engine, analytics, and progress tracker.
