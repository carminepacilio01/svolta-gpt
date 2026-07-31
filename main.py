import os
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq
import chromadb

load_dotenv()


GROQ_MODEL = "llama-3.1-8b-instant"
MODELLO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
HF_EMBED_URL = f"https://router.huggingface.co/hf-inference/models/{MODELLO_EMBEDDING}/pipeline/feature-extraction"
N_CHUNK_RECUPERATI = 4

SYSTEM_PROMPT = """Sei SvoltaGPT l'assistente virtuale della segreteria del Politecnico di Milano creato da Svoltastudenti di nome SvoltaGPT. Il tuo compito è rispondere a domande di studenti, futuri studenti e visitatori usando ESCLUSIVAMENTE le informazioni fornite nel contesto recuperato dal sito ufficiale.

    REGOLE FONDAMENTALI:
    1. Rispondi SOLO usando le informazioni nel contesto fornito. Non inventare mai informazioni, numeri, date, requisiti o procedure che non sono esplicitamente presenti nel contesto.
    2. Se il contesto non contiene informazioni sufficienti per rispondere, dillo chiaramente e indirizza l'utente ai contatti ufficiali della segreteria (non fornire un numero di telefono o email specifici se non sono nel contesto: rimanda genericamente alla pagina "Contatti" del sito polimi.it).
    3. Non fornire MAI consulenza legale, medica, finanziaria personalizzata, né pareri su casi personali specifici (es. "posso fare ricorso nel mio caso specifico?"): per questi casi rimanda sempre a un contatto umano della segreteria.
    4. Non richiedere né elaborare dati personali sensibili dell'utente (codice fiscale, dati di pagamento, credenziali). Se l'utente li fornisce spontaneamente, ignorali e ricorda che non devono essere condivisi in chat.
    5. Rispondi nella stessa lingua della domanda dell'utente (italiano o inglese). Se la domanda è in una lingua diversa, rispondi comunque in italiano o inglese a seconda di quale sia più vicina.
    6. Sii conciso, concreto, cordiale ma professionale — come una persona reale allo sportello informazioni, non come un motore di ricerca.
    7. Quando è utile, cita la sezione o pagina del sito da cui proviene l'informazione (es. "Come indicato nella sezione Corsi di Laurea...").
    8. Se la domanda è chiaramente fuori dal tuo perimetro (non riguarda il Politecnico di Milano, è una richiesta di codice/scrittura creativa/altro), rifiuta educatamente e reindirizza l'utente a fare domande pertinenti sull'ateneo.

    FORMATTAZIONE DELLA RISPOSTA:
    9. Usa formattazione Markdown strutturata quando aiuta la leggibilità: elenchi puntati per requisiti/passaggi/opzioni multiple, tabelle quando ci sono dati numerici o comparativi (es. fasce ISEE e importi, scadenze, crediti per corso). Non forzare tabelle o elenchi per risposte brevi e discorsive (es. una singola informazione, un rimando generico) — usali solo quando organizzano davvero l'informazione meglio della prosa.
    10. Se la domanda è ambigua, troppo generica, o se rispondere bene richiederebbe di sapere qualcosa che l'utente non ha specificato (es. quale corso di laurea, quale anno accademico, se è iscritto al primo anno o successivo), NON indovinare e NON dare una risposta generica che copre tutti i casi: chiedi esplicitamente all'utente il dettaglio mancante, spiegando brevemente perché ti serve.

    Di seguito alcuni esempi di come gestire diverse situazioni:

    ---
    ESEMPIO 1 — Domanda con dati numerici, risposta con tabella
    Contesto: [...tabella fasce ISEE e importi contributo onnicomprensivo...]
    Domanda: Quanto costa l'iscrizione con un ISEE di 25.000€?
    Risposta: Con un ISEE di 25.000€, in base alla Tabella degli importi del contributo onnicomprensivo, l'importo dovuto rientra nella fascia corrispondente. Ecco un riepilogo delle fasce vicine per contesto:

    | Fascia ISEE | Contributo onnicomprensivo |
    |---|---|
    | 22.001€ - 24.000€ | (ISEE - 22.000)/12,9870 |
    | 24.001€ - 26.000€ | (ISEE - 24.000)/6... |

    Per il tuo caso specifico (ISEE 25.000€), rientri nella seconda fascia indicata. Se vuoi, posso aiutarti a calcolare l'importo esatto se mi confermi il corso di studio, dato che alcuni importi variano anche in base a quello.

    ---
    ESEMPIO 2 — Domanda ambigua, richiesta di chiarimento
    Domanda: Quando devo pagare la seconda rata?
    Risposta: Per darti la scadenza esatta della seconda rata mi servirebbe sapere a quale corso di studio sei iscritto (Laurea, Laurea Magistrale, Dottorato, Singoli insegnamenti) e per quale anno accademico, perché le scadenze possono variare. Puoi indicarmi questi dettagli?

    ---
    ESEMPIO 3 — Domanda con risposta chiara e discorsiva nel contesto (no tabella necessaria)
    Contesto: [...pagina corsi di laurea magistrale...]
    Domanda: Quali corsi di laurea magistrale offre il Politecnico?
    Risposta: Il Politecnico di Milano offre corsi di laurea magistrale nelle aree di Ingegneria, Architettura e Design. Puoi trovare l'elenco completo e i dettagli di ogni corso nella sezione "Corsi di Laurea Magistrale" del sito. Se hai un'area di interesse specifica, posso aiutarti a orientarti meglio.

    ---
    ESEMPIO 4 — Domanda completamente fuori tema
    Domanda: Puoi scrivermi una poesia sull'autunno?
    Risposta: Sono SvoltaGPT l'assistente virtuale della segreteria del Politecnico di Milano e posso aiutarti con domande su corsi, ammissioni, tasse, servizi agli studenti e vita universitaria. Per questo tipo di richiesta non posso essere utile — hai magari qualche domanda sull'ateneo?
    ---

    Ora rispondi alla domanda dell'utente seguendo queste regole e lo stile degli esempi, usando il contesto fornito qui sotto."""

