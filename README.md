# CSCI514-GroupProject for Group 5

Author: Group 5 - John Pennig, Mary Lebens, Srivarsha Singireddy
Course: CSCI 514

Description of mongo_setup.py

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

----------------------------------------------------------------------------------

Description of neo_cache_operations.py

Helper functions for reading and writing to the neo_cache collection.

Before we call NASA's API, we check if we already have a cached
version of that asteroid. If the cache has it and it's less
lthan 24 hours old, we return the cached version. If not, we go
fetch it from NASA and save it to MongoDB so next time is faster.

This saves us from burning through NASA's API rate limit (1000 req/hour
for a free API key). Popular asteroids like Apophis might get looked up
dozens of times a day by different users, so caching makes a big difference.

