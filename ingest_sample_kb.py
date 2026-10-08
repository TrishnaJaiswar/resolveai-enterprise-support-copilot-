import os
from pinecone import Pinecone
from app.core.config import PINECONE_INDEX
from app.rag.ingestion import load_and_split_pdf
from app.rag.embeddings import get_embeddings

PDF_PATH = "data/nexora_enterprise.pdf"
COMPANY_ID = "company_demo"

def main():
    print("Loading and splitting PDF...")
    chunks = load_and_split_pdf(PDF_PATH)
    print(f"Created {len(chunks)} chunks.")
    print(f"Target company namespace: {COMPANY_ID}")
    print("Connecting to Pinecone...")
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(PINECONE_INDEX)
    print(f"Creating embeddings for {len(chunks)} chunks...")
    embeddings = get_embeddings()
    vectors = []
    for chunk in chunks:
        vector = embeddings.embed_query(chunk.page_content)
        vectors.append({
            "id": chunk.metadata["chunk_id"],
            "values": vector,
            "metadata": {
                "text": chunk.page_content,
                "company_id": COMPANY_ID,
                **chunk.metadata
            }
        })
    print(f"Uploading vectors to namespace: {COMPANY_ID}...")
    index.upsert(
        vectors=vectors,
        namespace=COMPANY_ID
    )
    print(f"Uploaded {len(vectors)} vectors.")
    print(f"Namespace '{COMPANY_ID}' is ready.")
    print("Ingestion completed successfully.")

if __name__ == "__main__":
    main()