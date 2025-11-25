import { send } from "../svc/network";

let chatContainer: HTMLElement;
const MAX_MESSAGES = 8;
const RESERVED = ["exp", ""];
export function initChat(
  container: HTMLElement,
  commandInput: HTMLInputElement
) {
  chatContainer = container; // Store the container for postLine to use

  commandInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && commandInput.value.trim()) {
      const command = commandInput.value;
      if (!RESERVED.includes(command.toLowerCase())) {
        postLine(command); // Show your own message
        send(command);
      }
      commandInput.value = "";
    }
  });

  commandInput.focus();
}

export function postLine(text: string) {
  if (!chatContainer) return;

  const div = document.createElement("div");
  div.className = "msg";
  div.textContent = text;

  // Add the new message
  chatContainer.appendChild(div);

  // Remove the oldest message if we're over the limit
  while (chatContainer.children.length > MAX_MESSAGES) {
    chatContainer.removeChild(chatContainer.firstChild!);
  }

  // Re-apply the opacity gradient to all current messages
  [...chatContainer.children].reverse().forEach((el, i) => {
    (el as HTMLElement).style.opacity = `${Math.max(0.07, Math.pow(0.55, i))}`;
  });

  // Auto-scroll to the bottom
  chatContainer.scrollTop = chatContainer.scrollHeight;
}
