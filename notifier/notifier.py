"""
AwaJobs - Notificateur mail
Envoie un digest des nouvelles offres via Gmail
"""

import sqlite3
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import logging

log = logging.getLogger(__name__)

DB_PATH      = os.environ.get("DB_PATH", "/data/awajobs.db")
GMAIL_USER   = os.environ.get("GMAIL_USER", "awajobsradar@gmail.com")
GMAIL_PASS   = os.environ.get("GMAIL_PASS", "")   # App Password 16 chars
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "eva.vives13@gmail.com")


def get_new_jobs(conn, min_score: int = 2) -> list:
    return conn.execute(
        """SELECT * FROM jobs
           WHERE label = 'new' AND score >= ?
           ORDER BY score DESC, created_at DESC
           LIMIT 30""",
        (min_score,)
    ).fetchall()


def build_html(jobs) -> str:
    date_str = datetime.now().strftime("%d %B %Y")
    rows = ""
    for job in jobs:
        score_color = "#16a34a" if job["score"] >= 6 else "#d97706" if job["score"] >= 3 else "#6b7280"
        rows += f"""
        <tr>
          <td style="padding:12px 8px; border-bottom:1px solid #f0ede8; vertical-align:top;">
            <a href="{job['url']}" style="font-weight:600; color:#2563eb; text-decoration:none; font-size:14px;">{job['title']}</a><br>
            <span style="color:#6b6966; font-size:12px;">{job['source']}</span>
            {f'&nbsp;·&nbsp;<span style="color:#6b6966;font-size:12px;">{job["location"]}</span>' if job["location"] else ""}
          </td>
          <td style="padding:12px 8px; border-bottom:1px solid #f0ede8; text-align:center; vertical-align:top;">
            <span style="background:{score_color}20; color:{score_color}; padding:3px 8px; border-radius:6px; font-size:13px; font-weight:600;">{job['score']}</span>
          </td>
        </tr>"""

    return f"""
    <html><body style="font-family:system-ui,sans-serif; background:#f8f7f4; margin:0; padding:0;">
    <div style="max-width:640px; margin:2rem auto; background:#fff; border-radius:12px; border:1px solid #e5e3de; overflow:hidden;">
      <div style="background:#2563eb; padding:1.5rem 2rem;">
        <h1 style="color:#fff; margin:0; font-size:20px; font-weight:600;">AwaJobs — Digest du {date_str}</h1>
        <p style="color:#bfdbfe; margin:4px 0 0; font-size:14px;">{len(jobs)} nouvelle(s) offre(s) à regarder</p>
      </div>
      <div style="padding:1.5rem 2rem;">
        <table style="width:100%; border-collapse:collapse;">
          <thead>
            <tr>
              <th style="text-align:left; font-size:12px; color:#6b6966; padding:0 8px 8px; border-bottom:2px solid #e5e3de;">Offre</th>
              <th style="text-align:center; font-size:12px; color:#6b6966; padding:0 8px 8px; border-bottom:2px solid #e5e3de; width:60px;">Score</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
        <div style="margin-top:1.5rem; text-align:center;">
          <a href="http://localhost:5000" style="background:#2563eb; color:#fff; padding:10px 24px; border-radius:8px; text-decoration:none; font-size:14px; font-weight:500;">
            Ouvrir le dashboard →
          </a>
        </div>
      </div>
      <div style="padding:1rem 2rem; border-top:1px solid #e5e3de; font-size:12px; color:#6b6966; text-align:center;">
        AwaJobs · Radar emploi personnel · <a href="http://localhost:5000" style="color:#2563eb;">Dashboard</a>
      </div>
    </div>
    </body></html>"""


def send_digest():
    if not GMAIL_PASS:
        log.error("GMAIL_PASS non défini — impossible d'envoyer le mail")
        return False

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    jobs = get_new_jobs(conn)

    if not jobs:
        log.info("Aucune nouvelle offre à envoyer")
        conn.close()
        return True

    html = build_html(jobs)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"AwaJobs — {len(jobs)} nouvelle(s) offre(s) [{datetime.now().strftime('%d/%m')}]"
    msg["From"]    = GMAIL_USER
    msg["To"]      = NOTIFY_EMAIL
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASS)
            smtp.sendmail(GMAIL_USER, NOTIFY_EMAIL, msg.as_string())
        log.info("Digest envoyé : %d offres", len(jobs))
        conn.execute("UPDATE jobs SET label='seen' WHERE label='new' AND score >= 2")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Erreur envoi mail : %s", e)
        conn.close()
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    send_digest()
