# ResolveAI — Enterprise Agentic Support Copilot

> An enterprise agentic AI platform that combines RAG, intelligent routing, evidence grading, web intelligence, and human-in-the-loop ticket automation to resolve employee support requests reliably.

---

## 📌 Overview

ResolveAI is an enterprise support intelligence platform designed to assist employees with common workplace IT and operational issues.

Instead of treating every request as a simple chatbot query, ResolveAI uses a **stateful agentic workflow** to determine the appropriate resolution path:

- Search trusted internal enterprise knowledge.
- Evaluate whether the retrieved evidence is sufficient.
- Fall back to web intelligence when internal knowledge is insufficient.
- Rewrite unsuccessful search queries and retry.
- Generate structured support tickets when human intervention is required.
- Require explicit employee approval before creating a ticket.

The system is designed around the principle:

> **Retrieve → Verify → Decide → Act → Respond**

---

# 🏗️ System Architecture

<img width="1536" height="1024" alt="ff9138fd-ec59-4b2a-a777-4d6812d4ffe7" src="https://github.com/user-attachments/assets/a72fd3e4-a5b7-4af3-8403-b0fdcbdde994" />


```text
                         User Request
                              │
                              ▼
                       Intent Router
                              │
                 ┌────────────┼────────────┐
                 │            │            │
                 ▼            ▼            ▼
                KB          Ticket       Direct
                 │           Agent        Answer
                 ▼            │
             Pinecone         ▼
             Retrieval    Human Approval
                 │            │
                 ▼            ▼
          Evidence Grader  Create Ticket
                 │
            ┌────┴────┐
            │         │
           Good      Bad
            │         │
            ▼         ▼
         Generate   Web Search
         Answer        │
                       ▼
                 Web Evidence
                    Grader
                       │
                  ┌────┴────┐
                  │         │
                 Good      Bad
                  │         │
                  ▼         ▼
              Generate   Rewrite Query
              Answer         │
                             ▼
                        Retry Search
```

---

# 🎯 Why I Built This Project

Traditional enterprise support systems often depend on employees searching through documentation, navigating multiple support portals, or manually creating tickets.

At the same time, a basic LLM chatbot introduces another problem: it can generate confident answers that are not supported by company policies or documentation.

I wanted to build a system that demonstrates how **Agentic AI and RAG can be applied to a realistic enterprise support workflow**, rather than building another basic PDF chatbot.

The project focuses on three practical problems:

1. **Finding the right information**
2. **Determining whether the retrieved information is trustworthy**
3. **Taking action when an answer alone is not enough**

This led to the design of ResolveAI as an **agentic support workflow rather than a conventional chatbot**.

---

# ❗ Problem Statement

Enterprise employees frequently face questions such as:

- How do I reset my password?
- What is the company's IT policy?
- How do I troubleshoot a network issue?
- What should I do if my laptop is lost?
- Can I raise a support ticket for this issue?

A conventional keyword-based support system has several limitations.

### 1. Information is distributed

Enterprise knowledge may exist across:

- IT documentation
- HR policies
- Security guidelines
- Internal handbooks
- Support documentation

Finding the correct information manually can be time-consuming.

### 2. Traditional RAG can retrieve irrelevant information

A vector database may return documents that are semantically similar but do not actually contain enough evidence to answer the question.

Simply passing retrieved documents to an LLM can therefore produce unsupported answers.

### 3. Internal knowledge is not always sufficient

Company documentation cannot answer every possible question.

The system therefore needs a controlled mechanism for obtaining external information when internal knowledge is insufficient.

### 4. Some requests require action

An employee asking:

> "My laptop WiFi is not working. Please create a support ticket."

doesn't need another paragraph of troubleshooting advice.

They need an actual support workflow.

### 5. Automated actions require human control

Automatically creating tickets without employee confirmation can result in incorrect or unwanted requests.

Therefore, actions should include a **human approval step**.

---

# 💡 Solution

ResolveAI addresses these problems using a **LangGraph-based agentic workflow**.

Instead of following one fixed RAG pipeline, the system dynamically chooses the appropriate path based on the user's request.

```text
                    User Request
                         │
                         ▼
                  Intent Router
                         │
             ┌───────────┼───────────┐
             │           │           │
             ▼           ▼           ▼
            KB         Ticket      Direct
             │          Agent       Answer
             ▼           │
        Pinecone          ▼
        Retrieval     Human Approval
             │           │
             ▼           ▼
      Evidence Grader  Create Ticket
             │
        ┌────┴────┐
        │         │
       Good      Bad
        │         │
        ▼         ▼
     Generate   Web Search
     Answer        │
                   ▼
             Web Evidence
                Grader
                   │
              ┌────┴────┐
              │         │
             Good      Bad
              │         │
              ▼         ▼
           Generate   Rewrite Query
           Answer        │
                         ▼
                    Retry Search
                         │
                         ▼
                  Web Evidence
                     Grader
```

