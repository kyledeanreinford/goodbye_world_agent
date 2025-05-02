FROM python:3.11-slim

RUN pip install flask uvicorn httpx python-multipart gunicorn

WORKDIR /app
COPY . /app

EXPOSE 8000

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "api:app"]