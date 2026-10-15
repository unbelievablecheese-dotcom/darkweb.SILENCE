(() => {
  const toggle = document.getElementById("silence-radio-toggle");
  const closeButton = document.getElementById("silence-radio-close");
  const panel = document.getElementById("silence-radio-panel");
  const frame = document.getElementById("silence-radio-frame");
  const state = toggle?.querySelector(".radio-toggle-state");
  const videoId = "NcauOz6DCeg";

  if (!toggle || !closeButton || !panel || !frame || !state) return;

  function stopPlayback() {
    panel.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
    state.textContent = "PLAY";
    frame.replaceChildren();
    toggle.focus();
  }

  toggle.addEventListener("click", () => {
    if (toggle.getAttribute("aria-expanded") === "true") {
      stopPlayback();
      return;
    }

    panel.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
    state.textContent = "STOP";

    const player = document.createElement("iframe");
    player.src = `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&loop=1&playlist=${videoId}&controls=1&playsinline=1&rel=0`;
    player.title = "SILENCE music on YouTube";
    player.allow = "autoplay; encrypted-media; picture-in-picture";
    player.referrerPolicy = "strict-origin-when-cross-origin";
    player.allowFullscreen = true;
    frame.replaceChildren(player);
  });

  closeButton.addEventListener("click", stopPlayback);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) stopPlayback();
  });
})();
