//src/ui/tui-styles.ts
import { css } from "lit";

export const COL_WIDTH = 15;
export const sharedStyles = css`
  :host {
    /* --- THEME --- */
    --c-bg: #050505;
    --c-high: #e0e0e0;
    --c-mid: #9e9e9e;
    --c-low: #555555;
    --c-void: #333333;
    --c-ember: #db5800;
    --c-flash: #fff5e6;
    font-family: "IBM Plex Mono", monospace;
  }
  .text-layer {
    color: var(--c-mid);
  }
  .dim {
    color: var(--c-low);
  }
`;
