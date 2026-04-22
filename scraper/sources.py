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
        "active": False,  # Surtout des postes US — désactivé par défaut
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
    # ── France ──────────────────────────────────────────────────────────────
    {
        "name": "Les Échos du RISC (CNRS)",
        "url": "https://www.risc.cnrs.fr/rss",
        "type": "rss",
        "active": True,
        "require_keywords": [
            # FR
            "poste", "postdoctorat", "chercheur", "ingénieur", "chargé",
            "maître de conférences", "professeur", "recrutement",
            # EN
            "postdoc", "post-doc", "post doc", "researcher", "research fellow",
            "lecturer", "position", "vacancy", "opening", "hiring",
        ],
    },
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
    # ── Allemagne ────────────────────────────────────────────────────────────
    {
        "name": "Max Planck Society Jobs",
        "url": "https://www.mpg.de/feeds/jobs.rss",
        "type": "rss",
        "active": True,
    },
    {
        "name": "Forschung & Lehre (DE)",
        "url": "https://www.forschung-und-lehre.de/rss/stellenmarkt.xml",
        "type": "rss",
        "active": True,
    },
    # ── UK — Neuroscience ─────────────────────────────────────────────────────
    {
        "name": "jobs.ac.uk — Neuroscience",
        "url": "https://www.jobs.ac.uk/jobs/neuroscience/?format=rss",
        "type": "rss",
        "active": True,
    },
    # ── Fundings ─────────────────────────────────────────────────────────────
    {
        "name": "Funding — EURAXESS Grants",
        "url": (
            "https://euraxess.ec.europa.eu/funding/rss"
            "?f[0]=funding_research_field:317"
            "&f[1]=funding_research_field:322"
        ),
        "type": "rss",
        "active": True,
        "category": "funding",
    },
    # ── Belgique / France (pas de RSS officiel — scraping désactivé pour l'instant) ──
    # FNRS, NWO, INSERM, JRC n'ont pas de flux RSS public fiable.
    # Ils seront ajoutés via scraping HTML en Sprint 3.
]
