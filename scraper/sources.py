SOURCES = [
    # ── Europe / International ───────────────────────────────────────────────
    {
        "name": "EURAXESS — Psychology & Neuroscience",
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
        "type": "rss",
        "active": True,
    },
    {
        "name": "Academic Jobs Online — Psychology",
        "url": "https://academicjobsonline.org/ajo/rss/feed?field=psychology",
        "type": "rss",
        "active": True,
    },
    {
        "name": "Academic Jobs Online — Neuroscience",
        "url": "https://academicjobsonline.org/ajo/rss/feed?field=neuroscience",
        "type": "rss",
        "active": True,
    },
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
    # ── Belgique / France (scraping HTML) ────────────────────────────────────
    {
        "name": "CNRS — Emploi-ESR",
        "url": "https://emploi.cnrs.fr/",
        "type": "html",
        "active": True,
    },
    {
        "name": "INSERM — Softy",
        "url": "https://inserm.softy.pro/offres",
        "type": "html",
        "active": True,
    },
    {
        "name": "JRC — EU Jobs",
        "url": "https://joint-research-centre.ec.europa.eu/jobs_en",
        "type": "html",
        "active": True,
    },
    # ── Norvège ──────────────────────────────────────────────────────────────
    {
        "name": "Jobbnorge (NO)",
        "url": "https://www.jobbnorge.no/",
        "type": "html",
        "active": True,
    },
]
