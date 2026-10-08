const API_BASE_URL = "http://127.0.0.1:8000";
const COMPANY_ID = "company_demo";
let questionInput;
let sendButton;
let chatContainer;
let ticketsView;
let ticketsTableBody;
let refreshTicketsButton;
let ticketCount;
let currentDate;
let navItems;
let actionCards;
let knowledgeView;
let pdfFileInput;
let uploadPdfButton;
let uploadStatus;
let currentThreadId = `thread-${Date.now()}`;

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}

function formatAnswer(value) {
    if (value === undefined || value === null) {
        return "";
    }
    return escapeHtml(String(value))
        .replace(/\n\n/g, "<br><br>")
        .replace(/\n/g, "<br>");
}

function scrollChatToBottom() {
    if (!chatContainer) {
        return;
    }
    requestAnimationFrame(() => {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    });
}

function addUserMessage(message) {
    if (!chatContainer) {
        console.error("chatContainer not found");
        return;
    }
    const element = document.createElement("div");
    element.className = "chat-message user-message";
    element.innerHTML = `
        <div class="message-avatar">U</div>
        <div class="message-content">
            <div class="message-author">You</div>
            <div class="message-bubble">${formatAnswer(message)}</div>
        </div>
    `;
    chatContainer.appendChild(element);
    scrollChatToBottom();
}

function addAssistantMessage(message, source = "direct") {
    if (!chatContainer) {
        console.error("chatContainer not found");
        return;
    }
    const sourceLabels = {
        internal_kb: "Internal Knowledge",
        web: "Web Search",
        direct: "ResolveAI",
        ticket_agent: "Ticket Agent",
        insufficient_evidence: "Evidence Check"
    };
    const sourceLabel = sourceLabels[source] || "ResolveAI";
    const element = document.createElement("div");
    element.className = "chat-message assistant-message";
    element.innerHTML = `
        <div class="message-avatar">R</div>
        <div class="message-content">
            <div class="message-author">ResolveAI</div>
            <div class="message-bubble">${formatAnswer(message)}</div>
            <div class="message-source">${escapeHtml(sourceLabel)}</div>
        </div>
    `;
    chatContainer.appendChild(element);
    scrollChatToBottom();
}

