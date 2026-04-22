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
        pwd = request.form.get("password", "")
        expected = os.environ.get("DASHBOARD_PASSWORD", "").strip().strip('"').strip("'")
        if pwd == expected:
            login_user(User(), remember=True)
            return redirect(url_for("index"))
        error = "Mot de passe incorrect"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    # Migration : ajouter category si elle n'existe pas (DB existante)
    try:
        conn.execute("ALTER TABLE jobs ADD COLUMN category TEXT DEFAULT 'job'")
        conn.commit()
    except Exception:
        pass
    return conn


@app.route("/")
@login_required
def index():
    conn = get_db()
    label_filter = request.args.get("label", "all")
    source_filter = request.args.get("source", "all")
    sort = request.args.get("sort", "score")

    query = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if label_filter == "funding":
        query += " AND category = 'funding'"
    elif label_filter != "all":
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
        "top": conn.execute("SELECT COUNT(*) FROM jobs WHERE label='top'").fetchone()[0],
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
@login_required
def set_label(job_id, label):
    if label not in ("yes", "no", "maybe", "new", "applied", "top"):
        return jsonify({"error": "invalid label"}), 400
    conn = get_db()
    conn.execute("UPDATE jobs SET label=? WHERE id=?", (label, job_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/job/<job_id>")
@login_required
def job_detail(job_id):
    conn = get_db()
    job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    if not job:
        return "Offre introuvable", 404
    return render_template("job.html", job=job)


@app.route("/add", methods=["GET", "POST"])
@login_required
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


@app.route("/api/clip", methods=["POST"])
def api_clip():
    """Endpoint pour l'extension Firefox — protégé par API key."""
    api_key = request.form.get("api_key", "")
    expected = os.environ.get("DASHBOARD_PASSWORD", "")
    if not expected or api_key != expected:
        resp = jsonify({"error": "Non autorisé"})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp, 401

    import hashlib
    from scraper.scraper import score_job
    url = request.form.get("url", "")
    title = request.form.get("title", "")
    description = request.form.get("description", "")
    location = request.form.get("location", "")
    source = request.form.get("source", "Extension")

    if not title or not url:
        return jsonify({"error": "Titre et URL requis"}), 400

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
    resp = jsonify({"ok": True})
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.route("/stats")
@login_required
def stats_page():
    conn = get_db()

    # Offres rejetées par source
    rejected_by_source = conn.execute("""
        SELECT source, COUNT(*) as cnt
        FROM jobs WHERE label='no'
        GROUP BY source ORDER BY cnt DESC
    """).fetchall()

    # Offres approuvées (yes/maybe/applied) — top 10 par score
    approved = conn.execute("""
        SELECT title, source, location, score, url, label
        FROM jobs WHERE label IN ('yes','maybe','applied')
        ORDER BY score DESC LIMIT 20
    """).fetchall()

    # Mots-clés les plus fréquents dans les offres approuvées
    approved_titles = conn.execute(
        "SELECT title, description FROM jobs WHERE label IN ('yes','maybe','applied')"
    ).fetchall()

    # Stats ML
    ml_stats = conn.execute("""
        SELECT label, COUNT(*) as cnt FROM jobs
        WHERE label NOT IN ('new')
        GROUP BY label
    """).fetchall()

    total_labeled = sum(r['cnt'] for r in ml_stats)
    total_positive = sum(r['cnt'] for r in ml_stats if r['label'] in ('yes','maybe','applied'))
    total_negative = sum(r['cnt'] for r in ml_stats if r['label'] == 'no')

    import os
    model_exists = os.path.exists(os.environ.get("MODEL_PATH", "/data/awajobs_model.pkl"))

    conn.close()
    return render_template("stats.html",
        rejected_by_source=rejected_by_source,
        approved=approved,
        ml_stats=ml_stats,
        total_labeled=total_labeled,
        total_positive=total_positive,
        total_negative=total_negative,
        model_exists=model_exists,
    )


@app.route("/purge-all-no", methods=["POST"])
@login_required
def purge_all_no():
    """Supprime TOUTES les offres labelées 'no'."""
    conn = get_db()
    deleted = conn.execute("DELETE FROM jobs WHERE label='no'").rowcount
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "deleted": deleted})


@app.route("/purge-usa", methods=["POST"])
@login_required
def purge_usa():
    """Supprime les offres non intéressantes hors-Europe (label no ou new)."""
    geo_negative = [
        "usa", "united states", "canada", "australia", "china", "japan",
        "india", "brazil", "singapore", "hong kong", "new york", "california",
        "boston", "chicago", "toronto", "sydney", "melbourne", "beijing",
        "shanghai", "seoul", "tokyo",
    ]
    conn = get_db()
    # Récupérer les offres supprimables (pas yes/maybe/applied)
    rows = conn.execute(
        "SELECT id, title, location, description FROM jobs WHERE label = 'no'"
    ).fetchall()

    to_delete = []
    for row in rows:
        text = ((row["location"] or "") + " " + (row["description"] or "") + " " + (row["title"] or "")).lower()
        remote = any(r in text for r in ["remote", "hybrid", "télétravail", "à distance"])
        if not remote and any(g in text for g in geo_negative):
            to_delete.append(row["id"])

    if to_delete:
        conn.execute(
            f"DELETE FROM jobs WHERE id IN ({','.join('?'*len(to_delete))})",
            to_delete
        )
        conn.commit()
    conn.close()
    return jsonify({"ok": True, "deleted": len(to_delete)})


@app.route("/run-scraper", methods=["POST"])
@login_required
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


@app.route("/train-model", methods=["POST"])
@login_required
def train_model():
    """Entraîne le modèle ML sur les offres labelisées"""
    try:
        import sys
        sys.path.insert(0, "/app")
        from scraper.ml_model import train, stats
        import io, logging
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        logging.getLogger().addHandler(handler)
        model = train()
        logging.getLogger().removeHandler(handler)
        if model is None:
            return jsonify({"ok": False, "error": "Pas assez de données labelisées (min 5 yes + 5 no)"})
        return jsonify({"ok": True, "message": buf.getvalue() or "Modèle entraîné ✓"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Gestion des sources ───────────────────────────────────────────────────────

@app.route("/sources")
@login_required
def sources_page():
    conn = get_db()
    sources = conn.execute("SELECT * FROM sources ORDER BY name").fetchall()
    conn.close()
    return render_template("sources.html", sources=sources)


@app.route("/sources/add", methods=["POST"])
@login_required
def source_add():
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    if not name or not url:
        return jsonify({"error": "Nom et URL requis"}), 400
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO sources (name, url, type, active, created_at) VALUES (?,?,?,1,?)",
            (name, url, "rss", datetime.utcnow().isoformat())
        )
        conn.commit()
    except Exception:
        return jsonify({"error": "URL déjà existante"}), 409
    finally:
        conn.close()
    return redirect(url_for("sources_page"))


@app.route("/sources/<int:source_id>/toggle", methods=["POST"])
@login_required
def source_toggle(source_id):
    conn = get_db()
    conn.execute("UPDATE sources SET active = 1 - active WHERE id = ?", (source_id,))
    conn.commit()
    active = conn.execute("SELECT active FROM sources WHERE id = ?", (source_id,)).fetchone()[0]
    conn.close()
    return jsonify({"ok": True, "active": bool(active)})


@app.route("/sources/<int:source_id>/delete", methods=["POST"])
@login_required
def source_delete(source_id):
    conn = get_db()
    conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("sources_page"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
