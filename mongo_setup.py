"""
mongo_setup.py

This file sets up the MongoDB collections and indexes for the NEO Tracker app.
We're using MongoDB here instead of PostgreSQL because the data coming back
from NASA's API is deeply nested JSON. The data has diameters in multiple units,
orbital data, and a list of close approach records all inside one object.
Trying to split that into relational tables would be a nightmare and we'd
lose a lot of flexibility if NASA ever changes their response format.

MongoDB is good for this because it stores documents as BSON (basically JSON), 
so we can dump the API response straight in without transforming it. The schema is 
flexible, sand it handles the nested/hierarchical structure of the data naturally.

We're using three collections:
  1. neo_cache      - caches full API responses so we don't spam NASA's API
  2. search_logs    - logs every search a user makes (for analytics/history)
  3. sessions       - stores user session tokens

Author: Group 5 - John Pennig, Mary Lebens, Srivarsha Singireddy
Course: CSCI 514
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
import pymongo
from pymongo.errors import CollectionInvalid
import datetime, os

# Connect to MongoDB - in production this would use an env variable
# for the connection string instead of hardcoding it

MONGO_URI = os.environ.get("MONGO_URI")
DB_NAME = os.environ.get("MONGO_DB_NAME", "neo_tracker")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

asteroids_cluster = db["asteroids"]
watchlist_cluster = db["watchlist"]

def get_db():
    """Return a reference to the neo_tracker database."""
    return client[DB_NAME]


def create_collections(db):
    """
    Create the collections with schema validation.
    MongoDB doesn't enforce schemas by default, but we can add
    JSON Schema validation to help with data consistency.
    """

    # --- neo_cache collection ---
    # Stores the full JSON response from NASA's NeoWs API.
    # We use the NASA neo_reference_id as the _id so we can do fast
    # lookups by asteroid ID without needing an extra index.
    try:
        db.create_collection(
            "neo_cache",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["_id", "name", "cached_at"],
                    "properties": {
                        "_id": {
                            # NASA JPL small-body ID, e.g. "2000433"
                            "bsonType": "string",
                            "description": "NASA neo_reference_id - required"
                        },
                        "name": {
                            "bsonType": "string",
                            "description": "Asteroid name - required"
                        },
                        "is_potentially_hazardous_asteroid": {
                            "bsonType": "bool"
                        },
                        "cached_at": {
                            # Timestamp so we know when to refresh the cache
                            "bsonType": "date",
                            "description": "When we last pulled this from NASA - required"
                        }
                    }
                }
            }
        )
        print("Created collection: neo_cache")
    except CollectionInvalid:
        # Collection already exists, that's fine
        print("Collection neo_cache already exists, skipping")

    # --- search_logs collection ---
    # Every time a user searches for an asteroid we log it here.
    # This is a good fit for NoSQL because search logs are write-heavy,
    # append-only, and we don't need joins to query them.
    try:
        db.create_collection(
            "search_logs",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["user_id", "query", "timestamp"],
                    "properties": {
                        "user_id": {
                            "bsonType": "int",
                            "description": "References users.user_id in PostgreSQL"
                        },
                        "query": {
                            "bsonType": "string",
                            "description": "What the user typed in the search box"
                        },
                        "neo_id": {
                            # nullable - search might return no results
                            "bsonType": ["string", "null"]
                        },
                        "timestamp": {
                            "bsonType": "date"
                        },
                        "result_count": {
                            "bsonType": "int"
                        }
                    }
                }
            }
        )
        print("Created collection: search_logs")
    except CollectionInvalid:
        print("Collection search_logs already exists, skipping")

    # --- sessions collection ---
    # Stores active user sessions. Session data can be messy and
    # change shape depending on what we store later (preferences,
    # last-viewed asteroids, etc.), so flexible schema makes sense here.
    try:
        db.create_collection(
            "sessions",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["session_token", "user_id", "created_at", "expires_at"],
                    "properties": {
                        "session_token": {
                            "bsonType": "string"
                        },
                        "user_id": {
                            "bsonType": "int"
                        },
                        "created_at": {
                            "bsonType": "date"
                        },
                        "expires_at": {
                            "bsonType": "date"
                        }
                    }
                }
            }
        )
        print("Created collection: sessions")
    except CollectionInvalid:
        print("Collection sessions already exists, skipping")


def create_indexes(db):
    """
    Set up indexes on all three collections.

    Index decisions:
      - neo_cache: TTL index on cached_at automatically deletes entries
        after 24 hours so we always have fresh data from NASA. Also index
        on is_potentially_hazardous so the dashboard filter is fast.

      - search_logs: compound index on (user_id, timestamp DESC) because
        the most common query is "show me this user's recent searches".
        We don't need a single-field index on user_id alone since the
        compound covers that.

      - sessions: unique index on session_token for fast auth lookups,
        TTL on expires_at so expired sessions get auto-cleaned up.
    """

    # neo_cache indexes
    # TTL: auto-delete cached asteroid data after 24 hours (86400 seconds)
    db.neo_cache.create_index(
        "cached_at",
        expireAfterSeconds=86400,
        name="idx_neo_cache_ttl"
    )
    # For filtering hazardous asteroids on the dashboard
    db.neo_cache.create_index(
        [("is_potentially_hazardous_asteroid", ASCENDING)],
        name="idx_neo_hazardous"
    )
    print("Created indexes on neo_cache")

    # search_logs indexes
    # Most queries will be "get recent searches for user X"
    db.search_logs.create_index(
        [("user_id", ASCENDING), ("timestamp", DESCENDING)],
        name="idx_search_user_time"
    )
    print("Created indexes on search_logs")

    # sessions indexes
    # Session token lookups need to be fast - every authenticated request hits this
    db.sessions.create_index(
        "session_token",
        unique=True,
        name="idx_session_token"
    )
    # Auto-delete expired sessions so the collection doesn't grow forever
    db.sessions.create_index(
        "expires_at",
        expireAfterSeconds=0,
        name="idx_session_ttl"
    )
    print("Created indexes on sessions")


def setup():
    """Run the full setup: connect, create collections, create indexes."""
    print(f"Connecting to MongoDB at {MONGO_URI}...")
    db = get_db()
    print(f"Connected. Setting up database: {DB_NAME}\n")

    create_collections(db)
    print()
    create_indexes(db)

    print("\nMongoDB setup complete.")
    return db


if __name__ == "__main__":
    setup()