function addLoadingMessage() {
    if (!chatContainer) {
        return;
    }
    removeLoadingMessage();
    const element = document.createElement("div");
    element.id = "loadingMessage";
    element.className = "chat-message assistant-message";
    element.innerHTML = `
        <div class="message-avatar">R</div>
        <div class="message-content">
            <div class="message-author">ResolveAI</div>
            <div class="message-bubble loading-bubble">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    chatContainer.appendChild(element);
    scrollChatToBottom();
}

function removeLoadingMessage() {
    const element = document.getElementById("loadingMessage");
    if (element) {
        element.remove();
    }
}

function addTicketConfirmation(ticket) {
    if (!chatContainer) {
        return;
    }
    const existing = document.getElementById("ticketConfirmationMessage");
    if (existing) {
        existing.remove();
    }
    const element = document.createElement("div");
    element.id = "ticketConfirmationMessage";
    element.className = "chat-message assistant-message";
    element.innerHTML = `
        <div class="message-avatar">R</div>
        <div class="message-content">
            <div class="message-author">ResolveAI</div>
            <div class="message-bubble ticket-message">
                <strong>Support ticket ready</strong>
                <p>I prepared the following ticket. Please confirm before creating it.</p>
                <div class="ticket-chat-card">
                    <div class="ticket-chat-field">
                        <span>Category</span>
                        <strong>${escapeHtml(ticket?.category)}</strong>
                    </div>
                    <div class="ticket-chat-field">
                        <span>Issue</span>
                        <strong>${escapeHtml(ticket?.issue)}</strong>
                    </div>
                    <div class="ticket-chat-field">
                        <span>Priority</span>
                        <strong>${escapeHtml(ticket?.priority)}</strong>
                    </div>
                    <div class="ticket-chat-field ticket-chat-description">
                        <span>Description</span>
                        <strong>${escapeHtml(ticket?.description)}</strong>
                    </div>
                </div>
                <div class="chat-ticket-actions">
                    <button id="chatTicketCancel" class="ticket-chat-cancel" type="button">Cancel</button>
                    <button id="chatTicketConfirm" class="ticket-chat-confirm" type="button">Create Ticket</button>
                </div>
            </div>
        </div>
    `;
    chatContainer.appendChild(element);
    document.getElementById("chatTicketCancel")?.addEventListener("click", cancelTicket);
    document.getElementById("chatTicketConfirm")?.addEventListener("click", confirmTicket);
    scrollChatToBottom();
}

function cancelTicket() {
    const confirmation = document.getElementById("ticketConfirmationMessage");
    if (confirmation) {
        confirmation.remove();
    }
    addAssistantMessage("Okay. The support ticket was not created.", "ticket_agent");
}

async function sendQuestion() {
    const question = questionInput.value.trim();
    if (!question) {
        return;
    }
    if (sendButton.disabled) {
        return;
    }
    addUserMessage(question);
    questionInput.value = "";
    questionInput.style.height = "auto";
    sendButton.disabled = true;
    sendButton.innerHTML = `<span>Processing...</span><span class="send-icon">◌</span>`;
    addLoadingMessage();
    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                question: question,
                company_id: COMPANY_ID,
                thread_id: currentThreadId
            })
        });
        const rawText = await response.text();
        console.log("ResolveAI backend response:", rawText);
        if (!response.ok) {
            throw new Error(`Backend error ${response.status}: ${rawText}`);
        }
        let result;
        try {
            result = JSON.parse(rawText);
        } catch (error) {
            throw new Error("Backend returned invalid JSON.");
        }
        removeLoadingMessage();
        console.log("ResolveAI parsed result:", result);
        if (result.status === "awaiting_confirmation" || result.confirmation_required === true) {
            addTicketConfirmation(result.ticket);
            return;
        }
        if (result.answer !== undefined && result.answer !== null && String(result.answer).trim() !== "") {
            addAssistantMessage(result.answer, result.source || "direct");
        } else {
            addAssistantMessage("The support agent did not return an answer.", "direct");
        }
        if (result.ticket_id) {
            await loadTickets();
        }
    } catch (error) {
        console.error("ResolveAI error:", error);
        removeLoadingMessage();
        addAssistantMessage("I could not process your request. Please check that the ResolveAI backend is running.", "direct");
    } finally {
        sendButton.disabled = false;
        sendButton.innerHTML = `<span>Ask ResolveAI</span><span class="send-icon">↗</span>`;
        questionInput.focus();
        scrollChatToBottom();
    }
}

async function confirmTicket() {
    const confirmButton = document.getElementById("chatTicketConfirm");
    const cancelButton = document.getElementById("chatTicketCancel");
    if (confirmButton) {
        confirmButton.disabled = true;
        confirmButton.textContent = "Creating...";
    }
    if (cancelButton) {
        cancelButton.disabled = true;
    }
    try {
        const response = await fetch(`${API_BASE_URL}/ticket/confirm`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                thread_id: currentThreadId,
                confirmation: "yes"
            })
        });
        const rawText = await response.text();
        if (!response.ok) {
            throw new Error(`Ticket confirmation failed: ${rawText}`);
        }
        const result = JSON.parse(rawText);
        const confirmation = document.getElementById("ticketConfirmationMessage");
        if (confirmation) {
            confirmation.remove();
        }
        if (result.answer) {
            addAssistantMessage(result.answer, result.source || "ticket_agent");
        }
        await loadTickets();
    } catch (error) {
        console.error("Ticket confirmation error:", error);
        if (confirmButton) {
            confirmButton.disabled = false;
            confirmButton.textContent = "Create Ticket";
        }
        if (cancelButton) {
            cancelButton.disabled = false;
        }
        addAssistantMessage("I could not create the ticket. Please try again.", "ticket_agent");
    }
}
async function uploadPdf() {
    const file = pdfFileInput?.files?.[0];
    const selectedFileName = document.getElementById("selectedFileName");
    if (!file) {
        uploadStatus.textContent = "Please select a PDF file.";
        return;
    }
    if (!file.name.toLowerCase().endsWith(".pdf")) {
        uploadStatus.textContent = "Only PDF files are supported.";
        return;
    }
    const formData = new FormData();
    formData.append("file", file);
    formData.append("company_id", COMPANY_ID);
    uploadPdfButton.disabled = true;
    uploadPdfButton.textContent = "Uploading...";
    uploadStatus.textContent = "Processing PDF and adding it to the knowledge base...";
    try {
        const response = await fetch(`${API_BASE_URL}/upload-pdf`, {
            method: "POST",
            body: formData
        });
        const rawText = await response.text();
        console.log("PDF upload response:", rawText);
        let result;
        try {
            result = JSON.parse(rawText);
        } catch (error) {
            throw new Error("Backend returned invalid JSON.");
        }
        if (!response.ok) {
            throw new Error(result.detail || "PDF upload failed.");
        }
        uploadStatus.textContent = `Uploaded successfully: ${result.filename} (${result.chunks} chunks added).`;
        pdfFileInput.value = "";
        if (selectedFileName) {
            selectedFileName.textContent = "No file selected";
        }
    } catch (error) {
        console.error("PDF upload error:", error);
        uploadStatus.textContent = `Upload failed: ${error.message}`;
    } finally {
        uploadPdfButton.disabled = false;
        uploadPdfButton.textContent = "Upload PDF";
    }
}

function setupInput() {
    sendButton.addEventListener("click", sendQuestion);
    questionInput.addEventListener("keydown", event => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendQuestion();
        }
    });
    questionInput.addEventListener("input", () => {
        questionInput.style.height = "auto";
        questionInput.style.height = `${Math.min(questionInput.scrollHeight, 180)}px`;
    });
}

function formatTicketDate(dateString) {
    if (!dateString) {
        return "-";
    }
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) {
        return "-";
    }
    return date.toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit"
    });
}

function renderTickets(tickets) {
    if (!ticketsTableBody) {
        return;
    }
    if (!tickets.length) {
        ticketsTableBody.innerHTML = `
            <div class="tickets-empty">
                <strong>No support tickets yet</strong>
                <span>Create a ticket through ResolveAI and it will appear here.</span>
            </div>
        `;
        return;
    }
    ticketsTableBody.innerHTML = tickets.map(ticket => `
        <div class="tickets-row">
            <span class="ticket-id">${escapeHtml(ticket.ticket_id)}</span>
            <div class="ticket-issue">
                <strong>${escapeHtml(ticket.issue)}</strong>
                <small>${escapeHtml(ticket.description)}</small>
            </div>
            <span>${escapeHtml(ticket.category)}</span>
            <span class="priority-badge ${String(ticket.priority || "").toLowerCase()}">${escapeHtml(ticket.priority)}</span>
            <span class="status-badge ${String(ticket.status || "").toLowerCase()}">${escapeHtml(ticket.status)}</span>
            <span class="ticket-date">${formatTicketDate(ticket.created_at)}</span>
        </div>
    `).join("");
}

async function loadTickets() {
    try {
        const response = await fetch(
            `${API_BASE_URL}/tickets?company_id=${encodeURIComponent(COMPANY_ID)}`
        );
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }
        const result = await response.json();
        const tickets = result.tickets || [];
        if (ticketCount) {
            ticketCount.textContent = tickets.length;
        }
        renderTickets(tickets);
    } catch (error) {
        console.error("Failed to load tickets:", error);
    }
}

function setupNavigation() {
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            navItems.forEach(nav => nav.classList.remove("active"));
            item.classList.add("active");
            const view = item.dataset.view;
            if (view === "tickets") {
                ticketsView.classList.remove("hidden");
                if (knowledgeView) {
                    knowledgeView.classList.add("hidden");
                }
                loadTickets();
                ticketsView.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });
            } else if (view === "knowledge") {
                ticketsView.classList.add("hidden");
                if (knowledgeView) {
                    knowledgeView.classList.remove("hidden");
                    knowledgeView.scrollIntoView({
                        behavior: "smooth",
                        block: "start"
                    });
                }
            } else {
                ticketsView.classList.add("hidden");
                if (knowledgeView) {
                    knowledgeView.classList.add("hidden");
                }
            }
        });
    });
}

function setupQuickActions() {
    const prompts = {
        password: "What is the company's password reset policy?",
        network: "I am having a network or VPN connectivity problem. How can I troubleshoot it?",
        ticket: "My laptop is not working. Please create an IT support ticket."
    };
    actionCards.forEach(card => {
        card.addEventListener("click", () => {
            const action = card.dataset.action;
            const prompt = card.dataset.prompt || prompts[action];
            if (!prompt) {
                return;
            }
            questionInput.value = prompt;
            questionInput.style.height = "auto";
            questionInput.style.height = `${Math.min(questionInput.scrollHeight, 180)}px`;
            questionInput.focus();
        });
    });
}

function initialize() {
    questionInput = document.getElementById("questionInput");
    sendButton = document.getElementById("sendButton");
    chatContainer = document.getElementById("chatContainer");
    ticketsView = document.getElementById("ticketsView");
    ticketsTableBody = document.getElementById("ticketsTableBody");
    refreshTicketsButton = document.getElementById("refreshTicketsButton");
    ticketCount = document.getElementById("ticketCount");
    currentDate = document.getElementById("currentDate");
    navItems = document.querySelectorAll(".nav-item");
    actionCards = document.querySelectorAll(".action-card");
    knowledgeView = document.getElementById("knowledgeView");
    pdfFileInput = document.getElementById("pdfFileInput");
    uploadPdfButton = document.getElementById("uploadPdfButton");
    uploadStatus = document.getElementById("uploadStatus");

    if (currentDate) {
        currentDate.textContent = new Date().toLocaleDateString(
            "en-IN",
            {
                day: "2-digit",
                month: "short",
                year: "numeric"
            }
        ).toUpperCase();
    }

    setupInput();
    setupNavigation();
    setupQuickActions();

    if (uploadPdfButton) {
        uploadPdfButton.addEventListener("click", uploadPdf);
    }

    if (refreshTicketsButton) {
        refreshTicketsButton.addEventListener("click", loadTickets);
    }

    loadTickets();

    console.log("ResolveAI initialized successfully.");
    console.log("Chat container:", chatContainer);
    console.log("PDF upload:", uploadPdfButton);
}

document.addEventListener("DOMContentLoaded", initialize);