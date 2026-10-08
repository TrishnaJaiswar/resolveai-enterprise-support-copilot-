from langchain_groq import ChatGroq

from langchain_huggingface import HuggingFaceEmbeddings

from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_community.document_loaders import PyPDFLoader

from langgraph.graph import StateGraph, START, END

from langgraph.types import interrupt , Command

from langgraph.checkpoint.sqlite import SqliteSaver

from typing import TypedDict, List, Literal

from pinecone import Pinecone, ServerlessSpec

from langchain_pinecone import PineconeVectorStore

from pydantic import BaseModel, Field

from langchain_core.documents import Document

from langchain_tavily import TavilySearch

import time
import os
import uuid

from datetime import datetime

from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# LOAD DOCUMENT
# ============================================================

loader = PyPDFLoader("nexora_enterprise.pdf")

raw_docs = loader.load()

print("Loaded pages:", len(raw_docs))


# ============================================================
# TEXT SPLITTER
# ============================================================

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
    add_start_index=True
)

chunks = splitter.split_documents(raw_docs)

print("Total chunks:", len(chunks))

print("\nFirst chunk preview:\n")

print(chunks[0].page_content[:900])


# ============================================================
# EMBEDDINGS
# ============================================================

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    encode_kwargs={
        "normalize_embeddings": True
    },
)

sample_vector = embeddings.embed_query(
    "What are the company policies?"
)

print(
    "Embedding dimension:",
    len(sample_vector)
)


# ============================================================
# PINECONE VECTOR DATABASE
# ============================================================

INDEX_NAME = "enterprise-support-copilot"

NAMESPACE = "Langraph-Agentic-Rag"


pc = Pinecone(
    api_key=os.environ["PINECONE_API_KEY"]
)


# Create index only if it does not exist

existing_indexes = [
    i["name"]
    for i in pc.list_indexes()
]


if INDEX_NAME not in existing_indexes:

    pc.create_index(
        name=INDEX_NAME,
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        ),
    )

    while not pc.describe_index(
        INDEX_NAME
    ).status["ready"]:

        time.sleep(1)


print(
    "Pinecone index ready:",
    INDEX_NAME
)


# ============================================================
# PINECONE VECTOR STORE
# ============================================================

vectorstore = PineconeVectorStore.from_documents(
    documents=chunks,
    embedding=embeddings,
    index_name=INDEX_NAME,
    namespace=NAMESPACE,
    pinecone_api_key=os.environ["PINECONE_API_KEY"],
)


retriever = vectorstore.as_retriever(
    search_kwargs={
        "k": 4
    }
)


print(
    "Pinecone vector database and retriever are ready"
)


# ============================================================
# LLM
# ============================================================

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0
)


# ============================================================
# TAVILY WEB SEARCH
# ============================================================

web_search = TavilySearch(
    max_results=5,
    topic="general",
    include_answer=True,
    include_raw_content=False,
)


print(
    "Tavily search tool ready"
)


# ============================================================
# SCHEMAS
# ============================================================

class RouteDecision(BaseModel):

    route: Literal[
        "kb",
        "ticket",
        "direct"
    ] = Field(
        ...,
        description=(
            "kb = company-specific knowledge base question, "
            "ticket = user wants to report or create a support ticket, "
            "direct = general conversation"
        ),
    )


class EvidenceGrade(BaseModel):

    grade: Literal[
        "good",
        "bad"
    ] = Field(
        ...,
        description=(
            "good means the evidence is sufficient to answer "
            "the question; bad means the evidence is insufficient"
        ),
    )


class TicketDetails(BaseModel):

    category: Literal[
        "IT",
        "HR",
        "Security",
        "Facilities"
    ] = Field(
        description="Category of the support ticket"
    )

    issue: str = Field(
        description="Short title describing the user's issue"
    )

    description: str = Field(
        description="Detailed description of the user's problem"
    )

    priority: Literal[
        "Low",
        "Medium",
        "High",
        "Critical"
    ] = Field(
        description="Priority of the ticket"
    )


# ============================================================
# AGENT STATE
# ============================================================

class AgentState(TypedDict):

    question: str

    current_query: str

    kb_docs: List[Document]

    web_results: str

    kb_grade: str

    web_grade: str

    answer: str

    source_used: str

    retry_count: int

    # Ticket information

    ticket_details: dict

    ticket_id: str

    ticket_status: str


# ============================================================
# ROUTER
# ============================================================

