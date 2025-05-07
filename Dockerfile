FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update \
 && apt-get install -y --no-install-recommends vim \
 && rm -rf /var/lib/apt/lists/*

COPY goodbye_world/ goodbye_world/

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "goodbye_world.api:app"]