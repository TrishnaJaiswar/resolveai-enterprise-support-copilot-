from app.rag.retriever import get_retriever

COMPANY_ID = "company_demo"

retriever = get_retriever(COMPANY_ID)

question = "What is the company's password reset policy?"

docs = retriever.invoke(question)

print(f"\nCompany: {COMPANY_ID}")
print(f"Retrieved {len(docs)} documents\n")

for i, doc in enumerate(docs, 1):
    print(f"--- Document {i} ---")
    print(doc.page_content[:1000])
    print()