router_llm = llm.with_structured_output(
    RouteDecision,
    method="json_mode"
)


def route_question(state: AgentState):

    question = state["question"]

    decision = router_llm.invoke(
        f"""
You are the routing agent for an Enterprise IT Support Copilot.

Your job is to decide the FIRST action required to answer
or handle the user's request.

Choose exactly ONE route.


--------------------------------------------------
1. KB
--------------------------------------------------

Use "kb" when the question is related to company-specific
information.

Examples:

- company policies
- HR policies
- leave
- holidays
- payroll
- work hours
- work from home
- employee benefits
- IT policies
- security policies
- facilities
- internal procedures
- company systems
- employee handbook


--------------------------------------------------
2. TICKET
--------------------------------------------------

Use "ticket" when the user wants to report, raise, open,
or create a support ticket.

Also use "ticket" when the user clearly reports an issue
that requires support from IT, HR, Security, or Facilities.

Examples:

- My laptop is not working.
- My VPN is not connecting.
- Please raise an IT ticket.
- I want to report a security issue.
- My office AC is broken.
- Please create a support ticket.
- I cannot access the company portal.


--------------------------------------------------
3. DIRECT
--------------------------------------------------

Use "direct" only for general conversation that does not
require company-specific knowledge.

Examples:

- Hello
- Hi
- How are you?
- What is machine learning?
- Explain Python.
- What is an API?


--------------------------------------------------
IMPORTANT RULES
--------------------------------------------------

- Prefer "kb" for company-specific information.
- Use "ticket" when the user needs support or ticket creation.
- Do not answer the question yourself.
- Return only the route decision.

User Question:

{question}

Return valid JSON.

Example:

{{"route": "kb"}}
"""
    )

    print(
        "[Router]",
        decision.route
    )

    return {
        "current_query": question,
        "source_used": decision.route
    }


def route_after_router(
    state: AgentState
) -> Literal[
    "retrieve_kb",
    "ticket_agent",
    "direct_answer"
]:

    if state["source_used"] == "kb":

        return "retrieve_kb"

    if state["source_used"] == "ticket":

        return "ticket_agent"

    return "direct_answer"


# ============================================================
# KB RETRIEVAL
# ============================================================

def retrieve_kb(state: AgentState):

    query = state["current_query"]

    docs = retriever.invoke(query)

    print(
        f"[KB Retriever] Query: {query}"
    )

    print(
        f"[KB Retriever] Documents retrieved: {len(docs)}"
    )

    return {
        "kb_docs": docs
    }


# ============================================================
# KB GRADER
# ============================================================

kb_grader_llm = llm.with_structured_output(
    EvidenceGrade,
    method="json_mode"
)


def grade_kb_evidence(state: AgentState):

    question = state["question"]

    context = "\n\n".join(
        f"""
Source: {doc.metadata.get("source")}

Page: {doc.metadata.get("page", "N/A")}

{doc.page_content}
"""
        for doc in state["kb_docs"]
    )

    grade = kb_grader_llm.invoke(
        f"""
You are an evidence grader.

Question:

{question}

Private KB evidence:

{context}

Determine whether the private KB evidence is sufficient
to answer the user's question.

Return:

"good" = evidence sufficiently answers the question.

"bad" = evidence is missing, irrelevant, or insufficient.

Do not use outside knowledge.

Return valid JSON.

Example:

{{"grade": "good"}}
"""
    )

    print(
        "[KB Grader]",
        grade.grade
    )

    return {
        "kb_grade": grade.grade
    }


def decide_after_kb_grade(
    state: AgentState
) -> Literal[
    "generate_from_kb",
    "search_web"
]:

    if state["kb_grade"] == "good":

        return "generate_from_kb"

    return "search_web"


# ============================================================
# TAVILY SEARCH
# ============================================================

def search_web(state: AgentState):

    query = state["current_query"]

    print(
        f"[Tavily Search] Query: {query}"
    )

    result = web_search.invoke(
        {
            "query": query
        }
    )

    if isinstance(result, dict):

        answer = result.get(
            "answer",
            ""
        )

        results = result.get(
            "results",
            []
        )

        lines = []

        if answer:

            lines.append(
                f"Tavily answer: {answer}"
            )

        for item in results:

            lines.append(
                f"""
Title: {item.get("title", "")}

URL: {item.get("url", "")}

Content: {item.get("content", "")}
"""
            )

        web_text = (
            "\n\n".join(lines)
            if lines
            else str(results)
        )

    else:

        web_text = str(result)

    print(
        "[Tavily Search] Result characters:",
        len(web_text)
    )

    return {
        "web_results": web_text,
        "source_used": "web"
    }


