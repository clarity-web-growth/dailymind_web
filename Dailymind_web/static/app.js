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

  const response = await fetch("/chat-stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      text: text,
      personality: personalitySelect.value,
      device_id: "WEB",
      license_key: "WEB"
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

