import requests
from bs4 import BeautifulSoup

SITEMAP_URL = "https://www.polimi.it/sitemap-type/pages/sitemap.xml"
BASE_URL = "https://www.polimi.it"



def scarica_sitemap(url):
    headers = {"User-Agent": "Mozilla/5.0 (Svolta-GPT RAG scraper)"}
    risposta = requests.get(url, headers=headers, timeout=15)
    risposta.raise_for_status()
    return risposta.text


def estrai_url(xml_content):
    # features="xml" perché il file è XML grezzo, non HTML
    soup = BeautifulSoup(xml_content, features="xml")
    loc_tags = soup.find_all("loc")
    urls = []
    for tag in loc_tags:
        full_url = tag.get_text(strip=True)
        # trasformiamo l'URL assoluto in path relativo per il filtro
        path = full_url.replace(BASE_URL, "")
        urls.append(path)
    return urls


if __name__ == "__main__":
    print("Scarico la sitemap...")
    html = scarica_sitemap(SITEMAP_URL)

    print("Estraggo gli URL...")
    tutti_gli_url = estrai_url(html)
    print(f"Totale URL trovati nella sitemap: {len(tutti_gli_url)}")

    with open("urls_selezionati.txt", "w") as f:
        for path in tutti_gli_url:
            f.write(BASE_URL + path + "\n")

    print("Salvato in urls_selezionati.txt")