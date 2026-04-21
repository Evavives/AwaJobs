"""
AwaJobs - Scraper principal
Collecte les offres depuis EURAXESS (RSS), Academic Jobs Online (RSS), et CNRS (web)
"""

import sqlite3
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import hashlib
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "/data/awajobs.db")

# ── Sources RSS ──────────────────────────────────────────────────────────────
RSS_SOURCES = [
    {
        "name": "EURAXESS – Psychology & Neuroscience",
        "url": (
            "https://euraxess.ec.europa.eu/jobs/rss"
            "?f[0]=job_research_field:317"
            "&f[1]=job_research_field:322"
            "&f[2]=job_research_field:323"
            "&f[3]=job_research_field:324"
            "&f[4]=job_research_field:374"
            "&f[5]=job_research_field:378"
            "&f[6]=job_research_field:379"
            "&f[7]=offer_type:job_offer"
        ),
    },
    {
        "name": "Academic Jobs Online – Psychology",
        "url": "https://academicjobsonline.org/ajo/rss/feed?field=psychology",
    },
    {
        "name": "Academic Jobs Online – Neuroscience",
        "url": "https://academicjobsonline.org/ajo/rss/feed?field=neuroscience",
    },
]

# ── Mots-clés pour le scoring ─────────────────────────────────────────────
KEYWORDS_POSITIVE = [
    "postdoc", "post-doc", "post doc", "researcher", "research fellow",
    "research officer", "project officer", "behavioral scientist",
    "behavioural scientist", "assistant editor", "research assistant",
    "ingénieur de recherche", "chargé de recherche",
    "psychology", "psychologie", "neuroscience", "neuropsychology",
    "neurophysiology", "cognitive", "behavioral", "behavioural",
    "affective", "social neuroscience", "eeg", "fmri", "brain",
    "mental health", "cognition", "perception",
]

KEYWORDS_NEGATIVE = [
    "manufacturing", "mechanical engineer", "electrical engineer",
    "software engineer", "infrastructure", "devops", "physics",
    "chemistry", "geology", "petroleum",
]


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            source      TEXT NOT NULL,
            url         TEXT NOT NULL,
            description TEXT,
            location    TEXT,
            score       INTEGER DEFAULT 0,
            label       TEXT DEFAULT 'new',
            created_at  TEXT NOT NULL,
            seen        INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scrape_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            source     TEXT,
            status     TEXT,
            count      INTEGER,
            scraped_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    log.info("DB initialisée : %s", DB_PATH)


def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def score_job(title: str, description: str) -> int:
    text = (title + " " + description).lower()
    score = 0
    for kw in KEYWORDS_POSITIVE:
        if kw in text:
            score += 2 if kw in title.lower() else 1
    for kw in KEYWORDS_NEGATIVE:
        if kw in text:
            score -= 3
    return max(score, 0)


def save_job(conn, job: dict):
    existing = conn.execute(
        "SELECT id FROM jobs WHERE id = ?", (job["id"],)
    ).fetchone()
    if existing:
        return False
    conn.execute(
        """INSERT INTO jobs (id, title, source, url, description, location, score, label, created_at)
           VALUES (:id, :title, :source, :url, :description, :location, :score, 'new', :created_at)""",
        job,
    )
    return True


# ── Scrapers ──────────────────────────────────────────────────────────────────
def scrape_rss(source: dict) -> list:
    log.info("RSS : %s", source["name"])
    try:
        feed = feedparser.parse(source["url"])
        jobs = []
        for entry in feed.entries:
            title = entry.get("title", "Sans titre")
            url = entry.get("link", "")
            description = entry.get("summary", "")
            location = entry.get("location", "")
            jobs.append({
                "id": make_id(url),
                "title": title,
                "source": source["name"],
                "url": url,
                "description": description[:2000],
                "location": location,
                "score": score_job(title, description),
                "created_at": datetime.utcnow().isoformat(),
            })
        log.info("  → %d offres trouvées", len(jobs))
        return jobs
    except Exception as e:
        log.error("Erreur RSS %s : %s", source["name"], e)
        return []


def scrape_cnrs() -> list:
    log.info("CNRS emploi.cnrs.fr")
    jobs = []
    try:
        url = "https://emploi.cnrs.fr/Offres/Recherche.aspx?domaine=6"
        headers = {"User-Agent": "Mozilla/5.0 AwaJobs/1.0"}
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        for item in soup.select(".offer-item, .job-item, article.offer"):
            title_el = item.select_one("h2, h3, .offer-title")
            link_el = item.select_one("a[href]")
            if not title_el or not link_el:
                continue
            title = title_el.get_text(strip=True)
            href = link_el["href"]
            full_url = href if href.startswith("http") else "https://emploi.cnrs.fr" + href
            location_el = item.select_one(".location, .lieu")
            location = location_el.get_text(strip=True) if location_el else ""
            desc_el = item.select_one(".description, .summary, p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            jobs.append({
                "id": make_id(full_url),
                "title": title,
                "source": "CNRS Emploi",
                "url": full_url,
                "description": description[:2000],
                "location": location,
                "score": score_job(title, description),
                "created_at": datetime.utcnow().isoformat(),
            })
        log.info("  → %d offres trouvées", len(jobs))
    except Exception as e:
        log.error("Erreur CNRS : %s", e)
    return jobs


# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    total_new = 0

    all_jobs = []
    for source in RSS_SOURCES:
        all_jobs.extend(scrape_rss(source))
    all_jobs.extend(scrape_cnrs())

    for job in all_jobs:
        if save_job(conn, job):
            total_new += 1

    conn.commit()
    conn.close()
    log.info("Terminé — %d nouvelles offres ajoutées", total_new)
    return total_new


if __name__ == "__main__":
    run()
