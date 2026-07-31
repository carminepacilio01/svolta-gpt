import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection(name="polimi_docs")
modello = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

query = "quante tasse pago con ISEE 30k?"
embedding_query = modello.encode([query]).tolist()

risultati = collection.query(
    query_embeddings=embedding_query,
    n_results=8,  # ne chiediamo di più per vedere meglio la situazione
)

for i, (doc, meta) in enumerate(zip(risultati["documents"][0], risultati["metadatas"][0])):
    print(f"\n--- Risultato {i+1} ---")
    print(f"Titolo: {meta.get('titolo')}")
    print(f"URL: {meta.get('url')}")
    print(f"Estratto: {doc[:200]}")

print(f"\n\nTotale elementi nella collection: {collection.count()}")