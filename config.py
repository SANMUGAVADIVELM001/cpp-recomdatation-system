"""Central configuration for the recommendation system."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Database path (can be overridden by environment variable)
DATABASE_PATH = os.environ.get(
    "DATABASE_PATH", str(BASE_DIR / "cprec.db")
)

# API base URLs
CODEFORCES_API_BASE = "https://codeforces.com/api"
LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

# HTTP request timeout (seconds)
REQUEST_TIMEOUT = 15

# Recommendation settings
DEFAULT_RECOMMENDATION_COUNT = 10
MAX_RECOMMENDATION_COUNT = 50

# Rating band used when estimating difficulty similarity
RATING_BAND = 300

# Minimum solved problems required before ML recommendations are used
MIN_SOLVED_FOR_ML = 5
