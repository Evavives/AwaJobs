document.getElementById("sendBtn").addEventListener("click", sendJob);
document.getElementById("saveBtn").addEventListener("click", saveSettings);

// Pré-remplir les champs avec la page courante
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  const tab = tabs[0];
  document.getElementById("url").value = tab.url || "";
  document.getElementById("title").value = tab.title || "";
});

// Charger les paramètres sauvegardés + texte sélectionné sur la page
chrome.storage.local.get(["dashUrl", "apiKey", "selectedText"], (data) => {
  if (data.dashUrl) document.getElementById("dashUrl").value = data.dashUrl;
  if (data.apiKey) document.getElementById("apiKey").value = data.apiKey;
  if (data.selectedText) {
    document.getElementById("description").value = data.selectedText;
    // Nettoyer pour la prochaine fois
    chrome.storage.local.remove("selectedText");
  }
});

function saveSettings() {
  const url = document.getElementById("dashUrl").value.trim();
  const key = document.getElementById("apiKey").value.trim();
  chrome.storage.local.set({ dashUrl: url, apiKey: key });
  showStatus("Paramètres sauvegardés ✓", "success");
}

async function sendJob() {
  const btn = document.getElementById("sendBtn");

  const title = document.getElementById("title").value.trim();
  const url = document.getElementById("url").value.trim();
  const description = document.getElementById("description").value.trim();
  const location = document.getElementById("location").value.trim();
  const dashUrl = document.getElementById("dashUrl").value.trim() || "http://192.168.68.103:5000";
  const apiKey = document.getElementById("apiKey").value.trim();

  if (!title || !url) { showStatus("Titre et URL requis.", "error"); return; }
  if (!apiKey) { showStatus("Entre ton mot de passe dashboard dans les paramètres.", "error"); return; }

  btn.disabled = true;
  btn.textContent = "Envoi…";

  try {
    const formData = new FormData();
    formData.append("title", title);
    formData.append("url", url);
    formData.append("description", description);
    formData.append("location", location);
    formData.append("source", getDomain(url));
    formData.append("api_key", apiKey);

    const endpoint = `${dashUrl}/api/clip`;
    let resp;
    try {
      resp = await fetch(endpoint, {
        method: "POST",
        body: formData,
      });
    } catch (networkErr) {
      alert("❌ Erreur réseau : " + networkErr.message + "\n\nEndpoint: " + endpoint);
      showStatus("Erreur réseau — voir alerte", "error");
      btn.disabled = false;
      btn.textContent = "Envoyer vers AwaJobs";
      return;
    }

    let data;
    try {
      data = await resp.json();
    } catch (jsonErr) {
      const text = await resp.text().catch(() => "(impossible de lire la réponse)");
      alert("❌ Réponse HTTP " + resp.status + " (pas du JSON)\n\n" + text.slice(0, 300));
      showStatus("Réponse inattendue (" + resp.status + ")", "error");
      btn.disabled = false;
      btn.textContent = "Envoyer vers AwaJobs";
      return;
    }

    if (data.ok) {
      showStatus("✓ Offre ajoutée au dashboard !", "success");
      setTimeout(() => window.close(), 1500);
    } else {
      alert("❌ Erreur serveur : " + (data.error || JSON.stringify(data)));
      showStatus("Erreur : " + (data.error || resp.status), "error");
    }
  } catch (e) {
    alert("❌ Erreur inattendue : " + e.message);
    showStatus("Erreur inattendue.", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Envoyer vers AwaJobs";
  }
}

function getDomain(url) {
  try { return new URL(url).hostname.replace("www.", ""); }
  catch { return "Extension"; }
}

function showStatus(msg, type) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = type;
}
