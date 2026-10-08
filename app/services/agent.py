import sqlite3
from typing import Literal, List, TypedDict
from langchain_core.documents import Document
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from langgraph.checkpoint.sqlite import SqliteSaver
from app.core.config import LLM_MODEL, SQLITE_DB
from app.rag.retriever import get_retriever
from app.rag.graders import grade_kb_evidence, grade_web_evidence
from app.rag.prompts import (
    KB_GENERATION_PROMPT,
    WEB_GENERATION_PROMPT,
    DIRECT_ANSWER_PROMPT,
    REWRITE_QUERY_PROMPT
)
from app.services.router import route_question
from app.services.web_search import search_web
from app.services.ticket_agent import create_ticket_details
from app.services.ticket_service import create_ticket

class AgentState(TypedDict, total=False):
    question: str
    company_id: str
    current_query: str
    route: str
    kb_docs: List[Document]
    web_results: str
    kb_grade: str
    web_grade: str
    answer: str
    source_used: str
    retry_count: int
    ticket_details: dict
    ticket_id: str
    ticket_status: str

llm = ChatGroq(
    model=LLM_MODEL,
    temperature=0
)

def route_question_node(state: AgentState):
    route = route_question(state["question"])
    print(f"\n[Router] {route}")
    return {
        "route": route,
        "current_query": state["question"]
    }

def route_after_router(state: AgentState) -> Literal[
    "retrieve_kb",
    "ticket_agent",
    "direct_answer"
]:
    if state["route"] == "kb":
        return "retrieve_kb"
    if state["route"] == "ticket":
        return "ticket_agent"
    return "direct_answer"

def retrieve_kb(state: AgentState):
    retriever = get_retriever(state["company_id"])
    docs = retriever.invoke(state["current_query"])
    print(f"\n[KB Retrieval] Company: {state['company_id']}")
    print(f"[KB Retrieval] Retrieved {len(docs)} documents")
    return {
        "kb_docs": docs
    }

def grade_kb(state: AgentState):
    grade = grade_kb_evidence(
        state["question"],
        state["kb_docs"]
    )
    print(f"[KB Grade] {grade}")
    return {
        "kb_grade": grade
    }

def decide_after_kb_grade(state: AgentState) -> Literal[
    "generate_from_kb",
    "search_web"
]:
    if state["kb_grade"] == "good":
        return "generate_from_kb"
    return "search_web"

def generate_from_kb(state: AgentState):
    print("[KB Generation] Starting...")
    context = "\n\n".join(
        doc.page_content
        for doc in state["kb_docs"]
    )
    prompt = KB_GENERATION_PROMPT.format(
        context=context,
        question=state["question"]
    )
    print("[KB Generation] Calling Groq...")
    response = llm.invoke(prompt)
    print("[KB Generation] Groq response received")
    return {
        "answer": response.content,
        "source_used": "internal_kb"
    }

def search_web_node(state: AgentState):
    query = state["current_query"]
    results = search_web(query)
    print("\n[Web Search]")
    return {
        "web_results": str(results)
    }

def grade_web(state: AgentState):
    grade = grade_web_evidence(
        state["question"],
        state["web_results"]
    )
    print(f"[Web Grade] {grade}")
    return {
        "web_grade": grade
    }

def decide_after_web_grade(state: AgentState) -> Literal[
    "generate_from_web",
    "rewrite_query",
    "answer_insufficient"
]:
    if state["web_grade"] == "good":
        return "generate_from_web"
    if state.get("retry_count", 0) < 2:
        return "rewrite_query"
    return "answer_insufficient"

def generate_from_web(state: AgentState):
    prompt = WEB_GENERATION_PROMPT.format(
        context=state["web_results"],
        question=state["question"]
    )
    response = llm.invoke(prompt)
    return {
        "answer": response.content,
        "source_used": "web"
    }

def rewrite_query(state: AgentState):
    prompt = REWRITE_QUERY_PROMPT.format(
        question=state["question"],
        results=state["web_results"]
    )
    response = llm.invoke(prompt)
    retry_count = state.get("retry_count", 0) + 1
    print(f"[Rewrite] Retry {retry_count}")
    return {
        "current_query": response.content,
        "retry_count": retry_count
    }

def answer_insufficient(state: AgentState):
    return {
        "answer": "I could not find enough reliable information to answer your question.",
        "source_used": "insufficient_evidence"
    }

