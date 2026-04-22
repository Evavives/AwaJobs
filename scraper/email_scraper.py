"""
AwaJobs - Email scraper
Lit la boîte awajobsradar@gmail.com via IMAP et extrait les offres
des alertes LinkedIn (et autres) transférées.

Prérequis Gmail : activer IMAP + générer un App Password (compte Google
→ Sécurité → Mots de passe des applications).
"""

import imaplib
import email
import re
import os
import logging
from email.header import decode_header
from bs4 import BeautifulSoup
from datetime import datetime
import hashlib

log = logging.getLogger(__name__)

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_PASS = os.environ.get("GMAIL_PASS", "")


def _make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _decode_str(value) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def _get_html_body(msg) -> str:
    """Extrait la partie HTML d'un email (multipart ou non)."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
    else:
        if msg.get_content_type() == "text/html":
            charset = msg.get_content_charset() or "utf-8"
            return msg.get_payload(decode=True).decode(charset, errors="replace")
    return ""


def _parse_linkedin_alert(html: str, email_subject: str) -> list:
    """
    Parse un email d'alerte LinkedIn.
    LinkedIn envoie les offres dans des blocs répétitifs avec :
    - titre du poste (lien)
    - nom de l'entreprise
    - localisation
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    seen_urls = set()

    # LinkedIn job alerts : chaque offre est dans un <a> avec le titre,
    # suivi de texte pour l'entreprise et la ville.
    # On cherche tous les liens qui pointent vers linkedin.com/jobs/view/
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Nettoyer les liens de tracking (redirections LinkedIn)
        # Format typique: https://www.linkedin.com/jobs/view/JOBID ou
        # https://linkedin.com/comm/jobs/view/JOBID
        clean_url = _extract_linkedin_url(href)
        if not clean_url or clean_url in seen_urls:
            continue
        seen_urls.add(clean_url)

        title = a.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        # L'entreprise et la localisation sont souvent dans les éléments suivants
        company = ""
        location = ""
        parent = a.parent
        if parent:
            siblings_text = parent.get_text(separator="|", strip=True)
            parts = [p.strip() for p in siblings_text.split("|") if p.strip()]
            if len(parts) >= 2:
                company = parts[1] if parts[1] != title else ""
            if len(parts) >= 3:
                location = parts[2]

        jobs.append({
            "id": _make_id(clean_url),
            "title": title,
            "source": "LinkedIn (email)",
            "url": clean_url,
            "description": f"Via alerte email : {email_subject}",
            "location": location,
            "company": company,
            "created_at": datetime.utcnow().isoformat(),
        })

    return jobs


def _extract_linkedin_url(href: str) -> str:
    """Extrait l'URL propre d'un lien LinkedIn (sans tracking)."""
    if not href:
        return ""
    # URL directe
    if "linkedin.com/jobs/view/" in href:
        # Garder seulement jusqu'à la fin de l'ID numérique
        match = re.search(r"(https?://(?:www\.)?linkedin\.com/jobs/view/\d+)", href)
        if match:
            return match.group(1)
    # URL de tracking LinkedIn → extraire le paramètre url= ou redirectUrl=
    if "linkedin.com" in href:
        match = re.search(r"[?&](?:url|redirectUrl)=([^&]+)", href)
        if match:
            from urllib.parse import unquote
            inner = unquote(match.group(1))
            if "linkedin.com/jobs/view/" in inner:
                m2 = re.search(r"(https?://(?:www\.)?linkedin\.com/jobs/view/\d+)", inner)
                if m2:
                    return m2.group(1)
        # URL LinkedIn générique (company pages, etc.) → ignorer
        if "/jobs/view/" in href:
            return href.split("?")[0]
    return ""


def _parse_generic_email(html: str, subject: str, sender: str) -> list:
    """
    Parser générique pour les autres emails d'offres transférés.
    Extrait tous les liens qui ressemblent à des offres d'emploi.
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    seen = set()

    job_patterns = [
        r"jobs?\.", r"/job/", r"/jobs/", r"/careers?/", r"/offres?/",
        r"/emploi", r"/vacancy", r"/vacancies", r"/position",
        r"jobbnorge", r"euraxess", r"academicjobsonline",
    ]

    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        if not title or len(title) < 10:
            continue
        if not any(re.search(p, href, re.I) for p in job_patterns):
            continue
        clean = href.split("?")[0].split("#")[0]
        if clean in seen:
            continue
        seen.add(clean)

        jobs.append({
            "id": _make_id(clean),
            "title": title[:200],
            "source": "LinkedIn (email)",
            "url": clean,
            "description": f"Via email transféré : {subject}",
            "location": "",
            "created_at": datetime.utcnow().isoformat(),
        })

    return jobs


def scrape_emails(score_fn) -> list:
    """
    Connexion IMAP à awajobsradar@gmail.com.
    Lit les emails non lus, extrait les offres, marque comme lus.
    score_fn : la fonction score_job de scraper.py
    """
    if not GMAIL_USER or not GMAIL_PASS:
        log.warning("Email scraper : GMAIL_USER ou GMAIL_PASS manquant, skip.")
        return []

    jobs = []
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("INBOX")

        # Chercher les emails non lus
        status, data = mail.search(None, "UNSEEN")
        if status != "OK" or not data[0]:
            log.info("Email scraper : aucun email non lu.")
            mail.logout()
            return []

        ids = data[0].split()
        log.info("Email scraper : %d email(s) non lu(s)", len(ids))

        for msg_id in ids:
            try:
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                subject = _decode_str(msg.get("Subject", ""))
                sender = _decode_str(msg.get("From", ""))
                html = _get_html_body(msg)

                if not html:
                    log.info("  Email '%s' : pas de HTML, skip", subject[:50])
                    continue

                log.info("  Parsing email : '%s' de %s", subject[:60], sender[:40])

                # Dispatcher selon l'expéditeur
                if "linkedin" in sender.lower():
                    raw_jobs = _parse_linkedin_alert(html, subject)
                else:
                    raw_jobs = _parse_generic_email(html, subject, sender)

                # Scorer et ajouter
                for j in raw_jobs:
                    j["score"] = score_fn(j["title"], j.get("description", ""))
                    jobs.append(j)

                # Marquer l'email comme lu
                mail.store(msg_id, "+FLAGS", "\\Seen")
                log.info("  → %d offres extraites", len(raw_jobs))

            except Exception as e:
                log.error("  Erreur traitement email %s : %s", msg_id, e)

        mail.logout()

    except imaplib.IMAP4.error as e:
        log.error("Email scraper IMAP erreur : %s", e)
    except Exception as e:
        log.error("Email scraper erreur inattendue : %s", e)

    log.info("Email scraper total : %d offres extraites", len(jobs))
    return jobs
