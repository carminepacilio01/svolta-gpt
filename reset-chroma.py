import chromadb

client = chromadb.PersistentClient(path="./chroma_db")

try:
    client.delete_collection(name="polimi_docs")
    print("Collection 'polimi_docs' eliminata.")
except Exception as e:
    print(f"Nessuna collection da eliminare o errore: {e}")