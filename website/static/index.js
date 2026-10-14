function deleteNote(noteId) {
  fetch("/delete-note", {
    method: "POST",
    body: JSON.stringify({ noteId: noteId }),
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("The note could not be deleted.");
      }
      window.location.reload();
    })
    .catch((error) => {
      console.error(error);
      window.alert(error.message);
    });
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-note-id]");
  if (button) {
    deleteNote(Number(button.dataset.noteId));
  }
});