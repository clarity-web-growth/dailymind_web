document.addEventListener("DOMContentLoaded", () => {

  /***********************
    CONFIG
  ************************/
  const FREE_LIMIT = 10;

  /***********************
    USER STATE
  ************************/
  let email = localStorage.getItem("email");
  let messageCount = parseInt(localStorage.getItem("messageCount") || "0");
  let isPremium = localStorage.getItem("isPremium") === "true";

  /***********************
    DOM ELEMENTS
  ************************/
  const chatBox = document.getElementById("chat-box");
  const input = document.getElementById("message-input");
  const sendBtn = document.getElementById("send-btn");
  const personalitySelect = document.getElementById("personality");

  /***********************
    SAFETY CHECK
  ************************/
  if (!sendBtn || !input) {
    return;
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

    if (!value || !value.includes("@")) {
      return;
    }

    localStorage.setItem("email", value);
    email = value;

    document.getElementById("emailModal").style.display = "none";

    appendMessage("Saved.", "bot");
  };

  function openPricing() {
    window.location.href = "/pricing";
  }

  window.openPricing = openPricing;

  function lockChat() {
    input.disabled = true;
    sendBtn.disabled = true;

    appendMessage(
      "Session limit reached.",
      "system"
    );

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

    // Email gate
    if (!email) {
      showEmailModal();
      appendMessage("An email is required to proceed.", "bot");
      return;
    }

    // Free limit check
    if (!isPremium && messageCount >= FREE_LIMIT) {
      lockChat();
      return;
    }

    appendMessage(text, "user");
    input.value = "";

    messageCount++;
    localStorage.setItem("messageCount", messageCount);

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
        lockChat();
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

    if (!isPremium && messageCount >= FREE_LIMIT) {
      lockChat();
    }
  });

});

