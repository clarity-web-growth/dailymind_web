let email = localStorage.getItem("email");

if (!email) {
  email = prompt("Enter your email used for payment:");
  localStorage.setItem("email", email);
}

async function checkPremium(email) {
  const res = await fetch("/check-premium", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email })
  });

  const data = await res.json();

  if (data.premium) {
    localStorage.setItem("email", email);
    alert("Premium unlocked 🎉");
    location.reload();
  } else {
    alert("Payment not confirmed yet. Try again in 10 seconds.");
  }
}

const chatBox = document.getElementById("chat-box");
const input = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const personalitySelect = document.getElementById("personality");

function appendMessage(text, className) {
  const div = document.createElement("div");
  div.className = className;
  div.textContent = text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

sendBtn.onclick = async () => {
  const text = input.value.trim();
  if (!text) return;

  appendMessage("You: " + text, "user");
  input.value = "";

  fetch("/chat-stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    text: message,
    personality: personality,
    email: email
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
};

function goToPayment() {
  window.open(
    "https://paystack.shop/pay/yzthx-tqho",
    "_blank"
  );
}