# ============================================================
# WEB GRADER
# ============================================================

web_grader_llm = llm.with_structured_output(
    EvidenceGrade,
    method="json_mode"
)


def grade_web_evidence(state: AgentState):

    question = state["question"]

    web_results = state["web_results"]

    grade = web_grader_llm.invoke(
        f"""
You are an evidence grader.

Question:

{question}

Web search evidence:

{web_results}

Can this web evidence answer the question?

Return:

"good" if the evidence sufficiently answers the question.

"bad" if the evidence is missing, irrelevant, or incomplete.

Return valid JSON.

Example:

{{"grade": "good"}}
"""
    )

    print(
        "[Web Grader]",
        grade.grade
    )

    return {
        "web_grade": grade.grade
    }


# ============================================================
# WEB DECISION
# ============================================================

MAX_RETRIES = 5


def decide_after_web_grade(
    state: AgentState
) -> Literal[
    "generate_from_web",
    "rewrite_query",
    "answer_insufficient"
]:

    if state["web_grade"] == "good":

        return "generate_from_web"

    if state["retry_count"] < MAX_RETRIES:

        return "rewrite_query"

    return "answer_insufficient"


# ============================================================
# QUERY REWRITER
# ============================================================

def rewrite_query(state: AgentState):

    question = state["question"]

    retry_count = (
        state["retry_count"] + 1
    )

    rewritten = llm.invoke(
        f"""
Rewrite the question for better retrieval
and web search.

Rules:

- Preserve the original intent.
- Make it specific and search-friendly.
- Return only the rewritten query.

Original question:

{question}
"""
    ).content.strip()

    print(
        "[Rewriter]",
        rewritten
    )

    return {
        "current_query": rewritten,
        "retry_count": retry_count
    }


# ============================================================
# GENERATE FROM KB
# ============================================================

def generate_from_kb(state: AgentState):

    question = state["question"]

    context = "\n\n".join(
        f"""
[KB Source: {doc.metadata.get("source")}]

[Page: {doc.metadata.get("page", "N/A")}]

{doc.page_content}
"""
        for doc in state["kb_docs"]
    )

    answer = llm.invoke(
        f"""
You are an Enterprise IT Support Copilot.

Answer using ONLY the private KB context.

Rules:

- Do not invent unsupported details.
- If the answer is present in the context, answer clearly.
- Mention that the answer is based on the private company
  knowledge base.
- Include the relevant source/page when possible.

Question:

{question}

Private KB context:

{context}
"""
    ).content

    return {
        "answer": answer,
        "source_used": "private_kb"
    }


# ============================================================
# GENERATE FROM WEB
# ============================================================

def generate_from_web(state: AgentState):

    question = state["question"]

    web_results = state["web_results"]

    answer = llm.invoke(
        f"""
You are an Enterprise IT Support Copilot.

Answer the user's question using the provided web evidence.

Rules:

- Do not invent information.
- Use only information supported by the web evidence.
- Clearly mention that the information came from web search.
- If the evidence is insufficient, say so.

Question:

{question}

Web evidence:

{web_results}
"""
    ).content

    return {
        "answer": answer,
        "source_used": "web"
    }


# ============================================================
# DIRECT ANSWER
# ============================================================

def direct_answer(state: AgentState):

    question = state["question"]

    answer = llm.invoke(
        f"""
Respond briefly and naturally.

This is a general conversation and does not require
the private company knowledge base.

User message:

{question}
"""
    ).content

    return {
        "answer": answer,
        "source_used": "direct"
    }


# ============================================================
# INSUFFICIENT EVIDENCE
# ============================================================

def answer_insufficient(state: AgentState):

    answer = (
        "I could not find enough reliable evidence in the "
        "private knowledge base or web search results to "
        "answer this confidently. Please provide more "
        "specific information or rephrase the question."
    )

    return {
        "answer": answer,
        "source_used": "insufficient_evidence"
    }


# ============================================================
# TICKET AGENT
# ============================================================

ticket_llm = llm.with_structured_output(
    TicketDetails,
    method="json_mode"
)


