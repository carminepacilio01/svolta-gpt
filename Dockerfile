FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# cache persistente per il modello fastembed, scaricato UNA VOLTA durante il build
ENV FASTEMBED_CACHE_DIR=/app/fastembed_cache
RUN python3 -c "from fastembed import TextEmbedding; TextEmbedding(model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

# diagnostica temporanea: mostra la struttura reale della cache creata
RUN find /app/fastembed_cache -maxdepth 3 -type d

COPY main.py .
COPY common_ingest.py .

RUN curl -fL -A "Mozilla/5.0" -o chroma_db.tar.gz https://github.com/carminepacilio01/svolta-gpt/releases/download/v1.2-chroma-db/chroma_db.tar.gz \
    && tar -xzf chroma_db.tar.gz \
    && rm chroma_db.tar.gz

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
