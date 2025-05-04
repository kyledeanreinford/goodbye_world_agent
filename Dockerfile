FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY goodbye_world/ goodbye_world/

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "goodbye_world.api:app"]