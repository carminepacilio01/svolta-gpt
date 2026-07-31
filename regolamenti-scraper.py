import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import time
import json

BASE_URL = "https://www.normativa.polimi.it"
HEADERS = {"User-Agent": "Mozilla/5.0 (RAG-project educational scraper)"}

# pagine indice da cui partire: home sezione + paginazione + sotto-categorie note
PAGINE_INDICE = [
    "/regolamenti-generali",
    "/regolamenti-generali/2",
    "/regolamenti-generali/3",
    "/regolamenti-generali/regolamenti-scuole",
    "/regolamenti-generali/regolamenti-dipartimenti",
    "/regolamenti-generali/regolamenti-poli-territoriali",
    "/studenti",
    "/codici",
    "/privacy-e-sicurezza"
]


CARTELLA_PDF = "pdf_regolamenti"


def scarica_pagina(url):
    risposta = requests.get(url, headers=HEADERS, timeout=15)
    risposta.raise_for_status()
    return risposta.text


def estrai_link_pdf(html, url_pagina):
    soup = BeautifulSoup(html, "lxml")
    link_pdf = []
    for tag_a in soup.find_all("a", href=True):
        href = tag_a["href"]
        if href.lower().endswith(".pdf"):
            url_assoluto = urljoin(url_pagina, href)
            titolo = tag_a.get_text(strip=True) or os.path.basename(href)
            link_pdf.append({"url": url_assoluto, "titolo": titolo})
    return link_pdf


def scarica_pdf(url, percorso_locale):
    risposta = requests.get(url, headers=HEADERS, timeout=30)
    risposta.raise_for_status()
    with open(percorso_locale, "wb") as f:
        f.write(risposta.content)


def nome_file_sicuro(titolo, url):
    # ricava un nome file leggibile ma sicuro dal titolo, fallback sul nome nell'URL
    base = titolo if titolo else os.path.basename(url)
    base = "".join(c if c.isalnum() or c in " -_." else "_" for c in base)
    base = base.strip()[:120]  # limite di lunghezza per sicurezza
    if not base.lower().endswith(".pdf"):
        base += ".pdf"
    return base


if __name__ == "__main__":
    os.makedirs(CARTELLA_PDF, exist_ok=True)

    tutti_link_pdf = []
    for path_indice in PAGINE_INDICE:
        url_indice = BASE_URL + path_indice
        print(f"Scansiono indice: {url_indice}")
        try:
            html = scarica_pagina(url_indice)
            link_trovati = estrai_link_pdf(html, url_indice)
            print(f"  -> trovati {len(link_trovati)} link PDF")
            tutti_link_pdf.extend(link_trovati)
        except Exception as e:
            print(f"  -> ERRORE: {e}")
        time.sleep(1)

    # rimuove duplicati mantenendo l'ordine (stesso PDF può comparire in più pagine indice)
    visti = set()
    link_unici = []
    for link in tutti_link_pdf:
        if link["url"] not in visti:
            visti.add(link["url"])
            link_unici.append(link)

    print(f"\nTotale PDF unici da scaricare: {len(link_unici)}")

    metadati_pdf = []
    for i, link in enumerate(link_unici, start=1):
        nome_file = nome_file_sicuro(link["titolo"], link["url"])
        percorso_locale = os.path.join(CARTELLA_PDF, nome_file)

        print(f"[{i}/{len(link_unici)}] {nome_file}")
        try:
            scarica_pdf(link["url"], percorso_locale)
            metadati_pdf.append({
                "titolo": link["titolo"],
                "url": link["url"],
                "file_locale": percorso_locale,
            })
        except Exception as e:
            print(f"  -> ERRORE: {e}")
        time.sleep(1)

    with open("pdf_metadati.json", "w", encoding="utf-8") as f:
        json.dump(metadati_pdf, f, ensure_ascii=False, indent=2)

    print(f"\nCompletato. {len(metadati_pdf)} PDF salvati in ./{CARTELLA_PDF}/")
    print("Metadati salvati in pdf_metadati.json")