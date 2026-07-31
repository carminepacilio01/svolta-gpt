FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# installiamo torch CPU-only separatamente, dall'indice ufficiale PyTorch,
# per evitare le pesanti dipendenze CUDA/NVIDIA inutili su un server senza GPU
RUN pip install --no-cache-dir torch==2.2.2 --index-url https://download.pytorch.org/whl/cpu

# installiamo il resto delle dipendenze, escludendo torch (già installato sopra)
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY common_ingest.py .

RUN curl -fL -A "Mozilla/5.0" -o chroma_db.tar.gz https://github.com/carminepacilio01/svolta-gpt/releases/download/v1.0-chroma-db/chroma_db.tar.gz \
    && tar -xzf chroma_db.tar.gz \
    && rm chroma_db.tar.gz

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]