---

# 🧠 Core Agentic Workflow

ResolveAI is implemented using **LangGraph** to orchestrate different support workflows.

The agent maintains state throughout execution, allowing the system to:

- Route requests
- Retrieve enterprise knowledge
- Evaluate evidence
- Perform web search
- Rewrite queries
- Retry failed searches
- Generate responses
- Pause for human confirmation
- Create support tickets

### Knowledge Workflow

```text
Question
   │
   ▼
Intent Router
   │
   ▼
Retrieve Enterprise Knowledge
   │
   ▼
Grade Evidence
   │
   ├── Good ──► Generate Grounded Answer
   │
   └── Bad ───► Web Search
                    │
                    ▼
              Grade Web Evidence
                    │
              ┌─────┴─────┐
              │           │
             Good         Bad
              │           │
              ▼           ▼
          Web Answer   Rewrite Query
                            │
                            ▼
                       Retry Search
```

### Ticket Workflow

```text
User Issue
    │
    ▼
Ticket Agent
    │
    ▼
Structured Ticket
    │
    ▼
Human Confirmation
    │
 ┌──┴──┐
 ▼     ▼
Yes    No
 │     │
 ▼     ▼
Create Cancel
Ticket Ticket
```

---

# 📚 Enterprise RAG Pipeline

The internal knowledge workflow uses a retrieval-augmented generation pipeline.

```text
Enterprise PDF
      │
      ▼
   PyPDFLoader
      │
      ▼
Text Extraction
      │
      ▼
Recursive Text Splitting
      │
      ▼
Embedding Generation
      │
      ▼
    Pinecone
      │
      ▼
Vector Retrieval
      │
      ▼
Evidence Grading
      │
      ▼
LLM Generation
      │
      ▼
Grounded Response
```

The system uses:

- **PyPDFLoader** for PDF document loading
- **RecursiveCharacterTextSplitter** for chunking
- **HuggingFace Embeddings** for vector generation
- **Pinecone** for vector storage and similarity search
- **Groq** for LLM inference

---

# 📄 Dynamic Knowledge Ingestion

ResolveAI supports uploading enterprise PDF documents through the **Knowledge Management** interface.

The ingestion pipeline is:

```text
PDF Upload
    │
    ▼
FastAPI
    │
    ▼
PDF Parsing
    │
    ▼
Text Extraction
    │
    ▼
Document Chunking
    │
    ▼
Embedding Generation
    │
    ▼
Pinecone Upsert
    │
    ▼
Knowledge Base Updated
```

Uploaded documents are stored under the corresponding company namespace.

```text
data/
└── uploads/
    └── company_demo/
        └── enterprise_document.pdf
```

Once ingestion is complete, the uploaded document becomes available to the RAG retrieval pipeline.

---

# 🏢 Multi-Tenant Knowledge Isolation

ResolveAI uses company-level Pinecone namespaces to isolate enterprise knowledge.

Each request contains a `company_id`.

```json
{
  "question": "What is the password reset policy?",
  "company_id": "company_demo",
  "thread_id": "thread-123"
}
```

The company ID is used as the Pinecone namespace:

```python
vectorstore = PineconeVectorStore(
    index_name=PINECONE_INDEX,
    namespace=company_id,
    embedding=get_embeddings()
)
```

This creates isolated retrieval boundaries:

```text
Pinecone
│
├── company_demo
│   └── Enterprise Knowledge
│
├── company_a
│   └── Company A Knowledge
│
└── company_b
    └── Company B Knowledge
```

This architecture provides the foundation for supporting multiple organizations using the same platform.

---

# 🔎 Evidence Grading

A key design decision in ResolveAI is that **retrieval does not automatically mean sufficient evidence**.

After retrieving documents from Pinecone, an evidence grader evaluates whether the retrieved context is relevant and sufficient for answering the user's question.

```text
User Question
      │
      ▼
Pinecone Retrieval
      │
      ▼
Retrieved Documents
      │
      ▼
Evidence Grader
      │
 ┌────┴────┐
 ▼         ▼
Good      Bad
 │         │
 ▼         ▼
Generate  Web Search
Answer
```

This adds a verification step between retrieval and generation.

---

# 🌐 Web Intelligence Fallback

Internal enterprise knowledge remains the primary source.

When the internal knowledge base cannot provide sufficient evidence, ResolveAI transitions to the web-search workflow.

```text
Internal Knowledge
        │
        ▼
   Evidence Grader
        │
        ▼
Insufficient Evidence
        │
        ▼
    Web Search
        │
        ▼
 Web Evidence Grader
        │
    ┌───┴────┐
    ▼        ▼
  Good      Bad
    │        │
    ▼        ▼
Generate   Rewrite
Answer     Query
              │
              ▼
          Retry Search
```

