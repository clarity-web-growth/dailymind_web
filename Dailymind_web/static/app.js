const chat = document.getElementById("chat");
const input = document.getElementById("input");

function add(text) {
  chat.textContent += text;
  chat.scrollTop = chat.scrollHeight;
}

async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  input.value = "";
  add("\n\nYou: " + text + "\nDailyMind: ");

  const res = await fetch("/chat-stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      personality: document.getElementById("personality").value,
      device_id: "web-user",
      license_key: ""
    })
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    add(decoder.decode(value));
  }
}
