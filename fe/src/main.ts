import "./main.css";
import { initializeNetwork } from "./svc/network";
import { initMap } from "./ui/map";
import { initChat } from "./ui/chat";
import { setupInputModes } from "./input/setup-input-modes";

import "./ui/tui-nearby";
import "./ui/tui-prompt";
import "./ui/tui-skills";
import "./ui/tui-stress-bar";
import "./ui/tui-tab-selector";

function startApp() {
  function getElement<T extends HTMLElement>(
    id: string,
    type: { new (): T }
  ): T {
    const element = document.getElementById(id);
    if (!element) throw new Error(`Fatal Error: Element #${id} not found.`);
    if (!(element instanceof type))
      throw new Error(`Fatal: #${id} is not a ${type.name}.`);
    return element as T;
  }

  try {
    initializeNetwork();

    const mapElement = getElement("mapBox", HTMLElement);
    const chatElement = getElement("chat", HTMLElement);
    const inputElement = getElement("cmd", HTMLInputElement);

    initMap(mapElement);
    initChat(chatElement, inputElement);
  } catch (error) {
    console.error(error);
  }
}

window.addEventListener("DOMContentLoaded", () => {
  setupInputModes();
  startApp();
});
