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
    "postdoc", "post-doc", "post doc", "postdoctorat", "poste",
    "researcher", "research fellow", "lecturer",
    "research officer", "project officer", "behavioral scientist",
    "behavioural scientist", "assistant editor", "research assistant",
    "ingénieur de recherche", "chargé de recherche", "maître de conférences",
    "psychology", "psychologie", "neuroscience", "neuropsychology",
    "neurophysiology", "cognitive", "behavioral", "behavioural",
    "affective", "social neuroscience", "social psychology",
    "psychologie sociale", "moral psychology", "psychologie morale",
    "morale", "morality", "moral", "ethics", "ethical",
    "psychologie cognitive", "cognitive psychology",
    "psychologie expérimentale", "experimental psychology",
    "sciences cognitives", "cognitive science",
    "eeg", "fmri", "brain", "mental health", "cognition", "perception",
    "cooperation", "coopération", "social norms", "normes sociales",
    "punishment", "punition", "sanctions", "emotions", "émotion",
    "culture", "cross-cultural", "intercultural",
    "self identity", "self-identity", "identité", "moral judgment", "moral judgement",
    "jugement moral", "process dissociation", "dual process",
    "political psychology", "psychologie politique",
    "cross-cultural psychology", "psychologie interculturelle",
]

KEYWORDS_NEGATIVE = [
    "manufacturing", "mechanical engineer", "electrical engineer",
    "software engineer", "infrastructure", "devops", "physics",
    "geology", "petroleum",
    # Chimie / biologie moléculaire
    "chemistry", "chimie", "chemical", "chimique",
    "molecular biology", "biologie moléculaire", "molecular", "moléculaire",
    "biochemistry", "biochimie", "biochemical",
    "biomedical", "biomédical", "biomedicine",
    # Maths / stats pures
    "mathematics", "mathématiques", "maths", "mathematician",
    "algebraic", "topology", "number theory",
    # Vision
    "computer vision", "vision artificielle", "image recognition",
    "object detection", "visual recognition",
    "visual neuroscience", "visual system", "visual cortex",
    "visual perception", "visionlist", "optic", "retina", "retinal",
    # NLP / TAL
    "nlp", "natural language processing", "traitement automatique",
    "tal ", "traitement du langage", "language model", "large language",
    "text mining", "speech recognition", "text classification",
    # Neurolinguistique / parole
    "neurolinguistic", "neurolinguistique", "perception de la parole",
    "speech perception", "phonology", "phonologie", "langage oral",
]

# Lieux acceptés — bonus géographique
GEO_POSITIVE = [
    "belgium", "belgique", "bruxelles", "brussels", "ghent", "liège", "leuven",
    "france", "paris", "lyon", "bordeaux", "montpellier", "strasbourg", "nancy",
    "netherlands", "pays-bas", "amsterdam", "rotterdam", "leiden", "utrecht",
    "uk", "united kingdom", "london", "oxford", "cambridge", "edinburgh",
    "europe", "european", "remote", "à distance", "telework", "télétravail",
    "hybrid", "hybride",
]

# Lieux à pénaliser (hors scope sauf remote)
GEO_NEGATIVE = [
    # Amérique du Nord
    "usa", "united states", "u.s.", "u.s.a",
    "new york", "california", "boston", "chicago", "los angeles",
    "san francisco", "seattle", "houston", "washington dc",
    "massachusetts", "new haven", "stanford", "michigan",
    "canada", "toronto", "montreal", "montréal", "vancouver", "ontario",
    # Océanie
    "australia", "sydney", "melbourne", "brisbane", "canberra",
    "new zealand", "nouvelle-zélande",
    # Asie
    "china", "beijing", "shanghai", "hong kong",
    "japan", "tokyo", "osaka",
    "india", "bangalore", "mumbai", "delhi",
    "singapore", "south korea", "seoul", "taiwan",
    # Amérique du Sud
    "brazil", "brasil", "são paulo", "rio de janeiro",
    "argentina", "chile", "colombia",
    # Moyen-Orient / Afrique
    "saudi arabia", "dubai", "qatar", "uae",
    "south africa",
]


