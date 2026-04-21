// Pré-remplir les champs avec la page courante
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  const tab = tabs[0];
  document.getElementById("url").value = tab.url || "";
  document.getElementById("title").value = tab.title || "";
});

// Charger l'URL du dashboard sauvegardée
chrome.storage.local.get("dashUrl", (data) => {
  if (data.dashUrl) {
    document.getElementById("dashUrl").value = data.dashUrl;
  }
});

function saveSettings() {
  const url = document.getElementById("dashUrl").value.trim();
  chrome.storage.local.set({ dashUrl: url });
  showStatus("URL sauvegardée ✓", "success");
}

async function sendJob() {
  const btn = document.getElementById("sendBtn");
  const status = document.getElementById("status");

  const title = document.getElementById("title").value.trim();
  const url = document.getElementById("url").value.trim();
  const description = document.getElementById("description").value.trim();
  const location = document.getElementById("location").value.trim();

  if (!title || !url) {
    showStatus("Titre et URL requis.", "error");
    return;
  }

  const dashUrl = document.getElementById("dashUrl").value.trim() || "http://192.168.68.103:5000";

  btn.disabled = true;
  btn.textContent = "Envoi…";

  try {
    const formData = new FormData();
    formData.append("title", title);
    formData.append("url", url);
    formData.append("description", description);
    formData.append("location", location);
    formData.append("source", getDomain(url));

    const resp = await fetch(`${dashUrl}/add`, {
      method: "POST",
      body: formData,
    });

    if (resp.ok || resp.redirected) {
      showStatus("✓ Offre ajoutée au dashboard !", "success");
      setTimeout(() => window.close(), 1500);
    } else {
      showStatus("Erreur serveur : " + resp.status, "error");
    }
  } catch (e) {
    showStatus("Impossible de contacter le dashboard. Vérifie que tu es sur le bon réseau.", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Envoyer vers AwaJobs";
  }
}

function getDomain(url) {
  try { return new URL(url).hostname.replace("www.", ""); }
  catch { return "Manuel"; }
}

function showStatus(msg, type) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = type;
}
