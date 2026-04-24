from flask import Flask, render_template, request, redirect, url_for, session
app = Flask(__name__)

SAMPLE_ASTEROIDS = [
    {
        "id": "2000433",
        "name": "433 Eros",
        "absolute_magnitude": 10.31,
        "hazardous": False,
        "diameter_min": 22.0,
        "diameter_max": 49.0,
        "miss_distance": "26,729,000 km",
        "velocity": "20,000 km/h"
    },
    {
        "id": "99942",
        "name": "99942 Apophis",
        "absolute_magnitude": 19.7,
        "hazardous": True,
        "diameter_min": 0.31,
        "diameter_max": 0.68,
        "miss_distance": "31,000 km",
        "velocity": "30,728 km/h"
    },
    {
        "id": "25143",
        "name": "25143 Itokawa",
        "absolute_magnitude": 19.2,
        "hazardous": False,
        "diameter_min": 0.21,
        "diameter_max": 0.47,
        "miss_distance": "5,800,000 km",
        "velocity": "25,000 km/h"
    }
]

def get_asteroid_by_id(asteroid_id):
    for asteroid in SAMPLE_ASTEROIDS:
        if asteroid["id"] == asteroid_id:
            return asteroid
    return None
    
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    results = []

    if query:
        for asteroid in SAMPLE_ASTEROIDS:
            if query.lower() in asteroid["name"].lower() or query in asteroid["id"]:
                results.append(asteroid)
    else:
        results = SAMPLE_ASTEROIDS

    return render_template("search.html", query=query, results=results)

@app.route("/asteroid/<asteroid_id>")
def asteroid_detail(asteroid_id):
    asteroid = get_asteroid_by_id(asteroid_id)
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
        session["user_name"] = request.form.get("first_name", "Demo User")
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
        asteroid = get_asteroid_by_id(asteroid_id)
        if asteroid:
            saved_asteroids.append(asteroid)

    return render_template("watchlist.html", saved_asteroids=saved_asteroids)

@app.route("/settings")
def settings():
    if not session.get("logged_in"):
        return redirect(url_for("login_register"))
    
    return render_template("settings.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")