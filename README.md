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

