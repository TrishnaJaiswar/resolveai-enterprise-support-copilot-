from typing import Literal
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from app.core.config import LLM_MODEL

class TicketDetails(BaseModel):
    category: Literal["IT", "HR", "Security", "Facilities"]
    issue: str
    description: str
    priority: Literal["Low", "Medium", "High", "Critical"]

llm = ChatGroq(
    model=LLM_MODEL,
    temperature=0
)

ticket_llm = llm.with_structured_output(
    TicketDetails,
    method="json_mode"
)

TICKET_PROMPT = """You are an Enterprise Support Ticket Agent.

Analyze the user's support request and prepare a support ticket.

Allowed categories:
- IT
- HR
- Security
- Facilities

Allowed priorities:
- Low
- Medium
- High
- Critical

Rules:
1. Do not invent information.
2. Create a short issue title.
3. The issue title MUST be stored in the field named "issue".
4. NEVER create or return a field named "title".
5. Create a useful description based only on the user's message.
6. If the issue blocks the employee from working, consider High priority.
7. Possible security or data exposure should be High or Critical.
8. Minor issues can be Low or Medium.

Return exactly these four fields:
- category
- issue
- description
- priority

Do not use:
- title
- ticket_title
- problem
- subject

User request:
{question}

Return valid JSON.
"""

def create_ticket_details(question):
    ticket = ticket_llm.invoke(
        TICKET_PROMPT.format(question=question)
    )
    return ticket