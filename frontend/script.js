const audio = document.querySelector('audio');
const noteList = document.querySelector("noteList");

function takeNotes() {
    const currentTime = audio.currentTime;

    //seconds -> readable format
    const minutes = Math.floor(currentTime / 60);
    const seconds = Math.floor(currentTime % 60);

    const timestamp = "${minutes}:${seconds.toString().padStart(2, '0')}";

    // not real AI response
    const noteText = generateFakeNote();
    
    // note showing
    const li = document.createElement("li");
    li.innerText = `[${timestamp}] ${noteText}`;
    noteList.appendChild(li);
}

function generateFakeNotes() {
    const fakeNotes = [
        "Key idea from the episode",
        "Interesting quote from the speaker",
        "Personal reflection on the topic",
        "Actionable takeaway to implement"
    ];
    return fakeNotes[Math.floor(Math.random() * fakeNotes.length)];
}