import os
from langchain_pinecone import PineconeVectorStore
from app.core.config import PINECONE_INDEX, RETRIEVAL_K
from app.rag.embeddings import get_embeddings

def get_vectorstore(company_id):
    return PineconeVectorStore(
        index_name=PINECONE_INDEX,
        namespace=company_id,
        embedding=get_embeddings(),
        pinecone_api_key=os.environ["PINECONE_API_KEY"]
    )

def get_retriever(company_id):
    vectorstore = get_vectorstore(company_id)
    return vectorstore.as_retriever(
        search_kwargs={"k": RETRIEVAL_K}
    )