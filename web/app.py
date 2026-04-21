"""
AwaJobs - Dashboard web (Flask)
"""

import sqlite3
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "awajobs-dev-key-change-me")
DB_PATH = os.environ.get("DB_PATH", "/data/awajobs.db")

# --- Auth ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    id = "1"

@login_manager.user_loader
def load_user(user_id):
    return User() if user_id == "1" else None

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        pwd = request.form.get("password")
        if pwd == os.environ.get("DASHBOARD_PASSWORD", ""):
            login_user(User(), remember=True)
            return redirect(url_for("index"))
        error = "Mot de passe incorrect"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    conn = get_db()
    label_filter = request.args.get("label", "all")
    source_filter = request.args.get("source", "all")
    sort = request.args.get("sort", "score")

    query = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if label_filter != "all":
        query += " AND label = ?"
        params.append(label_filter)
    if source_filter != "all":
        query += " AND source = ?"
        params.append(source_filter)

    order = "score DESC" if sort == "score" else "created_at DESC"
    query += f" ORDER BY {order}"

    jobs = conn.execute(query, params).fetchall()

    sources = [r[0] for r in conn.execute("SELECT DISTINCT source FROM jobs").fetchall()]

    stats = {
        "total": conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
        "new": conn.execute("SELECT COUNT(*) FROM jobs WHERE label='new'").fetchone()[0],
        "yes": conn.execute("SELECT COUNT(*) FROM jobs WHERE label='yes'").fetchone()[0],
        "no": conn.execute("SELECT COUNT(*) FROM jobs WHERE label='no'").fetchone()[0],
    }

    conn.execute("UPDATE jobs SET seen=1 WHERE seen=0")
    conn.commit()
    conn.close()

    return render_template("index.html",
                           jobs=jobs, stats=stats, sources=sources,
                           label_filter=label_filter,
                           source_filter=source_filter,
                           sort=sort)


@app.route("/label/<job_id>/<label>", methods=["POST"])
def set_label(job_id, label):
    if label not in ("yes", "no", "maybe", "new"):
        return jsonify({"error": "invalid label"}), 400
    conn = get_db()
    conn.execute("UPDATE jobs SET label=? WHERE id=?", (label, job_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/job/<job_id>")
def job_detail(job_id):
    conn = get_db()
    job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    if not job:
        return "Offre introuvable", 404
    return render_template("job.html", job=job)


@app.route("/add", methods=["GET", "POST"])
def add_manual():
    """Ajout manuel d'une offre (depuis LinkedIn, X, etc.)"""
    if request.method == "POST":
        import hashlib
        from scraper.scraper import score_job
        url = request.form.get("url", "")
        title = request.form.get("title", "")
        description = request.form.get("description", "")
        location = request.form.get("location", "")
        source = request.form.get("source", "Manuel")

        job_id = hashlib.md5(url.encode()).hexdigest()
        score = score_job(title, description)

        conn = get_db()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO jobs
                   (id, title, source, url, description, location, score, label, created_at)
                   VALUES (?,?,?,?,?,?,?,'new',?)""",
                (job_id, title, source, url, description[:2000], location, score,
                 datetime.utcnow().isoformat())
            )
            conn.commit()
        finally:
            conn.close()
        return redirect(url_for("index"))

    return render_template("add.html")


@app.route("/run-scraper", methods=["POST"])
def run_scraper():
    """Lance le scraper manuellement depuis le dashboard"""
    try:
        import sys
        sys.path.insert(0, "/app")
        from scraper.scraper import run
        count = run()
        return jsonify({"ok": True, "new": count})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
