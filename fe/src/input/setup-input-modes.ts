// src/input/setup-input-modes.ts
import { createInputModeMachine } from "./input-config";
import type { InputContext, InputEvent } from "./input-modes";

export function setupInputModes(): void {
  const tabs = document.querySelector("tui-tab-selector") as any;
  const cmdInput = document.querySelector<HTMLInputElement>("#cmd");

  if (!tabs || !cmdInput) {
    console.warn("Input mode setup: missing tabs or cmd input", {
      tabs,
      cmdInput,
    });
    return;
  }

  const ctx: InputContext = {
    focusCmdInput() {
      cmdInput.focus();
      const len = cmdInput.value.length;
      try {
        cmdInput.setSelectionRange(len, len);
      } catch {
        // some input types don't support selection; ignore
      }
    },
    setTab(label: string) {
      if (typeof tabs.selectLabel === "function") {
        tabs.selectLabel(label);
      } else {
        tabs.selectedLabel = label;
      }
    },
    onEnterCmd() {},
    onExitCmd() {},
    onEnterExp() {},
    onExitExp() {},
  };

  const machine = createInputModeMachine(ctx);
  const emit = (ev: InputEvent) => machine.handle(ev);

  // ENTER in cmd input → command event; keep focus if we remain in cmd
  cmdInput.addEventListener("keydown", (ev: KeyboardEvent) => {
    if (ev.key === "Enter") {
      const text = cmdInput.value;
      emit({ type: "command", text });

      if (machine.getCurrent() === "cmd") {
        ctx.focusCmdInput();
      }
    }
  });

  // Global typing behavior:
  // - ESC anywhere → back; if we land in cmd, focus cmd
  // - ENTER anywhere *except in #cmd* while not in cmd → switch to cmd
  // - Printable keys outside inputs → only hijack in cmd mode
  window.addEventListener("keydown", (ev: KeyboardEvent) => {
    const target = ev.target as HTMLElement | null;
    const isTypingElement =
      target &&
      (target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable);

    // ESC: always pop the stack; then, if we're now in cmd, focus it
    if (ev.key === "Escape") {
      emit({ type: "key", key: "Escape" });
      if (machine.getCurrent() === "cmd") {
        ctx.focusCmdInput();
      }
      ev.preventDefault();
      return;
    }

    // ENTER: if we're NOT in cmd mode, and this did NOT come from #cmd,
    // snap into cmd and focus input.
    if (ev.key === "Enter") {
      if (target !== cmdInput && machine.getCurrent() !== "cmd") {
        emit({ type: "tab", label: "cmd" });
        ctx.focusCmdInput();
      }
      // allow default so buttons/forms could still work later if needed
      return;
    }

    // If the user is already typing into some other input/textarea, do nothing
    if (isTypingElement) {
      return;
    }

    // Only in cmd mode do we hijack printable keys into the cmd input
    if (
      machine.getCurrent() === "cmd" &&
      ev.key.length === 1 &&
      !ev.metaKey &&
      !ev.ctrlKey &&
      !ev.altKey
    ) {
      ctx.focusCmdInput();
      cmdInput.value += ev.key;
      ev.preventDefault();
    }
  });

  // Label-based tab changes:
  // - always emit tab event
  // - if we end up in cmd, focus cmd (otherwise leave focus as-is)
  tabs.addEventListener(
    "tui-tab-changed",
    (ev: Event | CustomEvent<{ label: string; index: number }>) => {
      const detail = (ev as CustomEvent<{ label: string; index: number }>)
        .detail;
      if (!detail) return;

      emit({ type: "tab", label: detail.label });

      if (machine.getCurrent() === "cmd") {
        ctx.focusCmdInput();
      }
    }
  );

  // Initial focus only if starting in cmd (we do)
  if (machine.getCurrent() === "cmd") {
    ctx.focusCmdInput();
  }
}
