from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import Literal
from app.core.config import LLM_MODEL
from app.rag.prompts import KB_GRADER_PROMPT, WEB_GRADER_PROMPT

class EvidenceGrade(BaseModel):
    grade: Literal["good", "bad"] = Field(...)

llm = ChatGroq(
    model=LLM_MODEL,
    temperature=0
)

grader_llm = llm.with_structured_output(
    EvidenceGrade,
    method="json_mode"
)

def grade_kb_evidence(question, documents):
    document_text = "\n\n".join(
        document.page_content for document in documents
    )
    result = grader_llm.invoke(
        KB_GRADER_PROMPT.format(
            question=question,
            documents=document_text
        )
    )
    return result.grade

def grade_web_evidence(question, results):
    result = grader_llm.invoke(
        WEB_GRADER_PROMPT.format(
            question=question,
            results=results
        )
    )
    return result.grade