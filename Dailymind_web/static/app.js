// ===============================
// EMAIL HANDLING
// ===============================
let email = localStorage.getItem("email");

if (!email) {
  email = prompt("Enter your email (used for payment):");
  if (email) {
    localStorage.setItem("email", email);
  }
}

// ===============================
// ELEMENTS
// ===============================
const chatBox = document.getElementById("chat-box");
const input = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const personalitySelect = document.getElementById("personality");

// ===============================
// HELPERS
// ===============================
function appendMessage(text, className) {
  const div = document.createElement("div");
  div.className = className;
  div.textContent = text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function showUpgradeBox() {
  const box = document.createElement("div");
  box.className = "upgrade-box";
  box.innerHTML = `
    <strong>Free limit reached 🚫</strong><br/>
    Upgrade to Premium for unlimited conversations.<br/>
    <a href="/upgrade">Upgrade to Premium →</a>
  `;
  chatBox.appendChild(box);
  chatBox.scrollTop = chatBox.scrollHeight;
}

// ===============================
// SEND MESSAGE
// ===============================
sendBtn.onclick = async () => {
  const message = input.value.trim();
  if (!message) return;

  const personality = personalitySelect.value;

  appendMessage("You: " + message, "user");
  input.value = "";

  let response;

  try {
    response = await fetch("/chat-stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: message,
        personality: personality,
        email: email
      })
    });
  } catch (err) {
    appendMessage("Connection error. Try again.", "bot");
    return;
  }

  // 🚫 FREE LIMIT HIT
  if (response.status === 403) {
    showUpgradeBox();
    return;
  }

  // ⚠️ OTHER ERRORS
  if (!response.ok || !response.body) {
    appendMessage("Server error. Please retry.", "bot");
    return;
  }

  // ===============================
  // STREAM RESPONSE
  // ===============================
  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  appendMessage("DailyMind: ", "bot");

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    chatBox.lastChild.textContent += decoder.decode(value);
    chatBox.scrollTop = chatBox.scrollHeight;
  }
};

// ===============================
// PAYMENT HELPERS
// ===============================
async function checkPremium() {
  const res = await fetch("/check-premium", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email })
  });

  const data = await res.json();

  if (data.premium) {
    alert("Premium unlocked 🎉");
    location.reload();
  } else {
    alert("Payment not confirmed yet. Please wait a moment.");
  }
}

function goToPayment() {
  window.open(
    "https://paystack.shop/pay/yzthx-tqho",
    "_blank"
  );
}

}

