"""
AwaJobs - Point d'entrée principal
Lance le scheduler (scraper + notifier) + le serveur web Flask
"""

import sys
import os
sys.path.insert(0, "/app")

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
log = logging.getLogger(__name__)


def scheduled_scrape():
    log.info("Scraping planifié — démarrage")
    from scraper.scraper import run
    count = run()
    log.info("Scraping terminé — %d nouvelles offres", count)


def scheduled_notify():
    log.info("Notification planifiée — démarrage")
    from notifier.notifier import send_digest
    send_digest()


def main():
    from scraper.scraper import init_db
    init_db()

    scheduler = BackgroundScheduler(timezone="Europe/Brussels")

    # Scraping toutes les nuits à 7h00
    scheduler.add_job(
        scheduled_scrape,
        CronTrigger(hour=7, minute=0),
        id="scraper",
        name="Scraper quotidien"
    )

    # Mail digest tous les matins à 8h00
    scheduler.add_job(
        scheduled_notify,
        CronTrigger(hour=8, minute=0),
        id="notifier",
        name="Digest mail quotidien"
    )

    scheduler.start()
    log.info("Scheduler démarré — scraping à 7h, digest à 8h (heure de Bruxelles)")

    # Premier scraping au démarrage si la base est vide
    from scraper.scraper import init_db
    import sqlite3
    db_path = os.environ.get("DB_PATH", "/data/awajobs.db")
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    conn.close()
    if count == 0:
        log.info("Base vide — premier scraping immédiat")
        scheduled_scrape()

    # Démarrage Flask (bloquant)
    import sys
    sys.path.insert(0, "/app/web")
    from web.app import app
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
