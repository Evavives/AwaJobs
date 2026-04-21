# AwaJobs — Radar emploi personnel

Agrégateur d'offres postdoc/recherche avec dashboard web, scoring automatique et digest mail.

## Structure

```
AwaJobs/
├── scraper/        # Collecte RSS (EURAXESS, Academic Jobs) + CNRS
├── web/            # Dashboard Flask
│   └── templates/  # Pages HTML
├── notifier/       # Digest mail Gmail
├── docker/         # Dockerfile + docker-compose.yml
├── data/           # Base SQLite (créée automatiquement)
├── run.py          # Point d'entrée (scheduler + Flask)
├── requirements.txt
└── .env.example    # Variables d'environnement à remplir
```

## Installation sur NAS Ugreen (Docker)

### 1. Cloner le repo

```bash
git clone https://github.com/Evavives/AwaJobs.git
cd AwaJobs
```

### 2. Créer le fichier .env

```bash
cp .env.example .env
# Édite .env et remplace xxxx xxxx xxxx xxxx par ton App Password Gmail
```

### 3. Lancer via Docker Compose

```bash
cd docker
docker-compose up -d
```

### 4. Accéder au dashboard

Ouvre dans ton navigateur :
```
http://[IP-du-NAS]:5000
```

## Utilisation

- **Dashboard** : liste des offres avec score, filtres par source/label, tri
- **Boutons** : ✓ Postulé / ~ À voir / ✗ Non → entraîne le futur modèle
- **Ajouter manuellement** : pour les offres LinkedIn, X, etc.
- **Lancer la collecte** : bouton en haut à droite, ou automatique chaque matin à 7h
- **Mail digest** : envoyé automatiquement à 8h avec les nouvelles offres scorées ≥ 2

## Sources surveillées

| Source | Méthode | Fréquence |
|--------|---------|-----------|
| EURAXESS | RSS | Quotidien |
| Academic Jobs Online | RSS | Quotidien |
| CNRS Emploi | Scraping | Quotidien |
| LinkedIn / X / autres | Manuel (bouton + ajouter) | À la demande |

## Variables d'environnement

| Variable | Description |
|----------|-------------|
| `GMAIL_USER` | Adresse Gmail expéditrice |
| `GMAIL_PASS` | App Password Gmail (16 caractères) |
| `NOTIFY_EMAIL` | Adresse de réception du digest |
| `DB_PATH` | Chemin vers la base SQLite |
