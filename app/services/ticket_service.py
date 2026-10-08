import sqlite3
import uuid
from datetime import datetime
from app.core.config import SQLITE_DB

def init_ticket_db():
    connection = sqlite3.connect(SQLITE_DB)
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL,
            category TEXT NOT NULL,
            issue TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    connection.commit()
    connection.close()

def create_ticket(ticket_details, company_id):
    init_ticket_db()
    ticket_id = "INC-" + str(uuid.uuid4())[:8].upper()
    created_at = datetime.now().isoformat()
    ticket = {
        "ticket_id": ticket_id,
        "company_id": company_id,
        "category": ticket_details["category"],
        "issue": ticket_details["issue"],
        "description": ticket_details["description"],
        "priority": ticket_details["priority"],
        "status": "Open",
        "created_at": created_at
    }
    connection = sqlite3.connect(SQLITE_DB)
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO tickets (
            ticket_id,
            company_id,
            category,
            issue,
            description,
            priority,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ticket["ticket_id"],
            ticket["company_id"],
            ticket["category"],
            ticket["issue"],
            ticket["description"],
            ticket["priority"],
            ticket["status"],
            ticket["created_at"]
        )
    )
    connection.commit()
    connection.close()
    return ticket

def get_tickets(company_id):
    init_ticket_db()
    connection = sqlite3.connect(SQLITE_DB)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT
            ticket_id,
            category,
            issue,
            description,
            priority,
            status,
            created_at
        FROM tickets
        WHERE company_id = ?
        ORDER BY created_at DESC
        """,
        (company_id,)
    )
    tickets = [dict(row) for row in cursor.fetchall()]
    connection.close()
    return tickets