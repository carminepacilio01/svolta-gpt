FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY common_ingest.py .

# scarichiamo il database vettoriale già popolato da una GitHub Release,
# invece di versionarlo su Git (supera il limite di 100MB per file)
RUN curl -L -o chroma_db.tar.gz https://github.com/carminepacilio01/svolta-gpt/releases/download/v1.0-chroma-db/chroma_db.tar.gz \
    && tar -xzf chroma_db.tar.gz \
    && rm chroma_db.tar.gz

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]