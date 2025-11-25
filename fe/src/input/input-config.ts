// src/input/input-config.ts
import type { InputContext, InputEvent, ModeNode } from "./input-modes";
import { InputModeMachine } from "./input-modes";

function isCommand(name: string) {
  const target = name.toLowerCase();
  return (ev: InputEvent) =>
    ev.type === "command" && ev.text.trim().toLowerCase() === target;
}

export function createInputModeMachine(ctx: InputContext): InputModeMachine {
  const nodes: ModeNode[] = [
    {
      id: "cmd",
      enter(ctx) {
        ctx.setTab("cmd");
        ctx.focusCmdInput();
        if (ctx.onEnterCmd) ctx.onEnterCmd();
      },
      exit(ctx) {
        if (ctx.onExitCmd) ctx.onExitCmd();
      },
      transitions: [
        // from cmd, "exp" command → exp mode
        {
          kind: "push",
          to: "exp",
          when: isCommand("exp"),
        },
      ],
    },
    {
      id: "exp",
      enter(ctx) {
        // exp is currently the "skills" tab
        ctx.setTab("skills");
        // we *do* still want typing to go into cmd even in exp mode
        ctx.focusCmdInput();
        if (ctx.onEnterExp) ctx.onEnterExp();
      },
      exit(ctx) {
        if (ctx.onExitExp) ctx.onExitExp();
      },
      transitions: [
        // from exp, "cmd" command → cmd mode
        {
          kind: "push",
          to: "cmd",
          when: isCommand("cmd"),
        },
        // allow "exp" again without changing anything (no-op)
        {
          kind: "push",
          to: "exp",
          when: isCommand("exp"),
        },
      ],
    },
    {
      id: "passive",
      // This is the "ignoring" mode for inv/info/etc.
      // We do NOT touch tabs or focus here; the tab click already set the tab.
      enter(_ctx) {
        // intentionally minimal
      },
      exit(_ctx) {
        // intentionally minimal
      },
      transitions: [
        // even from passive, you can type "cmd" or "exp" to jump back
        {
          kind: "push",
          to: "cmd",
          when: isCommand("cmd"),
        },
        {
          kind: "push",
          to: "exp",
          when: isCommand("exp"),
        },
      ],
    },
  ];

  return new InputModeMachine(nodes, "cmd", ctx);
}
