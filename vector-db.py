import json
from pypdf import PdfReader

from common_ingest import (
    carica_modello,
    carica_collection,
    sanitizza_testo,
    spezza_in_chunk_adattivo,  # <-- cambiato
    aggiungi_chunk_a_collection,
)

def processa_pagine_html(path_json, modello, collection, prefisso_id):
    print(f"\n=== Processo pagine HTML da {path_json} ===")
    with open(path_json, "r", encoding="utf-8") as f:
        pagine = json.load(f)
    print(f"Pagine caricate: {len(pagine)}")

    documenti, metadati, ids = [], [], []
    contatore = 0

    for pagina in pagine:
        testo_grezzo = pagina.get("testo", "")
        if not testo_grezzo or len(testo_grezzo.strip()) < 100:
            continue

        testo_pulito = sanitizza_testo(testo_grezzo)
        chunks = spezza_in_chunk_adattivo(testo_pulito)

        for chunk in chunks:
            if len(chunk.strip()) < 50:
                continue
            documenti.append(chunk)
            metadati.append({
                "url": pagina.get("url", ""),
                "titolo": pagina.get("titolo", ""),
                "tipo": "pagina_web",
            })
            ids.append(f"{prefisso_id}_{contatore}")
            contatore += 1

    print(f"Chunk creati: {len(documenti)}")
    aggiungi_chunk_a_collection(collection, modello, documenti, metadati, ids)
    return len(documenti)


def processa_pdf(path_metadati_json, modello, collection, prefisso_id, tipo_documento):
    print(f"\n=== Processo PDF da {path_metadati_json} ===")
    with open(path_metadati_json, "r", encoding="utf-8") as f:
        lista_pdf = json.load(f)
    print(f"PDF da processare: {len(lista_pdf)}")

    documenti, metadati, ids = [], [], []
    contatore = 0
    falliti = []

    for pdf in lista_pdf:
        try:
            reader = PdfReader(pdf["file_locale"])
            testo_pagine = [p.extract_text() for p in reader.pages if p.extract_text()]
            testo_grezzo = "\n".join(testo_pagine)

            if not testo_grezzo or len(testo_grezzo.strip()) < 50:
                falliti.append(pdf["file_locale"])
                continue

            testo_pulito = sanitizza_testo(testo_grezzo)
            chunks = spezza_in_chunk_adattivo(testo_pulito)

            for chunk in chunks:
                if len(chunk.strip()) < 50:
                    continue
                documenti.append(chunk)
                metadati.append({
                    "url": pdf.get("url") or "",
                    "titolo": pdf.get("titolo", ""),
                    "tipo": tipo_documento,
                })
                ids.append(f"{prefisso_id}_{contatore}")
                contatore += 1

        except Exception as e:
            print(f"  -> ERRORE su {pdf['file_locale']}: {e}")
            falliti.append(pdf["file_locale"])

    print(f"Chunk creati: {len(documenti)}")
    if falliti:
        print(f"PDF falliti ({len(falliti)}): {falliti}")
    aggiungi_chunk_a_collection(collection, modello, documenti, metadati, ids)
    return len(documenti)


def processa_regolamenti_corsi(path_json, modello, collection, prefisso_id):
    print(f"\n=== Processo regolamenti corsi da {path_json} ===")
    with open(path_json, "r", encoding="utf-8") as f:
        regolamenti = json.load(f)
    print(f"Regolamenti caricati: {len(regolamenti)}")

    documenti, metadati, ids = [], [], []
    contatore = 0

    for regolamento in regolamenti:
        testo_grezzo = regolamento.get("testo", "")
        if not testo_grezzo or len(testo_grezzo.strip()) < 100:
            continue

        testo_pulito = sanitizza_testo(testo_grezzo)
        chunks = spezza_in_chunk_adattivo(testo_pulito)

        for chunk in chunks:
            if len(chunk.strip()) < 50:
                continue
            documenti.append(chunk)
            metadati.append({
                "url": regolamento.get("url", ""),
                "titolo": regolamento.get("titolo", "Regolamento didattico"),
                "tipo": "regolamento_corso_laurea",
            })
            ids.append(f"{prefisso_id}_{contatore}")
            contatore += 1

    print(f"Chunk creati: {len(documenti)}")
    aggiungi_chunk_a_collection(collection, modello, documenti, metadati, ids)
    return len(documenti)


if __name__ == "__main__":
    print("Carico il modello di embedding multilingue (prima volta: scarica il modello)...")
    modello = carica_modello()

    print("Mi connetto a ChromaDB...")
    collection = carica_collection()

    totale = 0
    totale += processa_pagine_html("contenuti_scrapati.json", modello, collection, "html_chunk")
    totale += processa_pdf("pdf_metadati.json", modello, collection, "pdf_normativa_chunk", "pdf_regolamento_generale")
    totale += processa_regolamenti_corsi("regolamenti.json", modello, collection, "regcorso_chunk")

    # se hai anche i PDF di ingindinf con metadati validi (URL veri), scommenta:
    # totale += processa_pdf("pdf_metadati_ingindinf.json", modello, collection, "pdf_ingindinf_chunk", "pdf_regolamento_scuola")

    print(f"\n=== COMPLETATO ===")
    print(f"Totale chunk inseriti in questa esecuzione: {totale}")
    print(f"Totale elementi nella collection: {collection.count()}")