import re
import unicodedata
import chromadb
from fastembed import TextEmbedding

MODELLO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "polimi_docs"

DIMENSIONE_PAROLE_MAX = 250
OVERLAP_PAROLE = 40
DIMENSIONE_PAROLE_MAX_TABELLARE = 500
OVERLAP_PAROLE_TABELLARE = 120


def carica_modello():
    return TextEmbedding(model_name=MODELLO_EMBEDDING)


def calcola_embedding(modello, testi):
    # fastembed restituisce un generatore di array numpy, li convertiamo in liste di float
    return [vettore.tolist() for vettore in modello.embed(testi)]


def carica_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(name=COLLECTION_NAME)


def sanitizza_testo(testo):
    testo = unicodedata.normalize("NFKC", testo)
    testo = re.sub(r"[\xa0\t]+", " ", testo)
    testo = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", testo)
    testo = re.sub(r"\n\s*\n+", "\n\n", testo)
    testo = re.sub(r"[ ]{2,}", " ", testo)
    righe = [riga.strip() for riga in testo.split("\n")]
    testo = "\n".join(riga for riga in righe if riga or True)
    return testo.strip()


def rileva_blocco_tabellare(paragrafo):
    """Euristica semplice: un paragrafo è "tabellare" se contiene molte cifre/simboli euro
    ravvicinati, tipico di tabelle PDF appiattite in testo lineare da pypdf."""
    cifre_e_euro = len(re.findall(r"[\d\u20ac%]", paragrafo))
    lunghezza = max(len(paragrafo), 1)
    densita = cifre_e_euro / lunghezza
    return densita > 0.08


def spezza_in_chunk_adattivo(testo, dimensione_max=DIMENSIONE_PAROLE_MAX, overlap=OVERLAP_PAROLE):
    """Chunking che rispetta i paragrafi naturali, usando parametri più larghi
    per i paragrafi identificati come tabellari, per non spezzare le tabelle a metà."""
    paragrafi = [p.strip() for p in testo.split("\n\n") if p.strip()]

    chunks = []
    buffer_corrente = []
    parole_buffer = 0

    def flush_buffer():
        if buffer_corrente:
            chunks.append("\n\n".join(buffer_corrente))

    for paragrafo in paragrafi:
        e_tabellare = rileva_blocco_tabellare(paragrafo)
        limite_locale = DIMENSIONE_PAROLE_MAX_TABELLARE if e_tabellare else dimensione_max
        overlap_locale = OVERLAP_PAROLE_TABELLARE if e_tabellare else overlap

        parole_paragrafo = paragrafo.split()
        n_parole = len(parole_paragrafo)

        if n_parole > limite_locale:
            flush_buffer()
            buffer_corrente = []
            parole_buffer = 0

            inizio = 0
            while inizio < n_parole:
                fine = inizio + limite_locale
                sotto_chunk = " ".join(parole_paragrafo[inizio:fine])
                chunks.append(sotto_chunk)
                inizio += limite_locale - overlap_locale

        elif parole_buffer + n_parole > limite_locale:
            flush_buffer()
            buffer_corrente = [paragrafo]
            parole_buffer = n_parole
        else:
            buffer_corrente.append(paragrafo)
            parole_buffer += n_parole

    flush_buffer()
    return chunks


def aggiungi_chunk_a_collection(collection, modello, documenti, metadati, ids, batch_size=100):
    for i in range(0, len(documenti), batch_size):
        batch_doc = documenti[i:i + batch_size]
        batch_meta = metadati[i:i + batch_size]
        batch_ids = ids[i:i + batch_size]
        batch_embed = calcola_embedding(modello, batch_doc)

        collection.add(
            documents=batch_doc,
            embeddings=batch_embed,
            metadatas=batch_meta,
            ids=batch_ids,
        )
        print(f"  Salvati {min(i + batch_size, len(documenti))}/{len(documenti)} chunk")
