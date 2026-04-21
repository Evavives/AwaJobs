import feedparser
import sqlite3
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "data/awajobs.db")

# Mots-clés pertinents pour ton profil
KEYWORDS = [
    "postdoc", "post-doc", "post doc",
    "psychology", "psychologie",
    "neuroscience", "neurosciences",
    "cognitive", "behavioral", "behaviour",
    "researcher", "research fellow",
    "chercheur", "chercheuse",
]

COUNTRIES = ["belgium", "france", "netherlands", "uk", "remote",
             "belgique", "pays-bas", "royaume-uni"]

def score_job(title, description):
    """Score simple basé sur mots-clés — sera remplacé par ML en Sprint 3."""
    text = (title + " " + description).lower()
    score = 0
    for kw in KEYWORDS:
        if kw in text:
            score += 2
    for country in COUNTRIES:
        if country in text:
            score += 1
    return min(score, 10)

def scrape_rss(url, source_name):
    """Parse un flux RSS et retourne les offres."""
    jobs = []
    try:
        feed = feedparser.parse(url)
        print(f"[{source_name}] {len(feed.entries)} entrées trouvées")
        for entry in feed.entries:
            title = entry.get("title", "")
            link  = entry.get("link", "")
            desc  = entry.get("summary", entry.get("description", ""))
            pub   = entry.get("published", datetime.now().isoformat())
            if title and link:
                jobs.append({
                    "title": title,
                    "url": link,
                    "source": source_name,
                    "published": pub,
                    "description": desc[:1000],
                    "score": score_job(title, desc),
                })
    except Exception as e:
        print(f"[{source_name}] Erreur: {e}")
    return jobs

def save_jobs(conn, jobs):
    """Sauvegarde les nouvelles offres, ignore les doublons (url unique)."""
    new_count = 0
    for job in jobs:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO jobs
                (title, url, source, published, description, score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (job["title"], job["url"], job["source"],
                  job["published"], job["description"], job["score"]))
            if conn.execute("SELECT changes()").fetchone()[0] > 0:
                new_count += 1
        except Exception as e:
            print(f"Erreur insertion: {e}")
    conn.commit()
    return new_count

def run():
    from scraper.sources import SOURCES
    conn = sqlite3.connect(DB_PATH)
    total = 0
    for source in SOURCES:
        if not source.get("active"):
            continue
        if source["type"] == "rss":
            jobs = scrape_rss(source["url"], source["name"])
            n = save_jobs(conn, jobs)
            print(f"[{source['name']}] {n} nouvelles offres sauvegardées")
            total += n
    conn.close()
    print(f"\nTotal : {total} nouvelles offres")
    return total
