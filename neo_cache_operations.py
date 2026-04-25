"""
neo_cache_operations.py

Helper functions for reading and writing to the neo_cache collection.

Before we call NASA's API, we check if we already have a cached
version of that asteroid. If the cache has it and it's less
lthan 24 hours old, we return the cached version. If not, we go
fetch it from NASA and save it to MongoDB so next time is faster.

This saves us from burning through NASA's API rate limit (1000 req/hour
for a free API key). Popular asteroids like Apophis might get looked up
dozens of times a day by different users, so caching makes a big difference.

Author: Group 5 - John Pennig, Mary Lebens, Srivarsha Singireddy
Course: CSCI 514
"""

import datetime, os, requests
from mongo_setup import get_db

# NASA NeoWs API base URL - we look up individual asteroids by their ID
NASA_NEO_URL = "https://api.nasa.gov/neo/rest/v1/neo/"

# We will put our NASA API key here after we sign up for it
# Using DEMO_KEY is fine for testing but it has lower rate limits
NASA_API_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")


def get_asteroid(neo_id: str) -> dict | None:
    """
    Main entry point for getting asteroid data.
    Checks the cache first, falls back to NASA API if needed.

    Args:
        neo_id: The NASA JPL small-body ID, e.g. "2000433" for Eros

    Returns:
        The asteroid document (dict) or None if not found
    """
    db = get_db()

    # Step 1: Check MongoDB cache
    cached = db.neo_cache.find_one({"_id": neo_id})
    if cached:
        # We got a cache hit. The TTL index will handle expiration automatically,
        # so if the document is in here it's still fresh (less than 24 hours old).
        print(f"Cache hit for NEO {neo_id}")
        return cached

    # Step 2: Cache miss - go get the asteroid data from NASA
    print(f"Cache miss for NEO {neo_id}, fetching from NASA API...")
    asteroid_data = fetch_from_nasa(neo_id)

    if asteroid_data:
        # Step 3: Save to MongoDB for next time
        store_in_cache(asteroid_data, neo_id)

    return asteroid_data


def fetch_from_nasa(neo_id: str) -> dict | None:
    """
    Call NASA's NeoWs API to get data for a single asteroid.
    Returns the response as a dict, or None if the request failed.

    Args:
        neo_id: The NASA JPL small-body ID

    Returns:
        Asteroid data dict from NASA, or None on error
    """
    url = f"{NASA_NEO_URL}{neo_id}"
    params = {"api_key": NASA_API_KEY}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # raises an exception for 4xx/5xx errors
        return response.json()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            # Asteroid ID doesn't exist in NASA's system
            print(f"NEO {neo_id} not found in NASA database")
        else:
            print(f"NASA API error for NEO {neo_id}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        # Network issue, timeout, etc.
        print(f"Request failed for NEO {neo_id}: {e}")
        return None


def store_in_cache(asteroid_data: dict, neo_id: str) -> None:
    """
    Save a NASA API response to the neo_cache collection.
    We use upsert so that if the document already exists (race condition,
    or manual refresh) we update it rather than getting a duplicate key error.

    Args:
        asteroid_data: The full JSON response from NASA's API
        neo_id: The NASA JPL small-body ID (used as MongoDB _id)
    """
    db = get_db()

    # Add our own fields on top of whatever NASA returned
    asteroid_data["_id"] = neo_id
    asteroid_data["id"] = neo_id
    asteroid_data["hazardous"] = asteroid_data.get("is_potentially_hazardous_asteroid", False)
    asteroid_data["cached_at"] = datetime.datetime.now(datetime.timezone.utc)

    # upsert=True means: insert if it doesn't exist, update if it does
    db.neo_cache.replace_one(
        {"_id": neo_id},
        asteroid_data,
        upsert=True
    )
    print(f"Cached NEO {neo_id} in MongoDB")


def get_hazardous_asteroids(limit: int = 20) -> list:
    """
    Get potentially hazardous asteroids from the cache for the dashboard.
    Only returns asteroids we've already cached. This is intentional
    since we don't want to make a huge number of API calls just for the
    dashboard. The dashboard will use the browse endpoint separately to
    populate the cache.

    Args:
        limit: Max number of results to return (default 20)

    Returns:
        List of asteroid documents where is_potentially_hazardous_asteroid is True
    """
    db = get_db()

    # The index on is_potentially_hazardous_asteroid makes this query fast
    results = db.neo_cache.find(
        {"is_potentially_hazardous_asteroid": True},
        # Only return the fields we actually need for the dashboard card
        # This reduces the data transferred over the network
        {
            "_id": 0,
            "id": 1,
            "name": 1,
            "estimated_diameter": 1,
            "close_approach_data": 1,
            "hazardous": 1
        }
    ).limit(limit)

    return list(results)


def log_search(user_id: int, query: str, neo_id: str | None, result_count: int, search_type: str = "name") -> None:
    """
    Log a user's search to the search_logs collection.
    This is fire-and-forget. If it fails we don't want to break the
    user's search experience, so we catch exceptions silently.

    Args:
        user_id: The user's ID from PostgreSQL
        query: What they typed in the search box
        neo_id: The asteroid ID if we found one, otherwise None
        result_count: How many results came back
        search_type: "name" or "jpl_id"
    """
    db = get_db()

    log_entry = {
        "user_id": user_id,
        "query": query,
        "neo_id": neo_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc),
        "result_count": result_count,
        "search_type": search_type
    }

    try:
        db.search_logs.insert_one(log_entry)
    except Exception as e:
        # Don't crash the app just because logging failed
        print(f"Warning: failed to log search: {e}")


def get_user_search_history(user_id: int, limit: int = 10) -> list:
    """
    Get a user's recent searches, most recent first.
    Uses the compound index on (user_id, timestamp) so this is fast.

    Args:
        user_id: The user's ID from PostgreSQL
        limit: Max number of results (default 10)

    Returns:
        List of search log documents
    """
    db = get_db()

    results = db.search_logs.find(
        {"user_id": user_id},
        {"_id": 0, "query": 1, "neo_id": 1, "timestamp": 1, "result_count": 1}
    ).sort("timestamp", -1).limit(limit)

    return list(results)

def get_asteroid_by_id(neo_id: str) -> dict | None:
    """Alias used by app.py for the asteroid detail page."""
    return get_asteroid(neo_id)


def search_asteroids(query: str, search_type: str = "name", limit: int = 25) -> list:
    """
    Search cached asteroids by name or exact NASA/JPL ID.
    If searching by ID and it is not cached, try NASA and cache it.
    """
    db = get_db()
    query = (query or "").strip()

    if not query:
        return []

    if search_type in ("id", "jpl_id", "neo_id"):
        asteroid = get_asteroid(query)
        return [asteroid] if asteroid else []

    results = db.neo_cache.find(
        {"name": {"$regex": query, "$options": "i"}}
    ).limit(limit)

    return list(results)


def get_dashboard_asteroids(limit: int = 20) -> list:
    """Return cached asteroids for a simple dashboard/list view."""
    db = get_db()
    results = db.neo_cache.find(
        {},
        {
            "_id": 0,
            "id": 1,
            "name": 1,
            "estimated_diameter": 1,
            "close_approach_data": 1,
            "hazardous": 1
        }
    ).sort("cached_at", -1).limit(limit)

    return list(results)
