import requests
from bs4 import BeautifulSoup
import time
import json

HEADERS = {"User-Agent": "Mozilla/5.0 (Svolta-GPT RAG scraper)"}


def carica_urls(path="urls_selezionati.txt"):
    with open(path, "r") as f:
        return [riga.strip() for riga in f if riga.strip()]


def scarica_pagina(url):
    risposta = requests.get(url, headers=HEADERS, timeout=15)
    risposta.raise_for_status()
    return risposta.text


def estrai_contenuto(html, url):
    soup = BeautifulSoup(html, "lxml")

    # Rimuoviamo tag che sicuramente non sono contenuto utile
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    titolo = soup.find("h1")
    titolo_testo = titolo.get_text(strip=True) if titolo else ""

    # Prendiamo il tag <main> se esiste, altrimenti tutto il <body>
    main = soup.find("main") or soup.find("body")
    testo = main.get_text(separator="\n", strip=True) if main else ""

    return {
        "url": url,
        "titolo": titolo_testo,
        "testo": testo,
    }


if __name__ == "__main__":
    urls = carica_urls()
    print(f"Trovati {len(urls)} URL da scaricare\n")

    risultati = []
    errori = []

    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{len(urls)}] {url}")
        try:
            html = scarica_pagina(url)
            dati = estrai_contenuto(html, url)

            # scartiamo pagine con pochissimo testo (probabilmente vuote o errori mascherati)
            if len(dati["testo"]) < 100:
                print("   -> scartata, troppo corta")
                continue

            risultati.append(dati)
        except Exception as e:
            print(f"   -> ERRORE: {e}")
            errori.append({"url": url, "errore": str(e)})

        time.sleep(1)  # pausa di cortesia tra le richieste

    print(f"\nCompletato: {len(risultati)} pagine salvate, {len(errori)} errori")

    with open("contenuti_scrapati.json", "w", encoding="utf-8") as f:
        json.dump(risultati, f, ensure_ascii=False, indent=2)

    if errori:
        with open("errori_scraping.json", "w", encoding="utf-8") as f:
            json.dump(errori, f, ensure_ascii=False, indent=2)

    print("Salvato in contenuti_scrapati.json")