FUNDING_KEYWORDS = [
    "grant", "funding", "bourse", "fellowship", "financement", "fonds",
]


def detect_category(title: str, description: str) -> str:
    """Retourne 'funding' si l'offre ressemble à un financement, sinon 'job'."""
    text = (title + " " + description).lower()
    if any(kw in text for kw in FUNDING_KEYWORDS):
        return "funding"
    return "job"


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
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
            category    TEXT DEFAULT 'job',
            created_at  TEXT NOT NULL,
            seen        INTEGER DEFAULT 0
        )
    """)
    # Migration : ajouter category si elle n'existe pas
    try:
        conn.execute("ALTER TABLE jobs ADD COLUMN category TEXT DEFAULT 'job'")
    except Exception:
        pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scrape_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            source     TEXT,
            status     TEXT,
            count      INTEGER,
            scraped_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            url        TEXT NOT NULL UNIQUE,
            type       TEXT DEFAULT 'rss',
            active     INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    # Synchroniser toutes les sources de sources.py dans la DB (INSERT OR IGNORE)
    try:
        from scraper.sources import SOURCES
        for s in SOURCES:
            conn.execute(
                "INSERT OR IGNORE INTO sources (name, url, type, active, created_at) VALUES (?,?,?,?,?)",
                (s["name"], s["url"], s.get("type", "rss"), 1 if s.get("active") else 0, datetime.utcnow().isoformat())
            )
    except Exception:
        pass
    conn.commit()
    conn.close()
    log.info("DB initialisée : %s", DB_PATH)


def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


# Chargement paresseux du modèle ML
_ml_model = None
_ml_model_loaded = False


def _get_ml_model():
    global _ml_model, _ml_model_loaded
    if not _ml_model_loaded:
        try:
            from scraper.ml_model import load_model
            _ml_model = load_model()
            if _ml_model:
                log.info("Modèle ML chargé.")
        except Exception as e:
            log.warning("ML model non disponible : %s", e)
        _ml_model_loaded = True
    return _ml_model


def score_job(title: str, description: str) -> int:
    # Scoring par mots-clés (toujours calculé)
    text = (title + " " + description).lower()
    score = 0
    for kw in KEYWORDS_POSITIVE:
        if kw in text:
            score += 2 if kw in title.lower() else 1
    for kw in KEYWORDS_NEGATIVE:
        if kw in text:
            score -= 3
    # Bonus géographique
    for geo in GEO_POSITIVE:
        if geo in text:
            score += 2
            break
    remote_mentioned = any(r in text for r in ["remote", "à distance", "telework", "hybrid"])
    has_geo_positive = any(g in text for g in GEO_POSITIVE)
    has_geo_negative = any(g in text for g in GEO_NEGATIVE)

    if has_geo_negative and not remote_mentioned:
        if not has_geo_positive:
            # Hors Europe sans remote → score forcé à 0
            return 0
        score -= 4

    # Si modèle ML disponible, remplace le score par la proba ML (0-20)
    model = _get_ml_model()
    if model:
        try:
            from scraper.ml_model import predict_score
            ml_proba = predict_score(model, title, description)
            geo_bonus = 2 if has_geo_positive else 0
            geo_penalty = -4 if has_geo_negative and not remote_mentioned else 0
            return max(0, int(ml_proba * 20) + geo_bonus + geo_penalty)
        except Exception:
            pass

    return max(score, 0)


def save_job(conn, job: dict):
    existing = conn.execute(
        "SELECT id FROM jobs WHERE id = ?", (job["id"],)
    ).fetchone()
    if existing:
        return False
    category = detect_category(job.get("title", ""), job.get("description", "") or "")
    conn.execute(
        """INSERT INTO jobs (id, title, source, url, description, location, score, label, category, created_at)
           VALUES (:id, :title, :source, :url, :description, :location, :score, 'new', :category, :created_at)""",
        {**job, "category": category},
    )
    return True


def scrape_inserm() -> list:
    log.info("INSERM Softy")
    jobs = []
    headers = {"User-Agent": "Mozilla/5.0 AwaJobs/1.0"}
    try:
        resp = requests.get("https://inserm.softy.pro/offres", headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select("article, .offer, .job, li.vacancy, div.offer-item, .card"):
            title_el = item.select_one("h2, h3, h4, .title, .offer-title, a")
            link_el = item.select_one("a[href]")
            if not title_el or not link_el:
                continue
            title = title_el.get_text(strip=True)
            href = link_el["href"]
            full_url = href if href.startswith("http") else "https://inserm.softy.pro" + href
            location_el = item.select_one(".location, .lieu, .city")
            location = location_el.get_text(strip=True) if location_el else "France"
            desc_el = item.select_one("p, .description, .summary")
            description = desc_el.get_text(strip=True) if desc_el else ""
            jobs.append({
                "id": make_id(full_url),
                "title": title,
                "source": "INSERM",
                "url": full_url,
                "description": description[:2000],
                "location": location,
                "score": score_job(title, description + " france europe"),
                "created_at": datetime.utcnow().isoformat(),
            })
    except Exception as e:
        log.error("Erreur INSERM : %s", e)
    log.info("  → %d offres trouvées", len(jobs))
    return jobs


def scrape_jrc() -> list:
    log.info("JRC European Commission")
    jobs = []
    headers = {"User-Agent": "Mozilla/5.0 AwaJobs/1.0"}
    try:
        resp = requests.get("https://recruitment.jrc.ec.europa.eu/vacancies", headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select("article, .vacancy, .job-item, tr.vacancy-row, div.vacancy-item"):
            title_el = item.select_one("h2, h3, h4, .title, a")
            link_el = item.select_one("a[href]")
            if not title_el or not link_el:
                continue
            title = title_el.get_text(strip=True)
            href = link_el["href"]
            full_url = href if href.startswith("http") else "https://recruitment.jrc.ec.europa.eu" + href
            desc_el = item.select_one("p, .description, .summary")
            description = desc_el.get_text(strip=True) if desc_el else ""
            jobs.append({
                "id": make_id(full_url),
                "title": title,
                "source": "JRC (EU Commission)",
                "url": full_url,
                "description": description[:2000],
                "location": "Europe",
                "score": score_job(title, description + " europe belgium"),
                "created_at": datetime.utcnow().isoformat(),
            })
    except Exception as e:
        log.error("Erreur JRC : %s", e)
    log.info("  → %d offres trouvées", len(jobs))
    return jobs


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
    headers = {"User-Agent": "Mozilla/5.0 AwaJobs/1.0"}
    urls = [
        "https://emploi.cnrs.fr/Offres/Recherche.aspx",           # toutes disciplines
        "https://emploi.cnrs.fr/Offres/Recherche.aspx?domaine=6",  # sciences de la vie
    ]
    seen = set()
    for url in urls:
        try:
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
                if full_url in seen:
                    continue
                seen.add(full_url)
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
        except Exception as e:
            log.error("Erreur CNRS (%s) : %s", url, e)
    log.info("  → %d offres trouvées", len(jobs))
    return jobs


def scrape_jobbnorge() -> list:
    log.info("Jobbnorge (Norvège)")
    jobs = []
    headers = {"User-Agent": "Mozilla/5.0 AwaJobs/1.0"}
    for term in ["psychology", "neuroscience", "postdoc"]:
        try:
            url = f"https://www.jobbnorge.no/search/en?term={term}&OrderBy=Published"
            resp = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            for item in soup.select("article, .job-item, li.vacancy"):
                title_el = item.select_one("h2, h3, .title, a")
                link_el = item.select_one("a[href]")
                if not title_el or not link_el:
                    continue
                title = title_el.get_text(strip=True)
                href = link_el["href"]
                full_url = href if href.startswith("http") else "https://www.jobbnorge.no" + href
                location_el = item.select_one(".location, .place, .city")
                location = location_el.get_text(strip=True) if location_el else "Norway"
                desc_el = item.select_one("p, .description, .summary")
                description = desc_el.get_text(strip=True) if desc_el else ""
                jobs.append({
                    "id": make_id(full_url),
                    "title": title,
                    "source": "Jobbnorge",
                    "url": full_url,
                    "description": description[:2000],
                    "location": location,
                    "score": score_job(title, description + " europe"),
                    "created_at": datetime.utcnow().isoformat(),
                })
        except Exception as e:
            log.error("Erreur Jobbnorge (%s) : %s", term, e)
    log.info("  → %d offres trouvées", len(jobs))
    return jobs


def _is_active(conn, name: str) -> bool:
    """Retourne True si la source est active dans la DB (défaut True si absente)."""
    row = conn.execute("SELECT active FROM sources WHERE name = ?", (name,)).fetchone()
    return row is None or bool(row[0])


# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    init_db()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    total_new = 0

    all_jobs = []

    # Sources originales (EURAXESS, Academic Jobs, CNRS)
    for source in RSS_SOURCES:
        all_jobs.extend(scrape_rss(source))
    if _is_active(conn, "CNRS — Emploi-ESR"):
        all_jobs.extend(scrape_cnrs())
    if _is_active(conn, "Jobbnorge (NO)"):
        all_jobs.extend(scrape_jobbnorge())
    if _is_active(conn, "INSERM — Softy"):
        all_jobs.extend(scrape_inserm())
    if _is_active(conn, "JRC — EU Jobs"):
        all_jobs.extend(scrape_jrc())
    # Emails transférés (LinkedIn alerts, etc.)
    try:
        from scraper.email_scraper import scrape_emails
        all_jobs.extend(scrape_emails(score_job))
    except Exception as e:
        log.error("Email scraper : %s", e)

    # Nouvelles sources (jobs.ac.uk, HigherEdJobs)
    try:
        from scraper.sources import SOURCES
        from scraper.rss_scraper import scrape_rss as scrape_rss_new, score_job as score_new
        for source in SOURCES:
            if not source.get("active"):
                continue
            if source["type"] == "rss":
                log.info("RSS : %s", source["name"])
                import feedparser
                feed = feedparser.parse(source["url"])
                for entry in feed.entries:
                    title = entry.get("title", "")
                    url = entry.get("link", "")
                    description = entry.get("summary", "")
                    if not title or not url:
                        continue
                    # Filtre require_keywords : si défini, au moins un mot doit être dans le titre
                    required = source.get("require_keywords")
                    if required:
                        title_lower = title.lower()
                        if not any(kw.lower() in title_lower for kw in required):
                            continue
                    all_jobs.append({
                        "id": make_id(url),
                        "title": title,
                        "source": source["name"],
                        "url": url,
                        "description": description[:2000],
                        "location": "",
                        "score": score_job(title, description),
                        "created_at": datetime.utcnow().isoformat(),
                    })
                log.info("  → %d offres trouvées", len(feed.entries))
    except Exception as e:
        log.error("Erreur nouvelles sources : %s", e)

    for job in all_jobs:
        if save_job(conn, job):
            total_new += 1

    # Purge automatique : supprimer les offres "no" de plus de 90 jours
    try:
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(days=3)).isoformat()
        deleted = conn.execute(
            "DELETE FROM jobs WHERE label='no' AND created_at < ?", (cutoff,)
        ).rowcount
        if deleted:
            log.info("Purge auto : %d offres 'no' supprimées (> 90 jours)", deleted)
    except Exception as e:
        log.error("Purge auto erreur : %s", e)

    conn.commit()
    conn.close()
    log.info("Terminé — %d nouvelles offres ajoutées", total_new)
    return total_new


if __name__ == "__main__":
    run()
