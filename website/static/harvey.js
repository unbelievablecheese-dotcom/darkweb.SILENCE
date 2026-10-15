(() => {
  const toggle = document.getElementById("harvey-toggle");
  const panel = document.getElementById("harvey-panel");
  const closeButton = document.getElementById("harvey-close");
  const messages = document.getElementById("harvey-messages");
  const status = document.getElementById("harvey-status");
  const form = document.getElementById("harvey-form");
  const input = document.getElementById("harvey-input");
  const micButton = document.getElementById("harvey-mic");
  const voiceButton = document.getElementById("harvey-voice");

  if (
    !toggle ||
    !panel ||
    !closeButton ||
    !messages ||
    !status ||
    !form ||
    !input ||
    !micButton ||
    !voiceButton
  ) {
    return;
  }

  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let voiceRepliesEnabled = false;

  function getAssistantVoice() {
    const voices = window.speechSynthesis.getVoices();
    const englishVoices = voices.filter((voice) =>
      voice.lang.toLowerCase().startsWith("en")
    );
    const britishVoice = englishVoices.find((voice) =>
      voice.lang.toLowerCase().startsWith("en-gb")
    );

    return britishVoice || englishVoices[0] || voices[0] || null;
  }

  function setStatus(message) {
    status.textContent = message;
  }

  function appendMessage(message, sender) {
    const element = document.createElement("p");
    element.className = `harvey-message harvey-message-${sender}`;
    element.textContent = message;
    messages.appendChild(element);
    messages.scrollTop = messages.scrollHeight;
  }

  function speak(message) {
    if (!voiceRepliesEnabled || !("speechSynthesis" in window)) {
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(message);
    utterance.lang = "en-GB";
    utterance.rate = 0.95;
    utterance.pitch = 1;
    const assistantVoice = getAssistantVoice();
    if (assistantVoice) {
      utterance.voice = assistantVoice;
      utterance.lang = assistantVoice.lang;
    }
    window.speechSynthesis.speak(utterance);
  }

  function reply(message) {
    appendMessage(message, "assistant");
    setStatus("Ready when you are");
    speak(message);
  }

  async function askGemini(message) {
    setStatus("Thinking…");

    try {
      const response = await fetch("/harvey-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const contentType = response.headers.get("Content-Type") || "";
      if (!contentType.includes("application/json")) {
        throw new Error("I couldn’t read the server response. Please try again.");
      }
      const result = await response.json();

      if (response.status === 401 && result.loginUrl) {
        appendMessage(result.error || "Your session has expired.", "assistant");
        const signInLink = document.createElement("a");
        signInLink.href = result.loginUrl;
        signInLink.className = "harvey-sign-in";
        signInLink.textContent = "Sign in again";
        messages.appendChild(signInLink);
        messages.scrollTop = messages.scrollHeight;
        setStatus("Sign in required");
        return;
      }

      if (!response.ok) {
        throw new Error(result.error || "H.A.R.V.E.Y. could not get a response.");
      }

      reply(result.reply);
    } catch (error) {
      console.error("H.A.R.V.E.Y. chat request failed:", error);
      reply(error.message || "I couldn’t reach the AI service. Please try again.");
    }
  }

  function normalizeCommand(command) {
    return command.trim().replace(/\s+/g, " ").toLowerCase();
  }

  function getNotes() {
    return Array.from(document.querySelectorAll("#notes > li"));
  }

  function readNotes() {
    const notes = getNotes().map((item) => {
      const text = item.cloneNode(true);
      text.querySelectorAll("button").forEach((button) => button.remove());
      return text.textContent.trim();
    });

    if (notes.length === 0) {
      reply("You don’t have any notes on this page yet.");
      return;
    }

    reply(`You have ${notes.length} note${notes.length === 1 ? "" : "s"}: ${notes.join(". ")}`);
  }

  function addNote(noteText) {
    const noteField = document.getElementById("note");
    const noteForm = noteField && noteField.form;
    if (!noteField || !noteForm) {
      reply("Open your notes page and sign in before adding a note.");
      return;
    }

    const value = noteText.trim();
    if (!value) {
      reply("Tell me what you’d like the note to say.");
      return;
    }

    noteField.value = value;
    reply("Adding that note now.");
    noteForm.requestSubmit();
  }

  function deleteNote(noteNumber) {
    const notes = getNotes();
    const index = Number(noteNumber) - 1;
    if (!Number.isInteger(index) || index < 0 || index >= notes.length) {
      reply(`I couldn’t find note ${noteNumber} on this page.`);
      return;
    }

    const deleteButton = notes[index].querySelector("button[data-note-id]");
    if (!deleteButton) {
      reply("I can only delete notes from your signed-in notes page.");
      return;
    }

    if (!window.confirm(`Delete note ${noteNumber}? This cannot be undone.`)) {
      reply("Okay, I left that note unchanged.");
      return;
    }

    deleteButton.click();
    reply(`I sent the request to delete note ${noteNumber}.`);
  }

  async function handleCommand(rawCommand) {
    const command = normalizeCommand(rawCommand);
    if (!command) {
      return;
    }

    appendMessage(rawCommand.trim(), "user");
    input.value = "";

    if (/^(help|what can you do|commands)$/.test(command)) {
      reply(
        "I can navigate this site, read your notes aloud, add a note, or delete a note after confirmation. Try “read my notes,” “add note call the dentist,” or “delete note 2.”"
      );
      return;
    }

    if (/^(hi|hello|hey)( harvey)?[.! ]*$/.test(command)) {
      reply("Hello. What would you like me to do?");
      return;
    }

    if (/^(read|show|list)( my)? notes$/.test(command) || command === "read my notes") {
      readNotes();
      return;
    }

    const addMatch = command.match(/^(?:please )?(?:add|write|save|create)(?: a)? note(?:\s*:\s*|\s+)(.+)$/);
    if (addMatch) {
      addNote(addMatch[1]);
      return;
    }

    const deleteMatch = command.match(/^(?:please )?delete note (\d+)$/);
    if (deleteMatch) {
      deleteNote(deleteMatch[1]);
      return;
    }

    if (/^(go to )?(home|notes|notes page|the notes page)$/.test(command)) {
      window.location.assign("/");
      return;
    }

    if (/^(go to )?login$/.test(command)) {
      window.location.assign("/login");
      return;
    }

    if (/^(go to )?(sign up|signup|registration)$/.test(command)) {
      window.location.assign("/sign-up");
      return;
    }

    if (/^(log out|logout|sign out)$/.test(command)) {
      window.location.assign("/logout");
      return;
    }

    if (/^(what time is it|tell me the time)$/.test(command)) {
      reply(`It is ${new Intl.DateTimeFormat(undefined, { timeStyle: "short" }).format(new Date())}.`);
      return;
    }

    await askGemini(rawCommand.trim());
  }

  toggle.addEventListener("click", () => {
    const isOpening = panel.hidden;
    panel.hidden = !isOpening;
    toggle.setAttribute("aria-expanded", String(isOpening));
    if (isOpening) {
      input.focus();
    }
  });

  closeButton.addEventListener("click", () => {
    panel.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
    toggle.focus();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) {
      panel.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
      toggle.focus();
    }
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const submitButton = form.querySelector('button[type="submit"]');
    input.disabled = true;
    if (submitButton) {
      submitButton.disabled = true;
    }
    handleCommand(input.value).finally(() => {
      input.disabled = false;
      if (submitButton) {
        submitButton.disabled = false;
      }
      input.focus();
    });
  });

  voiceButton.addEventListener("click", () => {
    if (!("speechSynthesis" in window)) {
      reply("Voice replies aren’t supported by this browser.");
      return;
    }

    voiceRepliesEnabled = !voiceRepliesEnabled;
    voiceButton.setAttribute("aria-pressed", String(voiceRepliesEnabled));
    voiceButton.querySelector("span").textContent = voiceRepliesEnabled
      ? "Voice replies on"
      : "Voice replies off";

    if (voiceRepliesEnabled) {
      speak("Voice replies enabled.");
      setStatus("Voice replies enabled");
    } else {
      window.speechSynthesis.cancel();
      setStatus("Voice replies disabled");
    }
  });

  if (!SpeechRecognition) {
    micButton.disabled = true;
    micButton.title = "Speech recognition isn’t supported by this browser.";
  } else {
    recognition = new SpeechRecognition();
    recognition.lang = navigator.language || "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.addEventListener("start", () => {
      setStatus("Listening…");
      micButton.setAttribute("aria-pressed", "true");
    });

    recognition.addEventListener("result", (event) => {
      const transcript = event.results[0][0].transcript;
      input.value = transcript;
      handleCommand(transcript);
    });

    recognition.addEventListener("error", (event) => {
      const messagesByError = {
        "not-allowed": "Microphone access was denied. Allow it in your browser settings to use voice input.",
        "no-speech": "I didn’t hear anything. Try again or type a command.",
        "audio-capture": "No microphone was found. You can type a command instead.",
      };
      setStatus(messagesByError[event.error] || "Voice input stopped. You can type a command.");
    });

    recognition.addEventListener("end", () => {
      micButton.setAttribute("aria-pressed", "false");
      if (status.textContent === "Listening…") {
        setStatus("Ready when you are");
      }
    });

    micButton.addEventListener("click", () => {
      try {
        recognition.start();
      } catch (error) {
        if (error.name !== "InvalidStateError") {
          console.error("Could not start speech recognition:", error);
          setStatus("Couldn’t start voice input. Try typing a command.");
        }
      }
    });
  }
})();
