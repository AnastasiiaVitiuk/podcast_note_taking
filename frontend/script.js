const API = "http://localhost:8000";
let currentEpisodeId = null;

// ── Startup ──────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    checkTranscriptStatus();

    // Update "Take Notes" button label as audio plays
    const player = document.getElementById("player");
    player.addEventListener("timeupdate", () => {
        const btn = document.getElementById("takeNotesBtn");
        btn.textContent = `Take Notes at ${formatTime(player.currentTime)}`;
    });
});

async function checkTranscriptStatus() {
    try {
        const res = await fetch(`${API}/transcript-status`);
        const data = await res.json();
        if (data.has_transcript) {
            currentEpisodeId = data.episode_id;
            setStatus("ready", "Transcript ready");
        } else {
            setStatus("missing", "No transcript yet — click Transcribe");
        }
    } catch {
        setStatus("missing", "Backend not reachable");
    }
}

async function loadSavedNotes(episodeId) {
    try {
        const res = await fetch(`${API}/episodes/${episodeId}/notes`);
        if (!res.ok) return;
        const data = await res.json();

        if (data.full_notes) {
            renderFullNotes(data.full_notes);
        }
        for (const n of data.timestamp_notes) {
            renderTimestampNote(n.timestamp, n.content);
        }
    } catch {
        // silently ignore — notes just won't pre-load
    }
}

// ── Transcription ─────────────────────────────────────────────────────────────

async function transcribeEpisode(event) {
    const button = event.target;
    setBtn(button, "Starting…");
    setStatus("loading", "Starting transcription…");

    let jobId;
    try {
        const res = await fetch(`${API}/transcribe`, { method: "POST" });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        jobId = data.job_id;
    } catch (e) {
        setStatus("missing", "Could not start transcription");
        alert("Transcription failed: " + e.message);
        setBtn(button, "Transcribe Episode");
        return;
    }

    // Poll until done
    setBtn(button, "Transcribing…");
    while (true) {
        await new Promise(r => setTimeout(r, 3000));
        try {
            const res = await fetch(`${API}/transcribe/status/${jobId}`);
            if (!res.ok) break;
            const job = await res.json();

            setStatus("loading", job.message || job.status);

            if (job.status === "done") {
                currentEpisodeId = job.episode_id;
                setStatus("ready", "Transcript saved");
                setBtn(button, "Transcribe Episode");
                return;
            }
            if (job.status === "error") {
                setStatus("missing", "Transcription failed");
                alert("Transcription failed: " + job.message);
                setBtn(button, "Transcribe Episode");
                return;
            }
        } catch {
            break;
        }
    }

    setStatus("missing", "Transcription failed");
    setBtn(button, "Transcribe Episode");
}

async function uploadTranscript(event) {
    const file = event.target.files[0];
    if (!file) return;

    setStatus("loading", "Uploading transcript…");

    try {
        const text = await file.text();
        const segments = JSON.parse(text);

        const res = await fetch(`${API}/upload-transcript`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ segments }),
        });
        if (!res.ok) throw new Error(await res.text());

        const data = await res.json();
        currentEpisodeId = data.episode_id;
        setStatus("ready", "Transcript uploaded and saved");
    } catch (e) {
        setStatus("missing", "Upload failed");
        alert("Upload failed: " + e.message);
    }
}

// ── Note Generation ──────────────────────────────────────────────────────────

async function fullEpisodeNotes(event) {
    if (!currentEpisodeId) {
        showError("fullNotes", "No transcript yet. Please transcribe the episode first.");
        return;
    }

    const button = event.target;
    setBtn(button, "Generating…");
    showLoading("fullNotes", "Generating notes…");

    try {
        const res = await fetch(`${API}/generate-note`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ full_episode: true, episode_id: currentEpisodeId }),
        });
        if (!res.ok) {
            const err = await res.text();
            throw new Error(err);
        }
        const data = await res.json();
        renderFullNotes(data.notes);
    } catch (e) {
        console.error("fullEpisodeNotes error:", e);
        showError("fullNotes", "Error: " + e.message);
    } finally {
        setBtn(button, "Summarize Full Episode");
    }
}

async function takeNotes(event) {
    if (!currentEpisodeId) {
        showError("timestampNotes", "No transcript yet. Please transcribe the episode first.");
        return;
    }

    const button = event.target;
    const player = document.getElementById("player");
    const timestamp = player.currentTime;

    setBtn(button, "Generating…");

    try {
        const res = await fetch(`${API}/generate-note`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ full_episode: false, episode_id: currentEpisodeId, timestamp }),
        });
        if (!res.ok) {
            const err = await res.text();
            throw new Error(err);
        }
        const data = await res.json();
        renderTimestampNote(timestamp, data.notes);
    } catch (e) {
        console.error("takeNotes error:", e);
        showError("timestampNotes", "Error: " + e.message);
    } finally {
        setBtn(button, `Take Notes at ${formatTime(player.currentTime)}`);
    }
}

// ── Rendering ────────────────────────────────────────────────────────────────

function renderFullNotes(markdown) {
    const container = document.getElementById("fullNotes");
    container.innerHTML = markdownToHtml(markdown);
}

function renderTimestampNote(timestamp, markdown) {
    const list = document.getElementById("timestampNotes");
    const li = document.createElement("li");
    li.innerHTML = `<strong>[${formatTime(timestamp)}]</strong><div class="note-body">${markdownToHtml(markdown)}</div>`;
    list.appendChild(li);
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function showLoading(containerId, text) {
    const el = document.getElementById(containerId);
    if (el) el.innerHTML = `<span class="placeholder">${text}</span>`;
}

function showError(containerId, text) {
    const el = document.getElementById(containerId);
    if (el) el.innerHTML = `<span style="color:#dc2626">${escapeHtml(text)}</span>`;
}

function setStatus(type, text) {
    const badge = document.getElementById("transcriptStatus");
    badge.className = `status-badge ${type}`;
    badge.textContent = text;
}

function setBtn(button, text) {
    button.textContent = text;
    button.disabled = text.endsWith("…");
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${String(s).padStart(2, "0")}`;
}

function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function formatInline(text) {
    return text
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>");
}

function markdownToHtml(text) {
    const lines = text.split("\n");
    let html = "";
    let inList = false;

    for (const line of lines) {
        if (line.startsWith("### ")) {
            if (inList) { html += "</ul>"; inList = false; }
            html += `<h4>${formatInline(escapeHtml(line.slice(4)))}</h4>`;
        } else if (line.startsWith("## ")) {
            if (inList) { html += "</ul>"; inList = false; }
            html += `<h3>${formatInline(escapeHtml(line.slice(3)))}</h3>`;
        } else if (line.startsWith("- ") || line.startsWith("* ")) {
            if (!inList) { html += "<ul>"; inList = true; }
            html += `<li>${formatInline(escapeHtml(line.slice(2)))}</li>`;
        } else if (line.trim() === "") {
            if (inList) { html += "</ul>"; inList = false; }
        } else {
            if (inList) { html += "</ul>"; inList = false; }
            html += `<p>${formatInline(escapeHtml(line))}</p>`;
        }
    }

    if (inList) html += "</ul>";
    return html;
}
