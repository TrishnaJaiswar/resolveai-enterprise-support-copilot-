import os
from pinecone import Pinecone
from app.core.config import PINECONE_INDEX
from app.rag.embeddings import get_embeddings

COMPANY_A = "company_demo"
COMPANY_B = "company_other"

def upload_company_b():
    with open("data/company_other.txt", "r", encoding="utf-8") as file:
        text = file.read()
    embeddings = get_embeddings()
    vector = embeddings.embed_query(text)
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(PINECONE_INDEX)
    index.upsert(
        vectors=[
            {
                "id": "company-other-policy-001",
                "values": vector,
                "metadata": {
                    "text": text,
                    "company_id": COMPANY_B
                }
            }
        ],
        namespace=COMPANY_B
    )
    print(f"Uploaded test document to namespace: {COMPANY_B}")

def test_isolation():
    from app.rag.retriever import get_retriever

    question = "What is the password reset policy?"

    retriever_a = get_retriever(COMPANY_A)
    retriever_b = get_retriever(COMPANY_B)

    docs_a = retriever_a.invoke(question)
    docs_b = retriever_b.invoke(question)

    print(f"\n{COMPANY_A} results:")
    for doc in docs_a:
        print(doc.page_content[:300])
        print()

    print(f"\n{COMPANY_B} results:")
    for doc in docs_b:
        print(doc.page_content[:300])
        print()

if __name__ == "__main__":
    upload_company_b()
    test_isolation()