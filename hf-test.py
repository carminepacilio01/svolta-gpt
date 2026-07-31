import os
import requests
from dotenv import load_dotenv

load_dotenv()

MODELLO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
url = f"https://router.huggingface.co/hf-inference/models/{MODELLO}/pipeline/feature-extraction"

r = requests.post(
    url,
    headers={"Authorization": f"Bearer {os.environ.get('HF_API_TOKEN')}"},
    json={"inputs": ["prova di embedding"], "options": {"wait_for_model": True}},
    timeout=30,
)
print("Status:", r.status_code)
dati = r.json()
if isinstance(dati, list):
    print("Dimensione vettore:", len(dati[0]))
else:
    print("Risposta:", dati)