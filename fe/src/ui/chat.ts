//src/ui/chat.ts
import { send } from "../svc/network";

let chatContainer: HTMLElement;

const MAX_MESSAGES = 8;
const RESERVED = ["exp", ""];
const MAX_HISTORY = 50;

const history: string[] = [];
let browsingOffset: number | null = null; // null = not browsing, >=1 = nth newest match
let searchPrefix = "";
let savedCurrentInput = "";

function pushHistory(command: string) {
  // Don't store reserved commands
  if (RESERVED.includes(command.toLowerCase())) return;

  // Avoid consecutive duplicates
  if (history.length > 0 && history[history.length - 1] === command) return;

  history.push(command);
  if (history.length > MAX_HISTORY) {
    history.shift();
  }
}

function resetHistoryBrowsing() {
  browsingOffset = null;
  searchPrefix = "";
  savedCurrentInput = "";
}

function findNthFromEnd(prefix: string, n: number): string | null {
  if (n <= 0) return null;

  let matchCount = 0;
  for (let i = history.length - 1; i >= 0; i--) {
    const cmd = history[i];
    if (!prefix || cmd.startsWith(prefix)) {
      matchCount++;
      if (matchCount === n) return cmd;
    }
  }
  return null;
}

function handleHistoryKey(e: KeyboardEvent, commandInput: HTMLInputElement) {
  if (history.length === 0) return;

  e.preventDefault();

  if (browsingOffset === null) {
    // Entering history-browse mode
    savedCurrentInput = commandInput.value;
    searchPrefix = commandInput.value;
    browsingOffset = 0;
  }

  if (e.key === "ArrowUp") {
    const nextOffset = (browsingOffset ?? 0) + 1;
    const cmd = findNthFromEnd(searchPrefix, nextOffset);
    if (cmd !== null) {
      browsingOffset = nextOffset;
      commandInput.value = cmd;
      // Move cursor to end
      const len = commandInput.value.length;
      commandInput.setSelectionRange(len, len);
    }
    // If no further match, stay on current command
    return;
  }

  if (e.key === "ArrowDown") {
    if (browsingOffset === null) return;

    const nextOffset = (browsingOffset ?? 0) - 1;

    if (nextOffset <= 0) {
      // Back to the user's original input and exit browse mode
      commandInput.value = savedCurrentInput;
      const len = commandInput.value.length;
      commandInput.setSelectionRange(len, len);
      resetHistoryBrowsing();
      return;
    }

    const cmd = findNthFromEnd(searchPrefix, nextOffset);
    if (cmd !== null) {
      browsingOffset = nextOffset;
      commandInput.value = cmd;
      const len = commandInput.value.length;
      commandInput.setSelectionRange(len, len);
    }
    // If no earlier match, stay on current command
  }
}

export function initChat(
  container: HTMLElement,
  commandInput: HTMLInputElement
) {
  chatContainer = container; // Store the container for postLine to use

  commandInput.addEventListener("keydown", (e) => {
    if (e.key === "ArrowUp" || e.key === "ArrowDown") {
      handleHistoryKey(e, commandInput);
      return;
    }

    if (e.key === "Enter" && commandInput.value.trim()) {
      const command = commandInput.value;
      if (!RESERVED.includes(command.toLowerCase())) {
        postLine(command); // Show your own message
        send(command);
        pushHistory(command);
      }
      commandInput.value = "";
      resetHistoryBrowsing();
      return;
    }

    // If the user types while browsing history, reset browse state
    if (
      browsingOffset !== null &&
      (e.key.length === 1 ||
        e.key === "Backspace" ||
        e.key === "Delete" ||
        e.key === "Escape")
    ) {
      resetHistoryBrowsing();
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
