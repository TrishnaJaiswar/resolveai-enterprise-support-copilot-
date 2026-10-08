import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone
from app.core.config import PINECONE_INDEX
from app.rag.embeddings import get_embeddings

def load_and_split_pdf(pdf_path):
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = splitter.split_documents(documents)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"{pdf_path}:chunk_{i}"
    return chunks

def ingest_pdf_to_pinecone(pdf_path, company_id):
    print(f"[INGESTION] Loading PDF: {pdf_path}")
    chunks = load_and_split_pdf(pdf_path)
    print(f"[INGESTION] Created {len(chunks)} chunks")
    if not chunks:
        raise ValueError("The PDF does not contain readable text.")
    print("[INGESTION] Loading embedding model...")
    embeddings = get_embeddings()
    print("[INGESTION] Creating embeddings...")
    texts = [chunk.page_content for chunk in chunks]
    vectors_values = embeddings.embed_documents(texts)
    print(f"[INGESTION] Created {len(vectors_values)} embeddings")
    print("[INGESTION] Connecting to Pinecone...")
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(PINECONE_INDEX)
    vectors = []
    for chunk, vector in zip(chunks, vectors_values):
        metadata = {
            "text": chunk.page_content,
            "company_id": company_id,
            "source_file": os.path.basename(pdf_path),
            **chunk.metadata
        }
        vectors.append({
            "id": chunk.metadata["chunk_id"],
            "values": vector,
            "metadata": metadata
        })
    batch_size = 100
    print(f"[INGESTION] Uploading to Pinecone namespace: {company_id}")
    for start in range(0, len(vectors), batch_size):
        batch = vectors[start:start + batch_size]
        index.upsert(
            vectors=batch,
            namespace=company_id
        )
        print(
            f"[INGESTION] Uploaded "
            f"{min(start + batch_size, len(vectors))}/{len(vectors)} vectors"
        )
    print("[INGESTION] PDF ingestion completed successfully")
    return len(chunks)