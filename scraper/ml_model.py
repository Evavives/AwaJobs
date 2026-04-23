"""
AwaJobs - Modèle ML (Sprint 3)
Entraîne un classifieur sur les offres labelisées et prédit yes/no.

Usage :
  python -m scraper.ml_model train    → entraîne et sauvegarde le modèle
  python -m scraper.ml_model stats    → affiche les stats du jeu d'entraînement
"""

import sqlite3
import os
import pickle
import logging

log = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "/data/awajobs.db")
MODEL_PATH = os.environ.get("MODEL_PATH", "/data/awajobs_model.pkl")

# Labels considérés comme "positif" (intéressant)
POSITIVE_LABELS = {"yes", "maybe", "applied"}
# Labels considérés comme "négatif" (pas intéressant)
NEGATIVE_LABELS = {"no"}
# Labels ignorés pour le training
SKIP_LABELS = {"new"}


def _load_training_data():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    rows = conn.execute(
        "SELECT title, description, label FROM jobs WHERE label NOT IN ('new')"
    ).fetchall()
    # Inclure aussi les offres purgées (données d'entraînement conservées)
    try:
        purged = conn.execute(
            "SELECT title, description, label FROM ml_training"
        ).fetchall()
        rows = list(rows) + list(purged)
    except Exception:
        pass
    conn.close()

    X, y = [], []
    for title, description, label in rows:
        if label in SKIP_LABELS:
            continue
        text = f"{title} {description or ''}".strip()
        X.append(text)
        y.append(1 if label in POSITIVE_LABELS else 0)

    return X, y


def train():
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    import numpy as np

    X, y = _load_training_data()
    n_pos = sum(y)
    n_neg = len(y) - n_pos
    log.info("Données : %d offres (%d positives, %d négatives)", len(X), n_pos, n_neg)

    if n_pos < 5 or n_neg < 5:
        log.warning("Pas assez de données labelisées (min 5 positives + 5 négatives). Entraînement annulé.")
        return None

    model = Pipeline([
        ("tfidf", TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            C=1.0,
        )),
    ])

    # Cross-validation pour évaluer
    if len(X) >= 20:
        scores = cross_val_score(model, X, y, cv=min(5, n_pos), scoring="f1")
        log.info("Cross-val F1 : %.2f ± %.2f", np.mean(scores), np.std(scores))

    model.fit(X, y)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    log.info("Modèle sauvegardé : %s", MODEL_PATH)
    return model


def load_model():
    """Charge le modèle depuis le disque. Retourne None si pas encore entraîné."""
    if not os.path.exists(MODEL_PATH):
        return None
    try:
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        log.warning("Impossible de charger le modèle ML : %s", e)
        return None


def predict_score(model, title: str, description: str) -> float:
    """
    Retourne la probabilité que l'offre soit intéressante (0.0 à 1.0).
    """
    text = f"{title} {description or ''}".strip()
    try:
        proba = model.predict_proba([text])[0][1]
        return round(float(proba), 3)
    except Exception:
        return 0.5


def stats():
    X, y = _load_training_data()
    n_pos = sum(y)
    n_neg = len(y) - n_pos
    print(f"Offres labelisées : {len(X)}")
    print(f"  Positives (yes/maybe/applied) : {n_pos}")
    print(f"  Négatives (no)               : {n_neg}")
    if n_pos < 10:
        print(f"  ⚠️  Il faut au moins 10 positives pour un bon modèle (manque {10 - n_pos})")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "train":
        train()
    elif cmd == "stats":
        stats()
    else:
        print("Usage: python -m scraper.ml_model [train|stats]")