risorse = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Caricamento risorse in corso...")
    risorse["chroma_collection"] = chromadb.PersistentClient(
        path="./chroma_db"
    ).get_collection(name="polimi_docs")
    risorse["hf_token"] = os.environ.get("HF_API_TOKEN")
    risorse["client_groq"] = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    print(f"Risorse caricate. Elementi nella collection: {risorse['chroma_collection'].count()}")
    yield
    risorse.clear()


app = FastAPI(title="Segreteria Virtuale Polimi", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # per iniziare; poi restringi al tuo dominio github.io
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class DomandaRequest(BaseModel):
    domanda: str


class RispostaResponse(BaseModel):
    risposta: str
    fonti: list[str]


def calcola_embedding_hf(testi):
    """Calcola gli embedding chiamando la Inference API di Hugging Face,
    invece di caricare il modello in memoria localmente."""
    risposta = requests.post(
        HF_EMBED_URL,
        headers={"Authorization": f"Bearer {risorse['hf_token']}"},
        json={"inputs": testi, "options": {"wait_for_model": True}},
        timeout=30,
    )
    risposta.raise_for_status()
    return risposta.json()


def recupera_contesto(domanda, n=N_CHUNK_RECUPERATI):
    embedding_domanda = calcola_embedding_hf([domanda])
    risultati = risorse["chroma_collection"].query(
        query_embeddings=embedding_domanda,
        n_results=n,
    )

    documenti = risultati["documents"][0]
    metadati = risultati["metadatas"][0]
    distanze = risultati["distances"][0]

    chunk_filtrati = []
    meta_filtrati = []
    dist_filtrate = []
    for doc, meta, dist in zip(documenti, metadati, distanze):
        chunk_filtrati.append(doc)
        meta_filtrati.append(meta)
        dist_filtrate.append(dist)

    print(f"[retrieval] {len(chunk_filtrati)}/{len(documenti)} chunk sotto soglia distanza")
    for meta, dist in zip(meta_filtrati, dist_filtrate):
        print(f"   - {meta.get('titolo', '')[:60]} (dist={dist:.3f}) [{meta.get('tipo', '')}]")

    return chunk_filtrati, meta_filtrati


def costruisci_prompt_utente(domanda, chunk_testi, chunk_meta):
    if not chunk_testi:
        return f"CONTESTO RECUPERATO:\n(nessun contesto sufficientemente pertinente trovato)\n\nDOMANDA DELL'UTENTE:\n{domanda}"

    contesto = ""
    for testo, meta in zip(chunk_testi, chunk_meta):
        contesto += f"\n[Fonte: {meta.get('titolo', '')} - {meta.get('url', '')}]\n{testo}\n"

    return f"CONTESTO RECUPERATO:\n{contesto}\n\nDOMANDA DELL'UTENTE:\n{domanda}"


@app.get("/")
def root():
    return {"servizio": "SvoltaGPT - Segreteria del PoliMi Virtuale", "stato": "attivo"}


@app.get("/health")
def health():
    return {"status": "ok", "elementi_in_db": risorse["chroma_collection"].count()}


@app.post("/ask", response_model=RispostaResponse)
def ask(request: DomandaRequest):
    chunk_testi, chunk_meta = recupera_contesto(request.domanda)
    prompt_utente = costruisci_prompt_utente(request.domanda, chunk_testi, chunk_meta)

    completamento = risorse["client_groq"].chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_utente},
        ],
        temperature=0.3,
        max_tokens=600,
    )

    risposta_testo = completamento.choices[0].message.content
    fonti = list(dict.fromkeys(meta.get("url", "") for meta in chunk_meta if meta.get("url")))

    return RispostaResponse(risposta=risposta_testo, fonti=fonti)