def direct_answer(state: AgentState):
    prompt = DIRECT_ANSWER_PROMPT.format(
        question=state["question"]
    )
    response = llm.invoke(prompt)
    return {
        "answer": response.content,
        "source_used": "direct"
    }

def ticket_agent_node(state: AgentState):
    ticket = create_ticket_details(state["question"])
    print("\n[Ticket Agent]")
    print("Category:", ticket.category)
    print("Issue:", ticket.issue)
    print("Description:", ticket.description)
    print("Priority:", ticket.priority)
    return {
        "ticket_details": ticket.model_dump(),
        "ticket_status": "awaiting_confirmation"
    }

def confirm_ticket(state: AgentState):
    confirmation = interrupt({
        "type": "ticket_confirmation",
        "message": "Do you want to create this support ticket?",
        "ticket": state["ticket_details"]
    })
    if confirmation is True or str(confirmation).lower() == "yes":
        return {
            "ticket_status": "confirmed"
        }
    return {
        "ticket_status": "cancelled"
    }

def decide_after_confirmation(state: AgentState) -> Literal[
    "create_ticket",
    "ticket_cancelled"
]:
    if state["ticket_status"] == "confirmed":
        return "create_ticket"
    return "ticket_cancelled"

def create_ticket_node(state: AgentState):
    ticket = create_ticket(
        state["ticket_details"],
        state["company_id"]
    )
    answer = f"""Your support ticket has been created successfully.

Ticket ID: {ticket["ticket_id"]}

Category: {ticket["category"]}

Issue: {ticket["issue"]}

Priority: {ticket["priority"]}

Status: {ticket["status"]}"""
    return {
        "ticket_id": ticket["ticket_id"],
        "ticket_status": "open",
        "answer": answer,
        "source_used": "ticket_agent"
    }

def ticket_cancelled(state: AgentState):
    return {
        "answer": "Okay. The support ticket was not created.",
        "source_used": "ticket_agent",
        "ticket_status": "cancelled"
    }

def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("route_question", route_question_node)
    workflow.add_node("retrieve_kb", retrieve_kb)
    workflow.add_node("grade_kb_evidence", grade_kb)
    workflow.add_node("generate_from_kb", generate_from_kb)
    workflow.add_node("search_web", search_web_node)
    workflow.add_node("grade_web_evidence", grade_web)
    workflow.add_node("generate_from_web", generate_from_web)
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("answer_insufficient", answer_insufficient)
    workflow.add_node("direct_answer", direct_answer)
    workflow.add_node("ticket_agent", ticket_agent_node)
    workflow.add_node("confirm_ticket", confirm_ticket)
    workflow.add_node("create_ticket", create_ticket_node)
    workflow.add_node("ticket_cancelled", ticket_cancelled)

    workflow.add_edge(START, "route_question")

    workflow.add_conditional_edges(
        "route_question",
        route_after_router,
        {
            "retrieve_kb": "retrieve_kb",
            "ticket_agent": "ticket_agent",
            "direct_answer": "direct_answer"
        }
    )

    workflow.add_edge(
        "retrieve_kb",
        "grade_kb_evidence"
    )

    workflow.add_conditional_edges(
        "grade_kb_evidence",
        decide_after_kb_grade,
        {
            "generate_from_kb": "generate_from_kb",
            "search_web": "search_web"
        }
    )

    workflow.add_edge(
        "search_web",
        "grade_web_evidence"
    )

    workflow.add_conditional_edges(
        "grade_web_evidence",
        decide_after_web_grade,
        {
            "generate_from_web": "generate_from_web",
            "rewrite_query": "rewrite_query",
            "answer_insufficient": "answer_insufficient"
        }
    )

    workflow.add_edge(
        "rewrite_query",
        "search_web"
    )

    workflow.add_edge(
        "ticket_agent",
        "confirm_ticket"
    )

    workflow.add_conditional_edges(
        "confirm_ticket",
        decide_after_confirmation,
        {
            "create_ticket": "create_ticket",
            "ticket_cancelled": "ticket_cancelled"
        }
    )

    for end_node in [
        "generate_from_kb",
        "generate_from_web",
        "direct_answer",
        "answer_insufficient",
        "create_ticket",
        "ticket_cancelled"
    ]:
        workflow.add_edge(end_node, END)

    return workflow

def get_app():
    workflow = build_graph()
    connection = sqlite3.connect(
        SQLITE_DB,
        check_same_thread=False
    )
    checkpointer = SqliteSaver(connection)
    return workflow.compile(
        checkpointer=checkpointer
    )