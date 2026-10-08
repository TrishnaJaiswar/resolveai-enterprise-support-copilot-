from typing import Literal
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from app.core.config import LLM_MODEL

class RouteDecision(BaseModel):
    route: Literal["kb", "ticket", "direct"] = Field(...)

llm = ChatGroq(
    model=LLM_MODEL,
    temperature=0
)

router_llm = llm.with_structured_output(
    RouteDecision,
    method="json_mode"
)

ROUTER_PROMPT = """You are the routing agent for an enterprise IT support copilot.

Classify the user's request into exactly one route.

Routes:

kb:
Use this when the question can be answered using the company's internal knowledge base, policies, procedures, or support documentation.

ticket:
Use this when the employee is explicitly asking to create, raise, or submit a support ticket.

direct:
Use this for general conversation, greetings, simple questions, or questions that do not require internal company knowledge or ticket creation.

Return valid JSON.

The JSON must contain exactly one field:
{{
    "route": "kb"
}}

The route value must be exactly one of:
"kb"
"ticket"
"direct"

User question:
{question}
"""

def route_question(question):
    result = router_llm.invoke(
        ROUTER_PROMPT.format(question=question)
    )
    return result.route