def ticket_agent(state: AgentState):

    question = state["question"]

    ticket = ticket_llm.invoke(
        f"""
You are an Enterprise Support Ticket Agent.

Analyze the user's support request and prepare
a support ticket.


==================================================
ALLOWED CATEGORIES
==================================================

- IT
- HR
- Security
- Facilities


==================================================
ALLOWED PRIORITIES
==================================================

- Low
- Medium
- High
- Critical


==================================================
RULES
==================================================

1. Do not invent information.

2. Create a short issue title.

3. The issue title MUST be stored in the
   field named "issue".

4. NEVER create or return a field named "title".

5. Create a useful description based only
   on the user's message.

6. If the issue blocks the employee from
   working, consider High priority.

7. Possible security or data exposure should
   be High or Critical.

8. Minor issues can be Low or Medium.


==================================================
REQUIRED JSON STRUCTURE
==================================================

Return EXACTLY these four fields:

{{
    "category": "IT",
    "issue": "Laptop WiFi connectivity issue",
    "description": "Employee cannot connect the laptop to the company network.",
    "priority": "High"
}}

The field names MUST be:

- category
- issue
- description
- priority

Do NOT use:

- title
- ticket_title
- problem
- subject


==================================================
USER REQUEST
==================================================

{question}


Return valid JSON.
"""
    )

    print("\n[Ticket Agent]")

    print(
        "Category:",
        ticket.category
    )

    print(
        "Issue:",
        ticket.issue
    )

    print(
        "Description:",
        ticket.description
    )

    print(
        "Priority:",
        ticket.priority
    )

    return {
        "ticket_details": ticket.model_dump(),
        "ticket_status": "awaiting_confirmation"
    }


# ============================================================
# HUMAN CONFIRMATION
# ============================================================

def confirm_ticket(state: AgentState):

    confirmation = interrupt(
        {
            "type": "ticket_confirmation",

            "message": (
                "Do you want to create this "
                "support ticket?"
            ),

            "ticket": state["ticket_details"],
        }
    )

    if (
        confirmation is True
        or str(confirmation).lower() == "yes"
    ):

        return {
            "ticket_status": "confirmed"
        }

    return {
        "ticket_status": "cancelled"
    }


def decide_after_confirmation(
    state: AgentState
) -> Literal[
    "create_ticket",
    "ticket_cancelled"
]:

    if state["ticket_status"] == "confirmed":

        return "create_ticket"

    return "ticket_cancelled"


# ============================================================
# CREATE TICKET
# ============================================================

def create_ticket(
    ticket_details: dict
):

    ticket_id = (
        "INC-"
        + str(uuid.uuid4())[:8].upper()
    )

    return {
        "ticket_id": ticket_id,

        "category":
            ticket_details["category"],

        "issue":
            ticket_details["issue"],

        "description":
            ticket_details["description"],

        "priority":
            ticket_details["priority"],

        "status":
            "Open",

        "created_at":
            datetime.now().isoformat(),
    }


# ============================================================
# CREATE TICKET NODE
# ============================================================

def create_ticket_node(
    state: AgentState
):

    ticket = create_ticket(
        state["ticket_details"]
    )

    print("\n[Ticket Created]")

    print(
        "Ticket ID:",
        ticket["ticket_id"]
    )

    print(
        "Category:",
        ticket["category"]
    )

    print(
        "Issue:",
        ticket["issue"]
    )

    print(
        "Priority:",
        ticket["priority"]
    )

    print(
        "Status:",
        ticket["status"]
    )

    answer = f"""
Your support ticket has been created successfully.

Ticket ID: {ticket["ticket_id"]}

Category: {ticket["category"]}

Issue: {ticket["issue"]}

Priority: {ticket["priority"]}

Status: {ticket["status"]}
"""

    return {
        "ticket_id":
            ticket["ticket_id"],

        "ticket_status":
            "open",

        "answer":
            answer,

        "source_used":
            "ticket_agent"
    }


# ============================================================
# TICKET CANCELLED
# ============================================================

def ticket_cancelled(
    state: AgentState
):

    return {
        "answer":
            "Okay. The support ticket was not created.",

        "source_used":
            "ticket_agent",

        "ticket_status":
            "cancelled"
    }


# ============================================================
# LANGGRAPH WORKFLOW
# ============================================================

workflow = StateGraph(
    AgentState
)


# ============================================================
# NODES
# ============================================================

workflow.add_node(
    "route_question",
    route_question
)

workflow.add_node(
    "retrieve_kb",
    retrieve_kb
)

workflow.add_node(
    "grade_kb_evidence",
    grade_kb_evidence
)

workflow.add_node(
    "search_web",
    search_web
)

