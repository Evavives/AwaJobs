// Capture le texte sélectionné et le sauvegarde pour le popup
document.addEventListener("mouseup", () => {
  const selected = window.getSelection().toString().trim();
  if (selected.length > 20) {
    chrome.storage.local.set({ selectedText: selected });
  }
});