The workflow limits retries to avoid uncontrolled search loops.

---

# 🔄 Query Rewriting

When web search does not provide sufficient evidence, ResolveAI can rewrite the search query before retrying.

```text
Original Query
      │
      ▼
  Web Search
      │
      ▼
Insufficient Evidence
      │
      ▼
 Query Rewriting
      │
      ▼
Improved Query
      │
      ▼
  Web Search
```

This gives the agent a recovery mechanism when the original query does not retrieve useful information.

---

# 🎫 Agentic Ticket Automation

Requests that require operational action are routed to the Ticket Agent.

For example:

> "My laptop is not connecting to the company VPN. Please create a support ticket."

The Ticket Agent extracts:

```text
Category
Issue
Description
Priority
```

Example:

```text
Category: Network

Issue:
VPN connectivity problem

Priority:
High

Description:
Employee cannot connect to the corporate VPN.
```

The system then pauses for employee confirmation.

```text
Ticket Agent
     │
     ▼
Structured Ticket
     │
     ▼
Human Confirmation
     │
 ┌───┴────┐
 ▼        ▼
Confirm  Cancel
 │        │
 ▼        ▼
Create   Stop
Ticket   Action
```

---

# 🧑‍💻 Human-in-the-Loop

ResolveAI does not automatically create support tickets without employee approval.

When a ticket needs to be created, LangGraph interrupts the workflow and waits for confirmation.

The frontend displays the generated ticket before execution:

```text
┌──────────────────────────────────────┐
│ Support Ticket Ready                 │
├──────────────────────────────────────┤
│ Category: Network                    │
│ Issue: VPN Connectivity              │
│ Priority: High                       │
│ Description: Unable to connect...    │
├──────────────────────────────────────┤
│        Cancel     Create Ticket      │
└──────────────────────────────────────┘
```

Only after confirmation is the ticket created.

---

# 💬 Conversational Interface

ResolveAI uses a single conversational interface for the employee interaction.

The conversation can contain:

```text
User Question
      ↓
ResolveAI Response
      ↓
User Follow-up
      ↓
ResolveAI Response
      ↓
Ticket Preview
      ↓
Ticket Confirmation
      ↓
Ticket Creation Result
```

Knowledge answers and ticket interactions remain within the same conversation.

A separate Tickets dashboard provides an operational view of previously created tickets.

---


...

## 📸 Results:
<img width="952" height="415" alt="Screenshot 2026-10-08 222239" src="https://github.com/user-attachments/assets/28f7ef01-1fc6-4fa2-8cce-d62913d5bdd2" />

<img width="947" height="410" alt="Screenshot 2026-10-08 202133" src="https://github.com/user-attachments/assets/a59750d4-b0b7-4502-833e-19889454ea13" />

<img width="952" height="415" alt="Screenshot 2026-10-08 222239" src="https://github.com/user-attachments/assets/5aab3dfb-4afc-4cab-9e4c-bbc1d37de5a2" />
<img width="952" height="415" alt="Screenshot 2026-10-08 222239" src="https://github.com/user-attachments/assets/c0c4cb17-c503-4218-a116-a4b26926fff2" />

<img width="952" height="415" alt="Screenshot 2026-10-08 222239" src="https://github.com/user-attachments/assets/abab89bb-8759-44bf-acb5-b3fac0de6cf0" />
<img width="952" height="415" alt="Screenshot 2026-10-08 222239" src="https://github.com/user-attachments/assets/a61870b1-21f4-4e28-97db-3530a50b3255" />
![Uploading Screenshot 2026-10-08 201250.png…]()










# 🗂️ Project Structure

```text
ResolveAI/
│
├── app/
│   ├── core/
│   │   └── config.py
│   │
│   ├── rag/
│   │   ├── embeddings.py
│   │   ├── ingestion.py
│   │   ├── retriever.py
│   │   ├── graders.py
│   │   └── prompts.py
│   │
│   ├── services/
│   │   ├── agent.py
│   │   ├── router.py
│   │   ├── web_search.py
│   │   ├── ticket_agent.py
│   │   └── ticket_service.py
│   │
│   └── main.py
│
├── data/
│   ├── uploads/
│   └── enterprise_documents/
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── tests/
│   └── test_retrieval.py
│
├── scripts/
│   └── ingest.py
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

# ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Agent Orchestration | LangGraph |
| LLM Framework | LangChain |
| LLM | Groq |
| Embeddings | HuggingFace Sentence Transformers |
| Vector Database | Pinecone |
| PDF Processing | PyPDFLoader |
| Text Splitting | RecursiveCharacterTextSplitter |
| Web Intelligence | Tavily |
| Agent Persistence | SQLite |
| Frontend | HTML, CSS, JavaScript |

---

# 🚀 Getting Started

## Prerequisites

- Python 3.10+
- Git
- Pinecone account
- Groq API key
- Tavily API key

---

## 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/ResolveAI.git
cd ResolveAI
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

For PDF upload support:

```bash
pip install python-multipart
```

---

# 🔐 Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
PINECONE_API_KEY=your_pinecone_api_key
TAVILY_API_KEY=your_tavily_api_key
```

