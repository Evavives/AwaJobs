SOURCES = [
    # ── UK ──────────────────────────────────────────────────────────────────
    {
        "name": "jobs.ac.uk — Psychology",
        "url": "https://www.jobs.ac.uk/jobs/psychology/?format=rss",
        "type": "rss",
        "active": True,
    },
    {
        "name": "jobs.ac.uk — Biological Sciences",
        "url": "https://www.jobs.ac.uk/jobs/biological-sciences/?format=rss",
        "type": "rss",
        "active": True,
    },
    {
        "name": "jobs.ac.uk — Health & Medical",
        "url": "https://www.jobs.ac.uk/jobs/health-and-medical/?format=rss",
        "type": "rss",
        "active": True,
    },
    # ── USA / International académique ──────────────────────────────────────
    {
        "name": "HigherEdJobs — Psychology",
        "url": "https://www.higheredjobs.com/rss/categoryFeed.cfm?catID=91",
        "type": "rss",
        "active": True,
    },
    {
        "name": "Nature Careers",
        "url": "https://www.nature.com/naturecareers/rss/jobs",
        "type": "rss",
        "active": True,
    },
    {
        "name": "Science Careers (AAAS)",
        "url": "https://jobs.sciencecareers.org/rss/jobs/",
        "type": "rss",
        "active": True,
    },
    {
        "name": "Chronicle of Higher Education",
        "url": "https://jobs.chronicle.com/jobs/rss/",
        "type": "rss",
        "active": True,
    },
    # ── Pays-Bas ─────────────────────────────────────────────────────────────
    {
        "name": "Academic Transfer (NL)",
        "url": "https://www.academictransfer.com/en/jobs/rss/",
        "type": "rss",
        "active": True,
    },
    # ── ONG / Institutions internationales ──────────────────────────────────
    {
        "name": "ReliefWeb — Research Jobs",
        "url": "https://reliefweb.int/jobs/rss.xml?search[field_career_categories]=20966",
        "type": "rss",
        "active": True,
    },
    {
        "name": "Impactpool",
        "url": "https://www.impactpool.org/feeds/jobs.rss",
        "type": "rss",
        "active": True,
    },
    # ── Belgique / France (pas de RSS officiel — scraping désactivé pour l'instant) ──
    # FNRS, NWO, INSERM, JRC n'ont pas de flux RSS public fiable.
    # Ils seront ajoutés via scraping HTML en Sprint 3.
]
