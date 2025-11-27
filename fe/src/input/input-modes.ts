// src/input/input-modes.ts
const MAX_STACK = 50;
export type ModeId = "cmd" | "exp" | "passive";
export type InputEvent =
  | { type: "command"; text: string }
  | { type: "tab"; label: string }
  | { type: "key"; key: string }
  | { type: "external"; name: string; payload?: unknown };

export interface InputContext {
  focusCmdInput(): void;
  setTab(label: string): void;

  onEnterCmd?(): void;
  onExitCmd?(): void;
  onEnterExp?(): void;
  onExitExp?(): void;
  // passive intentionally has no callbacks for now
}

export type TransitionKind = "push" | "back" | "replace";

export type TransitionGuard = (event: InputEvent, ctx: InputContext) => boolean;

export interface Transition {
  kind: TransitionKind;
  to: ModeId;
  when: TransitionGuard;
}

export interface ModeNode {
  id: ModeId;
  enter?(ctx: InputContext, from?: ModeId): void;
  exit?(ctx: InputContext, to?: ModeId): void;
  transitions: Transition[];
}

export class InputModeMachine {
  private nodes: Map<ModeId, ModeNode>;
  private stack: ModeId[] = [];
  private current: ModeId;
  private ctx: InputContext;

  constructor(nodes: ModeNode[], initial: ModeId, ctx: InputContext) {
    this.nodes = new Map(nodes.map((n) => [n.id, n]));
    this.current = initial;
    this.stack.push(initial);
    this.ctx = ctx;

    const node = this.nodes.get(initial);
    if (node && node.enter) {
      node.enter(this.ctx, undefined);
    }
  }

  getCurrent(): ModeId {
    return this.current;
  }

  handle(event: InputEvent): void {
    // Global ESC: pop if possible
    if (event.type === "key" && event.key === "Escape") {
      this.back();
      return;
    }

    // Global tab → mode mapping (label-based)
    if (event.type === "tab") {
      const next = this.mapTabLabelToMode(event.label);
      if (next) {
        this.transitionTo(next, true);
      }
      return;
    }

    const node = this.nodes.get(this.current);
    if (!node) return;

    for (const t of node.transitions) {
      if (!t.when(event, this.ctx)) continue;

      if (t.kind === "back") {
        this.back();
        return;
      }

      if (t.kind === "push") {
        this.transitionTo(t.to, true);
        return;
      }

      if (t.kind === "replace") {
        this.transitionTo(t.to, false);
        return;
      }
    }
  }

  private mapTabLabelToMode(label: string): ModeId | null {
    if (label === "cmd") return "cmd";
    if (label === "exp") return "exp";
    if (label === "inv" || label === "info") return "passive";
    return null;
  }

  private transitionTo(next: ModeId, push: boolean): void {
    if (next === this.current) return;

    const from = this.current;
    const fromNode = this.nodes.get(from);
    const toNode = this.nodes.get(next);
    if (!toNode) return;

    if (fromNode && fromNode.exit) {
      fromNode.exit(this.ctx, next);
    }

    if (push) {
      this.stack.push(next);

      // Clamp oldest frames if too large
      if (this.stack.length > MAX_STACK) {
        // keep the newest MAX_STACK entries
        this.stack = this.stack.slice(this.stack.length - MAX_STACK);
      }
    } else {
      this.stack[this.stack.length - 1] = next;
    }

    this.current = next;

    if (toNode.enter) {
      toNode.enter(this.ctx, from);
    }
  }

  private back(): void {
    if (this.stack.length <= 1) return;

    const from = this.current;
    const fromNode = this.nodes.get(from);

    this.stack.pop();
    const next = this.stack[this.stack.length - 1];
    const toNode = this.nodes.get(next);
    if (!toNode) return;

    if (fromNode && fromNode.exit) {
      fromNode.exit(this.ctx, next);
    }

    this.current = next;

    if (toNode.enter) {
      toNode.enter(this.ctx, from);
    }
  }
}
