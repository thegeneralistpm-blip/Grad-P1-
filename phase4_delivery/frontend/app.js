/*
   app.js
   ==========================================================================
   Frontend Logic for Spotify Review Discovery Engine Dashboard
   Handles Q&A, weekly aggregates, Jira status updates, & channel previews.
   ==========================================================================
*/

document.addEventListener("DOMContentLoaded", () => {
    // UI Elements
    const navItems = document.querySelectorAll(".nav-item");
    const tabPanels = document.querySelectorAll(".tab-panel");
    const tabTitle = document.getElementById("tab-title");
    
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatHistory = document.getElementById("chat-history");
    const btnSaveQuery = document.getElementById("btn-save-query");
    const savedQueriesContainer = document.getElementById("saved-queries");
    
    const jiraList = document.getElementById("jira-list");
    const jiraBadge = document.getElementById("jira-badge");
    
    const slackBlocksView = document.getElementById("slack-blocks-view");
    const emailPreviewIframe = document.getElementById("email-preview-iframe");

    // State Variables
    let currentResponse = null; // Stash latest RAG query result for bookmarking
    let savedQueries = JSON.parse(localStorage.getItem("spotify_saved_queries") || "[]");

    // Initialize UI
    renderSavedQueries();
    loadDashboardData();

    // 1. Sidebar Tab Switching
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const tabId = item.getAttribute("data-tab");
            
            navItems.forEach(n => n.classList.remove("active"));
            item.classList.add("active");
            
            tabPanels.forEach(panel => {
                panel.classList.remove("active");
                if (panel.id === `panel-${tabId}`) {
                    panel.classList.add("active");
                }
            });
            
            // Set navbar title
            tabTitle.textContent = item.querySelector("span").textContent;
        });
    });

    // 2. Chat Search Submission
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const question = chatInput.value.trim();
        if (!question) return;

        // Append User Bubble
        appendMessage(question, "user");
        chatInput.value = "";
        
        // Show Loading Indicator
        const loadingBubble = appendLoadingMessage();
        
        try {
            const response = await fetch("/api/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question })
            });

            if (!response.ok) throw new Error("API Connection Failed");
            const result = await response.json();
            
            // Remove loading indicator
            loadingBubble.remove();

            // Store result for saving/bookmarking
            currentResponse = { question, answer: result.answer, cited_sources: result.cited_sources };
            
            // Append Assistant Response Card
            appendAssistantResponse(result);
            
        } catch (error) {
            loadingBubble.remove();
            appendMessage("Sorry, I encountered an error connecting to the RAG Query Engine. Please ensure the server is running.", "assistant error");
        }
    });

    // Handle suggested question buttons click
    document.addEventListener("click", (e) => {
        if (e.target.classList.contains("suggested-btn")) {
            chatInput.value = e.target.textContent;
            chatForm.dispatchEvent(new Event("submit"));
        }
    });

    // 3. Saved Queries System (LocalStorage)
    btnSaveQuery.addEventListener("click", () => {
        if (!currentResponse) {
            alert("Please submit a search query first to bookmark it!");
            return;
        }

        const queryText = currentResponse.question;
        if (savedQueries.includes(queryText)) {
            alert("This query is already bookmarked!");
            return;
        }

        savedQueries.push(queryText);
        localStorage.setItem("spotify_saved_queries", JSON.stringify(savedQueries));
        renderSavedQueries();
        
        // Visual indicator
        btnSaveQuery.style.color = "var(--spotify-green)";
        setTimeout(() => {
            btnSaveQuery.style.color = "var(--text-secondary)";
        }, 1000);
    });

    function renderSavedQueries() {
        if (savedQueries.length === 0) {
            savedQueriesContainer.innerHTML = '<p class="empty-state">No saved queries yet.</p>';
            return;
        }

        savedQueriesContainer.innerHTML = "";
        savedQueries.forEach((q, idx) => {
            const div = document.createElement("div");
            div.className = "saved-item";
            div.innerHTML = `
                <span>${q}</span>
                <button class="delete-saved" data-idx="${idx}"><i class="fa-solid fa-trash-can"></i></button>
            `;
            
            // Clicking card inputs query
            div.addEventListener("click", (e) => {
                if (e.target.closest(".delete-saved")) return;
                chatInput.value = q;
                chatForm.dispatchEvent(new Event("submit"));
                
                // Switch to chat tab if in another page
                document.querySelector('[data-tab="chat"]').click();
            });

            // Delete query logic
            div.querySelector(".delete-saved").addEventListener("click", (e) => {
                e.stopPropagation();
                savedQueries.splice(idx, 1);
                localStorage.setItem("spotify_saved_queries", JSON.stringify(savedQueries));
                renderSavedQueries();
            });

            savedQueriesContainer.appendChild(div);
        });
    }

    // 4. API Dashboard Loader (Weekly Digest, Slack, Email, Jira)
    async function loadDashboardData() {
        try {
            // Load Weekly Summary Digest
            const digestResp = await fetch("/api/digest");
            if (digestResp.ok) {
                const digest = await digestResp.json();
                renderDigestMetrics(digest);
            }

            // Load Jira Ticket Backlog
            const jiraResp = await fetch("/api/jira-tickets");
            if (jiraResp.ok) {
                const tickets = await jiraResp.json();
                renderJiraTickets(tickets);
            }

            // Load Slack Digest Blocks Preview
            const slackResp = await fetch("/api/slack-preview");
            if (slackResp.ok) {
                const slackPayload = await slackResp.json();
                renderSlackPreview(slackPayload);
            }

            // Load Email HTML Template Preview
            emailPreviewIframe.src = "/api/email-preview";

        } catch (err) {
            console.error("Error fetching dashboard statistics: ", err);
        }
    }

    function renderDigestMetrics(data) {
        document.getElementById("digest-total-count").textContent = data.total_reviews_analyzed || 0;
        document.getElementById("digest-date-range").textContent = data.report_date_range || "Weekly Report";
        
        // Urgency
        const urgencyTheme = data.top_urgency_issue?.theme || "None";
        document.getElementById("digest-urgency-theme").textContent = urgencyTheme;
        document.getElementById("digest-urgency-score").textContent = `Urgency: ${data.top_urgency_issue?.urgency || 0}/5.0`;
        
        // Rising Theme
        const risingTheme = data.top_rising_theme?.theme || "None";
        document.getElementById("digest-rising-theme").textContent = risingTheme;
        document.getElementById("digest-rising-percent").textContent = `▲ ${data.top_rising_theme?.wow_increase_percent || 0}% WoW Growth`;
        
        // Unmet Need
        document.getElementById("digest-unmet-need").textContent = `"${data.new_unmet_need || 'N/A'}"`;

        // Themes Bar chart lists
        const themesContainer = document.getElementById("digest-themes-list");
        themesContainer.innerHTML = "";
        const maxMentions = data.top_themes?.[0]?.count || 1;
        
        data.top_themes?.forEach(t => {
            const percentage = (t.count / maxMentions) * 100;
            const div = document.createElement("div");
            div.className = "theme-metric-row";
            div.innerHTML = `
                <div class="theme-metric-meta">
                    <span class="theme-name">${t.theme}</span>
                    <span class="theme-val">${t.count} mention(s)</span>
                </div>
                <div class="theme-metric-bar-bg">
                    <div class="theme-metric-bar-fill" style="width: ${percentage}%"></div>
                </div>
            `;
            themesContainer.appendChild(div);
        });

        // Competitive Signals
        const competitorContainer = document.getElementById("digest-competitors");
        competitorContainer.innerHTML = "";
        const comps = data.competitive_signals || {};
        
        Object.entries(comps).forEach(([compName, count]) => {
            const div = document.createElement("div");
            div.className = "competitor-row";
            div.innerHTML = `
                <span class="comp-title">${compName.replace('_', ' ').toUpperCase()}</span>
                <span class="comp-count-badge">${count} mention(s)</span>
            `;
            competitorContainer.appendChild(div);
        });
        if (Object.keys(comps).length === 0) {
            competitorContainer.innerHTML = '<p class="empty-state">No competitive signals detected.</p>';
        }

        // Platform breakdowns
        const platformChart = document.getElementById("digest-platforms");
        platformChart.innerHTML = "";
        const platforms = data.platform_breakdown || {};
        const maxPlatVal = Math.max(...Object.values(platforms), 1);
        
        Object.entries(platforms).forEach(([pName, count]) => {
            const pPct = (count / maxPlatVal) * 100;
            const div = document.createElement("div");
            div.className = "share-bar-row";
            div.innerHTML = `
                <span class="share-label">${pName.replace('_', ' ').toUpperCase()}</span>
                <div class="share-bar-bg">
                    <div class="share-bar-fill" style="width: ${pPct}%"></div>
                </div>
                <span class="share-val">${count}</span>
            `;
            platformChart.appendChild(div);
        });
    }

    function renderJiraTickets(tickets) {
        jiraList.innerHTML = "";
        
        // Count drafts
        const activeDrafts = tickets.filter(t => t.status === "DRAFT").length;
        jiraBadge.textContent = activeDrafts;
        jiraBadge.style.display = activeDrafts > 0 ? "block" : "none";

        if (tickets.length === 0) {
            jiraList.innerHTML = `
                <div class="welcome-chat-message">
                    <div class="icon-bubble" style="background-color:rgba(29, 185, 84, 0.05)"><i class="fa-solid fa-clipboard-check"></i></div>
                    <h3>All Backlog Clear!</h3>
                    <p>No high-urgency user complaints are currently pending triage.</p>
                </div>
            `;
            return;
        }

        tickets.forEach(t => {
            const div = document.createElement("div");
            div.className = "jira-ticket-card";
            
            const isSubmitted = t.status === "SUBMITTED";
            const btnText = isSubmitted ? '<i class="fa-solid fa-check"></i> Pushed to Backlog' : '<i class="fa-solid fa-square-arrow-up-right"></i> Approve & Push to Backlog';
            const btnClass = isSubmitted ? "jira-btn submitted" : "jira-btn";
            const disabledAttr = isSubmitted ? "disabled" : "";
            
            div.innerHTML = `
                <div class="jira-card-header">
                    <span class="ticket-id">${t.ticket_id}</span>
                    <span class="ticket-prio-badge priority-${t.priority.toLowerCase()}">${t.priority} Priority</span>
                </div>
                <div class="jira-card-body">
                    <h3>${t.summary}</h3>
                    <p>${t.description}</p>
                    <div class="jira-meta-row">
                        <span><strong>Reporter:</strong> ${t.reporter}</span>
                        <span><strong>Status:</strong> ${t.status}</span>
                    </div>
                </div>
                <div class="jira-card-footer">
                    <button class="${btnClass}" ${disabledAttr} data-id="${t.ticket_id}">${btnText}</button>
                </div>
            `;
            
            // Push Jira action handler
            if (!isSubmitted) {
                div.querySelector(".jira-btn").addEventListener("click", async (e) => {
                    const btn = e.currentTarget;
                    btn.disabled = true;
                    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Pushing...';
                    
                    try {
                        const pushResp = await fetch("/api/jira-tickets/create", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ ticket_id: t.ticket_id })
                        });
                        
                        if (pushResp.ok) {
                            btn.className = "jira-btn submitted";
                            btn.innerHTML = '<i class="fa-solid fa-check"></i> Pushed to Backlog';
                            loadDashboardData(); // Refresh badge count
                        } else {
                            throw new Error();
                        }
                    } catch {
                        btn.disabled = false;
                        btn.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i> Action Failed. Retry?';
                    }
                });
            }

            jiraList.appendChild(div);
        });
    }

    function renderSlackPreview(payload) {
        slackBlocksView.innerHTML = "";
        
        payload.blocks?.forEach(block => {
            const div = document.createElement("div");
            div.className = "slack-block-item";
            
            if (block.type === "header") {
                div.innerHTML = `<h4 class="slack-bold" style="color: #FFFFFF; font-size: 16px; margin-bottom: 6px;">${block.text.text}</h4>`;
            } else if (block.type === "context") {
                div.innerHTML = `<span style="color: #8B8D90; font-size: 13px;">${block.elements[0].text}</span>`;
            } else if (block.type === "section") {
                div.innerHTML = `<p>${block.text.text}</p>`;
            } else if (block.type === "divider") {
                div.className = "slack-divider";
            } else if (block.type === "actions") {
                const btn = block.elements[0];
                div.innerHTML = `<button class="slack-btn-action">${btn.text.text}</button>`;
            }
            
            slackBlocksView.appendChild(div);
        });
    }

    // 5. Chat History Bubbles Render
    function appendMessage(text, type) {
        const div = document.createElement("div");
        div.className = `message-bubble ${type}`;
        
        const avatarIcon = type === "user" ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';
        
        div.innerHTML = `
            <div class="msg-avatar">${avatarIcon}</div>
            <div class="msg-text-card">${text}</div>
        `;
        
        // Remove welcome screen if it exists
        const welcome = chatHistory.querySelector(".welcome-chat-message");
        if (welcome) welcome.remove();
        
        chatHistory.appendChild(div);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        return div;
    }

    function appendLoadingMessage() {
        const div = document.createElement("div");
        div.className = "message-bubble assistant";
        div.innerHTML = `
            <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="msg-text-card"><i class="fa-solid fa-spinner fa-spin"></i> Analyzing vector database user signals...</div>
        `;
        chatHistory.appendChild(div);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        return div;
    }

    function appendAssistantResponse(result) {
        const div = document.createElement("div");
        div.className = "message-bubble assistant";
        
        // Create citations list HTML
        let citationsToggle = "";
        let citationsListHtml = "";
        
        if (result.cited_sources && result.cited_sources.length > 0) {
            citationsToggle = `
                <div class="citations-box">
                    <button class="citations-toggle">
                        <i class="fa-solid fa-circle-info"></i> View ${result.cited_sources.length} Cited Review Sources
                    </button>
                    <div class="citations-list">
            `;
            
            result.cited_sources.forEach(c => {
                const pClass = c.platform?.toLowerCase().replace('_', '-');
                citationsListHtml += `
                    <div class="citation-item-card">
                        <div class="citation-meta">
                            <span class="platform-tag ${pClass}">${c.platform}</span>
                            <span style="color:var(--text-secondary); font-size:11px;">ID: ${c.review_id}</span>
                        </div>
                        <p class="citation-quote">"${c.quote}"</p>
                    </div>
                `;
            });
            
            citationsToggle += citationsListHtml + `</div></div>`;
        }

        // Parse markdown lists to simple bullets
        let formattedText = result.answer
            .replace(/\n/g, "<br>")
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>");

        div.innerHTML = `
            <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="msg-text-card">
                <div>${formattedText}</div>
                ${citationsToggle}
            </div>
        `;

        chatHistory.appendChild(div);
        
        // Citation toggle show/hide logic
        if (result.cited_sources && result.cited_sources.length > 0) {
            const toggleBtn = div.querySelector(".citations-toggle");
            const list = div.querySelector(".citations-list");
            
            toggleBtn.addEventListener("click", () => {
                const isHidden = list.style.display === "none" || !list.style.display;
                list.style.display = isHidden ? "flex" : "none";
                chatHistory.scrollTop = chatHistory.scrollHeight;
            });
        }
        
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
});
