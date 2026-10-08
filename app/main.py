from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langgraph.types import Command
from app.services.agent import get_app
from app.services.ticket_service import get_tickets
from app.rag.ingestion import ingest_pdf_to_pinecone

app = FastAPI(
    title="ResolveAI Enterprise Support Copilot",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

agent = get_app()

class ChatRequest(BaseModel):
    question: str
    company_id: str
    thread_id: str

class TicketConfirmationRequest(BaseModel):
    thread_id: str
    confirmation: str

@app.get("/")
def root():
    return {
        "service": "ResolveAI Enterprise Support Copilot",
        "status": "running"
    }

@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    company_id: str = Form(...)
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file was provided."
        )
    filename = Path(file.filename).name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )
    if not company_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Company ID is required."
        )
    upload_dir = Path("data/uploads") / company_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / filename
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(
                status_code=400,
                detail="The uploaded PDF is empty."
            )
        pdf_path.write_bytes(contents)
        chunks_count = ingest_pdf_to_pinecone(
            str(pdf_path),
            company_id
        )
        return {
            "status": "success",
            "message": "PDF uploaded and added to the knowledge base.",
            "filename": filename,
            "company_id": company_id,
            "chunks": chunks_count
        }
    except HTTPException:
        raise
    except Exception as error:
        print(f"[PDF UPLOAD ERROR] {type(error).__name__}")
        print(error)
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
@app.post("/chat")
def chat(request: ChatRequest):
    try:
        print("\n[CHAT] Request received")
        print(f"[CHAT] Question: {request.question}")
        print(f"[CHAT] Company: {request.company_id}")
        print(f"[CHAT] Thread: {request.thread_id}")

        config = {
            "configurable": {
                "thread_id": request.thread_id
            }
        }

        print("[CHAT] Calling agent.invoke()...")

        result = agent.invoke(
            {
                "question": request.question,
                "company_id": request.company_id,
                "retry_count": 0
            },
            config=config
        )

        print("[CHAT] agent.invoke() completed")
        print("[CHAT] Result:", result)

        interrupts = result.get("__interrupt__", [])

        if interrupts:
            print("[CHAT] Interrupt detected")

            interrupt_value = interrupts[0].value

            return {
                "status": "awaiting_confirmation",
                "confirmation_required": True,
                "message": interrupt_value.get(
                    "message",
                    "Please confirm this action."
                ),
                "ticket": interrupt_value.get("ticket")
            }

        response_data = {
            "status": "completed",
            "answer": result.get("answer", ""),
            "source": result.get("source_used", ""),
            "ticket_id": result.get("ticket_id"),
            "ticket_status": result.get("ticket_status")
        }

        print("[CHAT] Sending response:")
        print(response_data)

        return response_data

    except Exception as error:
        print(f"[CHAT ERROR] {type(error).__name__}")
        print(error)

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

@app.post("/ticket/confirm")
def confirm_ticket(request: TicketConfirmationRequest):
    try:
        config = {
            "configurable": {
                "thread_id": request.thread_id
            }
        }
        confirmation = request.confirmation.lower().strip()
        result = agent.invoke(
            Command(resume=confirmation),
            config=config
        )
        return {
            "status": "completed",
            "answer": result.get("answer", ""),
            "source": result.get("source_used", ""),
            "ticket_id": result.get("ticket_id"),
            "ticket_status": result.get("ticket_status")
        }
    except Exception as error:
        print(f"[TICKET CONFIRMATION ERROR] {type(error).__name__}")
        print(error)
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

@app.get("/tickets")
def tickets(company_id: str):
    try:
        return {
            "tickets": get_tickets(company_id)
        }
    except Exception as error:
        print(f"[TICKETS ERROR] {type(error).__name__}")
        print(error)
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )