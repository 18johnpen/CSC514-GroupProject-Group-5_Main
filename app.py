from flask import Flask, render_template, request, redirect, url_for, session
from apscheduler.schedulers.background import BackgroundScheduler
from pymongo.errors import PyMongoError
import os

from mongo_setup import setup
from neo_cache_operations import (
    get_asteroid,
    search_cached_asteroids,
    sync_recent_neos,
    log_search)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

try:
    setup()
except Exception as error:
    print(f'MongoDB setup skipped or failed: {error}')

#Starts a scheduler to sync with NASA's API every 24hrs. 
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(sync_recent_neos, "interval", hours=24, id="sync_recent_neos")
    scheduler.start()

    try:
        sync_recent_neos()
    except Exception as error:
        print(f'Sync with NASA API failed: {error}')

start_scheduler()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()

    try:
        results = search_cached_asteroids(query)
    except PyMongoError as error:
        print(f"MongoDB search failed: {error}")
        results = []

    user_id = session.get("user_id", 0)
    if query:
        first_result_id = results[0]["id"] if results else None
        log_search(user_id, query, first_result_id, len(results))

    return render_template("search.html", query=query, results=results)


@app.route("/asteroid/<asteroid_id>")
def asteroid_detail(asteroid_id):
    asteroid = get_asteroid(asteroid_id)
    if asteroid is None:
        return "asteroid not found", 404
    
    return render_template("asteroid_detail.html", asteroid=asteroid)


@app.route("/save/<asteroid_id>")
def save_asteroid(asteroid_id):
    if not session.get("logged_in"):
        return redirect(url_for("login_register"))
    
    watchlist = session.get("watchlist", [])
    if asteroid_id not in watchlist:
        watchlist.append(asteroid_id)
        session["watchlist"] = watchlist

    return redirect(url_for("watchlist"))


@app.route("/remove/<asteroid_id>")
def remove_asteroid(asteroid_id):
    watchlist = session.get("watchlist", [])
    if asteroid_id in watchlist:
        watchlist.remove(asteroid_id)
        session["watchlist"] = watchlist
    
    return redirect(url_for("watchlist"))


@app.route("/login", methods=["GET", "POST"])
def login_register():
    if request.method == "POST":
        session["logged_in"] = True
        session["user_id"] = 1
        session["user_name"] = request.form.get("first_name", "Demo User")
        session["email"] = request.form.get("email", "demo@example.com")
        return redirect(url_for("watchlist"))

    return render_template("login_register.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/watchlist")
def watchlist():
    if not session.get("logged_in"):
        return redirect(url_for("login_register"))

    saved_ids = session.get("watchlist", [])
    saved_asteroids = []

    for asteroid_id in saved_ids:
        asteroid = get_asteroid(asteroid_id)
        if asteroid:
            saved_asteroids.append(asteroid)

    return render_template("watchlist.html", saved_asteroids=saved_asteroids)


@app.route("/settings")
def settings():
    if not session.get("logged_in"):
        return redirect(url_for("login_register"))
    
    return render_template("settings.html")


@app.route("/sync")
def sync():
    if not session.get("logged_in"):
        return redirect(url_for("login_register"))
    
    count = sync_recent_neos()
    return f"NASA sync complete. {count} asteroid records."


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")