workflow.add_node(
    "grade_web_evidence",
    grade_web_evidence
)

workflow.add_node(
    "generate_from_kb",
    generate_from_kb
)

workflow.add_node(
    "generate_from_web",
    generate_from_web
)

workflow.add_node(
    "rewrite_query",
    rewrite_query
)

workflow.add_node(
    "answer_insufficient",
    answer_insufficient
)

workflow.add_node(
    "direct_answer",
    direct_answer
)

workflow.add_node(
    "ticket_agent",
    ticket_agent
)

workflow.add_node(
    "confirm_ticket",
    confirm_ticket
)

workflow.add_node(
    "create_ticket",
    create_ticket_node
)

workflow.add_node(
    "ticket_cancelled",
    ticket_cancelled
)


# ============================================================
# EDGES
# ============================================================

workflow.add_edge(
    START,
    "route_question"
)


workflow.add_conditional_edges(
    "route_question",

    route_after_router,

    {
        "retrieve_kb":
            "retrieve_kb",

        "ticket_agent":
            "ticket_agent",

        "direct_answer":
            "direct_answer",
    }
)


# ------------------------------------------------------------
# KB FLOW
# ------------------------------------------------------------

workflow.add_edge(
    "retrieve_kb",
    "grade_kb_evidence"
)


workflow.add_conditional_edges(
    "grade_kb_evidence",

    decide_after_kb_grade,

    {
        "generate_from_kb":
            "generate_from_kb",

        "search_web":
            "search_web",
    }
)


# ------------------------------------------------------------
# WEB FLOW
# ------------------------------------------------------------

workflow.add_edge(
    "search_web",
    "grade_web_evidence"
)


workflow.add_conditional_edges(
    "grade_web_evidence",

    decide_after_web_grade,

    {
        "generate_from_web":
            "generate_from_web",

        "rewrite_query":
            "rewrite_query",

        "answer_insufficient":
            "answer_insufficient",
    }
)


workflow.add_edge(
    "rewrite_query",
    "search_web"
)


# ------------------------------------------------------------
# TICKET FLOW
# ------------------------------------------------------------

workflow.add_edge(
    "ticket_agent",
    "confirm_ticket"
)


workflow.add_conditional_edges(
    "confirm_ticket",

    decide_after_confirmation,

    {
        "create_ticket":
            "create_ticket",

        "ticket_cancelled":
            "ticket_cancelled",
    }
)


# ============================================================
# END NODES
# ============================================================

for end_node in (

    "generate_from_kb",

    "generate_from_web",

    "direct_answer",

    "answer_insufficient",

    "create_ticket",

    "ticket_cancelled",

):

    workflow.add_edge(
        end_node,
        END
    )


# ============================================================
# SQLITE CHECKPOINTER
# ============================================================

with SqliteSaver.from_conn_string(
    "enterprise_agent.db"
) as checkpointer:

    app = workflow.compile(
        checkpointer=checkpointer
    )

    print(
        "========================================"
    )

    print(
        "Enterprise Agentic RAG Workflow Ready"
    )

    print(
        "========================================"
    )


    # ========================================================
    # TEST CONFIG
    # ========================================================

    config = {
        "configurable": {
            "thread_id": "employee-001"
        }
    }


    # ========================================================
    # FIRST INVOKE
    # ========================================================

    result = app.invoke(
        {
            "question":
                "My laptop WiFi is not working and I cannot connect to the company network. Please create an IT support ticket.",

            "current_query": "",

            "kb_docs": [],

            "web_results": "",

            "kb_grade": "",

            "web_grade": "",

            "answer": "",

            "source_used": "",

            "retry_count": 0,

            "ticket_details": {},

            "ticket_id": "",

            "ticket_status": ""
        },

        config=config
    )


    # ========================================================
    # HUMAN CONFIRMATION
    # ========================================================

    print(
        "\n========================================"
    )

    print(
        "HUMAN CONFIRMATION REQUIRED"
    )

    print(
        "========================================"
    )

    print(result)


    confirmation = input(
        "\nCreate this ticket? Type yes/no: "
    ).strip().lower()


    # ========================================================
    # RESUME GRAPH
    # ========================================================

    result = app.invoke(
        Command(resume=confirmation),
        config=config
    )


    # ========================================================
    # FINAL RESULT
    # ========================================================

    print(
        "\n========================================"
    )

    print(
        "FINAL RESULT"
    )

    print(
        "========================================"
    )

    print(result.get("answer"))