Never commit `.env` or API keys to GitHub.

---

# 🗄️ Pinecone Configuration

Create a Pinecone index with:

```text
Index Name: enterprise-support-copilot
Dimension: 384
Metric: cosine
Cloud: AWS
Region: us-east-1
```

The project uses:

```text
sentence-transformers/all-MiniLM-L6-v2
```

for embeddings.

The embedding dimension is `384`.

---

# ▶️ Running the Application

## Start the Backend

```bash
uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

FastAPI Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

## Start the Frontend

Serve the `frontend` directory using VS Code Live Server.

Example:

```text
http://127.0.0.1:5500
```

---

# 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/chat` | Process employee requests |
| `POST` | `/upload-pdf` | Upload enterprise PDF knowledge |
| `POST` | `/ticket/confirm` | Confirm ticket creation |
| `GET` | `/tickets` | Retrieve company tickets |

---

# 🧪 Example Queries

### Enterprise Knowledge

```text
What is the company's password reset policy?
```

```text
How do I connect to the corporate VPN?
```

```text
What should I do if my laptop is lost?
```

### Support Ticket

```text
My laptop is not connecting to WiFi. Please create a support ticket.
```

### General Question

```text
What is the difference between a VPN and a proxy?
```

---

# 🧪 Testing

Run the retrieval test:

```bash
python tests/test_retrieval.py
```

Example:

```text
Company: company_demo
Retrieved 4 documents
```

The retrieval test verifies that the configured company namespace can retrieve the expected enterprise knowledge.

---

# 📊 Current Capabilities

| Capability | Status |
|---|:---:|
| Agentic Routing | ✅ |
| Enterprise RAG | ✅ |
| Pinecone Retrieval | ✅ |
| PDF Ingestion | ✅ |
| PDF Upload | ✅ |
| Multi-Tenant Namespaces | ✅ |
| Evidence Grading | ✅ |
| Web Search Fallback | ✅ |
| Query Rewriting | ✅ |
| AI Ticket Generation | ✅ |
| Human-in-the-Loop | ✅ |
| Ticket Dashboard | ✅ |
| Persistent Agent State | ✅ |
| Conversational Interface | ✅ |

---

# 🔮 Future Improvements

- [ ] Authentication and SSO
- [ ] Role-based access control
- [ ] Document versioning
- [ ] Document deletion and replacement
- [ ] OCR for scanned enterprise documents
- [ ] RAG evaluation with Ragas
- [ ] LangSmith observability
- [ ] Slack / Microsoft Teams integration
- [ ] Email-based ticket creation
- [ ] SLA-aware ticket prioritization
- [ ] Admin analytics
- [ ] Docker deployment
- [ ] CI/CD pipeline
- [ ] Kubernetes deployment
- [ ] Cloud deployment

---

# 🎯 Engineering Principles

ResolveAI is built around five principles:

### 1. Retrieve Before Generating

Use enterprise knowledge whenever the question is company-specific.

### 2. Verify Before Trusting

Retrieved documents are evaluated for relevance before being used for generation.

### 3. Use External Knowledge Carefully

Web intelligence is used as a fallback when internal enterprise knowledge is insufficient.

### 4. Ask Before Acting

Operational actions such as ticket creation require explicit human confirmation.

### 5. Keep Enterprise Data Isolated

Company-specific retrieval is isolated using Pinecone namespaces.

---

# 📌 Key Takeaway

ResolveAI is not designed as another basic "chat with PDF" application.

The project demonstrates how an enterprise AI support system can combine:

```text
RAG
+
Agentic Routing
+
Evidence Grading
+
Query Rewriting
+
Web Intelligence
+
Human-in-the-Loop
+
Tool-Based Actions
+
Multi-Tenant Retrieval
```

into a single enterprise support workflow.

The core design principle is:

> **Retrieve → Verify → Decide → Act → Respond**

---

# 👨‍💻 Author

**Trishna Jaiswar**

2026 AI/Data Science Graduate

**Focus:** AI Engineering · Generative AI · Agentic AI · RAG

GitHub: https://github.com/TrishnaJaiswar

---

# 📄 License

This project is intended for educational, portfolio, and demonstration purposes.
