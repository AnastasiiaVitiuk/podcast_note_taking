const audio = document.getElementById('player');
const noteList = document.getElementById('notesList');

async function takeNotes() {
    const timestamp = audio.currentTime;

    const responce = await fetch("http://localhost:8000/generate-note", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            timestamp: timestamp,
        full_episode: false
        })
    });

    const data = await responce.json();
    displayNote(timestamp, data.notes);
}

async function fullNotes() {
    const timestamp = await fetch ("http://localhost:8000/generate-note", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            full_episode: true
        })
    });

    const data = await responce.json();
    displayNote("Full Episode", data.notes);
}

function showNotes(time, text){
    const li = document.createElement("li");
    li.innerText = `[${time}] ${text}`;
    noteList.appendChild(li);
}
