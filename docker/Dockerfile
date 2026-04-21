FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scraper/ ./scraper/
COPY web/     ./web/
COPY notifier/ ./notifier/
COPY run.py   .

RUN mkdir -p /data

ENV DB_PATH=/data/awajobs.db
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["python", "run.py"]
