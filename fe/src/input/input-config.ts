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
        ctx.setTab("exp");
        ctx.focusCmdInput();
        if (ctx.onEnterExp) ctx.onEnterExp();
      },
      exit(ctx) {
        if (ctx.onExitExp) ctx.onExitExp();
      },
      transitions: [
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
    {
      id: "passive",
      enter(_ctx) {},
      exit(_ctx) {},
      transitions: [
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
