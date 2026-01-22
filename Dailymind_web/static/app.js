let email = localStorage.getItem("email");
let messageCount = parseInt(localStorage.getItem("messageCount") || "0");

/***********************
  USER STATE
************************/
const FREE_LIMIT = 10;

// Email (free users get a temp one)
let email = localStorage.getItem("email");
if (!email) {
  email = "free_user_" + Date.now();
  localStorage.setItem("email", email);
}

// Message count & premium
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
  UI HELPERS
************************/
function appendMessage(text, className) {
  const div = document.createElement("div");
  div.className = className;
  div.textContent = text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function lockChat() {
  if (input.disabled) return; // prevent double-lock

  input.disabled = true;
  sendBtn.disabled = true;

  appendMessage(
    "🔒 Free limit reached. Upgrade to Premium to continue chatting.",
    "system"
  );

  showUpgradeInline();
}

function showUpgradeInline() {
  const upgradeDiv = document.createElement("div");
  upgradeDiv.className = "upgrade-box";
  upgradeDiv.innerHTML = `
    <button onclick="openPricing()" class="upgrade-btn">
      🚀 Upgrade to Premium
    </button>
  `;
  chatBox.appendChild(upgradeDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function showEmailModal() {
  if (!email) {
    document.getElementById("emailModal").style.display = "flex";
  }
}

function saveEmail() {
  const input = document.getElementById("emailInput").value.trim();
  if (!input || !input.includes("@")) {
    alert("Please enter a valid email");
    return;
  }

  localStorage.setItem("email", input);
  email = input;

  document.getElementById("emailModal").style.display = "none";
}

/***********************
  PAYMENT / UPGRADE
************************/
function openPricing() {
  window.location.href = "/pricing";
}

function goToPayment() {
  window.open(
    "https://paystack.shop/pay/yzthx-tqho",
    "_blank"
  );
}

/***********************
  CHAT HANDLER
************************/
sendBtn.onclick = async () => {
  const text = input.value.trim();
  if (!text) return;

  // ⛔ FREE LIMIT CHECK
  if (!isPremium && messageCount >= FREE_LIMIT) {
    lockChat();
    return;
  }

  appendMessage("You: " + text, "user");
  input.value = "";

 messageCount++;
localStorage.setItem("messageCount", messageCount);

// 👇 SHOW EMAIL POPUP AFTER 2 MESSAGES
if (messageCount === 2 && !email) {
  setTimeout(showEmailModal, 800);
}

  // Send message
  const response = await fetch("/chat-stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      personality: personalitySelect.value,
      email,
      is_free: !isPremium
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  appendMessage("DailyMind: ", "bot");

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    chatBox.lastChild.textContent += decoder.decode(value);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // Lock AFTER response if limit hit
  if (!isPremium && messageCount >= FREE_LIMIT) {
    lockChat();
  }
};

/***********************
  PREMIUM CHECK
************************/
async function checkPremium(email) {
  const res = await fetch("/check-premium", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email })
  });

  const data = await res.json();

  if (data.premium) {
    localStorage.setItem("isPremium", "true");
    localStorage.removeItem("messageCount");
    alert("🎉 Premium unlocked!");
    location.reload();
  } else {
    alert("Payment not confirmed yet. Please try again.");
  }
}

/***********************
  AUTO LOCK ON LOAD
************************/
if (!isPremium && messageCount >= FREE_LIMIT) {
  lockChat();
}

// GLOBAL UPGRADE HANDLER
window.openPricing = function () {
  window.location.href = "/pricing";
};
