document.addEventListener("DOMContentLoaded", () => {

  /***********************
    USER STATE
  ************************/
let email = localStorage.getItem("email");
let messageCount = parseInt(localStorage.getItem("messageCount") || "0");
let isPremium = false; // never trust localStorage

async function verifyPremiumStatus() {
  if (!email) return;

  try {
    const res = await fetch("/check-premium", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });

    const data = await res.json();

    if (data.premium) {
      isPremium = true;
      localStorage.setItem("isPremium", "true");
      localStorage.removeItem("messageCount"); // premium = no limit
    } else {
      isPremium = false;
      localStorage.setItem("isPremium", "false");
    }

  } catch (err) {
    console.error("Premium verification failed.");
  }
}

  /***********************
    DOM ELEMENTS
  ************************/
  const chatBox = document.getElementById("chat-box");
  const input = document.getElementById("message-input");
  const sendBtn = document.getElementById("send-btn");
  const personalitySelect = document.getElementById("personality");

  if (!sendBtn || !input) return;

  /***********************
    SYNC PREMIUM WITH SERVER
  ************************/
  if (email) {
    fetch("/check-premium", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    })
      .then(res => res.json())
      .then(data => {
        if (data.premium) {
          localStorage.setItem("isPremium", "true");
          isPremium = true;
        }
      })
      .catch(() => {});
  }

  /***********************
    UI HELPERS
  ************************/
  function appendMessage(text, className) {
    const div = document.createElement("div");
    div.className = className;
    div.textContent = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function showEmailModal() {
    document.getElementById("emailModal").style.display = "flex";
  }

  window.saveEmail = function () {
    const value = document.getElementById("emailInput").value.trim();
    if (!value || !value.includes("@")) return;

    localStorage.setItem("email", value);
    email = value;

    document.getElementById("emailModal").style.display = "none";
    appendMessage("Saved.", "bot");
  };

  function openPricing() {
    window.location.href = "/pricing";
  }

  window.openPricing = openPricing;

  function lockChat(messageText) {
    input.disabled = true;
    sendBtn.disabled = true;

    appendMessage(messageText || "Session limit reached.", "system");

    const upgradeDiv = document.createElement("div");
    upgradeDiv.className = "upgrade-box";
    upgradeDiv.innerHTML = `
      <button class="upgrade-btn" onclick="openPricing()">
        View premium access
      </button>
    `;
    chatBox.appendChild(upgradeDiv);
  }

  /***********************
    CHAT HANDLER
  ************************/
  sendBtn.addEventListener("click", async (e) => {
    e.preventDefault();

    const text = input.value.trim();
    if (!text) return;

    if (!email) {
      showEmailModal();
      appendMessage("An email is required.", "bot");
      return;
    }

    appendMessage(text, "user");
    input.value = "";

    let response;

    try {
      response = await fetch("/chat-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          personality: personalitySelect.value,
          email
        })
      });
    } catch {
      appendMessage("That didn’t load.", "bot");
      return;
    }

    if (!response.ok) {
      if (response.status === 403) {
        lockChat("Session limit reached.");
        return;
      }

      appendMessage("Response unavailable.", "bot");
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    appendMessage("", "bot");

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      chatBox.lastChild.textContent += decoder.decode(value);
      chatBox.scrollTop = chatBox.scrollHeight;
    }
  });

});
