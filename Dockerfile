FROM python:3.11-slim

RUN pip install flask uvicorn httpx python-multipart

WORKDIR /app
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]