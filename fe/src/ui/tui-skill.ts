import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { SkillState } from "../state";
import { sharedStyles, COL_WIDTH } from "./tui-styles";

// Import sub-components
import "./tui-counter";
import "./tui-percentage";
import "./tui-micro-bar";
import "./tui-macro-bar";

@customElement("tui-skill")
export class TuiSkill extends LitElement {
  @property({ type: Object }) skill!: SkillState;

  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        width: 100%;
        box-sizing: border-box;
        padding: 2px 0;
        position: relative;
        font-size: 19px;
        line-height: 1.2;
      }

      /* STRICT GRID LINES */
      .line {
        display: flex;
        flex-direction: row;
        align-items: center;
        height: 1.2em;
        width: 100%;
        overflow: hidden;
      }

      .name-col {
        white-space: pre;
        overflow: hidden;
      }
    `,
  ];

  private renderContent(skill: SkillState) {
    const tnl = Math.max(0, Math.min(1, skill.tnl));
    const nameStr = skill.name.padStart(COL_WIDTH, " ");
    const safeTnl = Math.max(0, Math.min(1, tnl));
    let microPct =
      safeTnl >= 0.999 ? 100.0 : (safeTnl * 5 - Math.floor(safeTnl * 5)) * 100;
    microPct /= 100.0;

    const valRank = skill.rank;
    const padding = "".padStart(COL_WIDTH - 11);
    // prettier-ignore
    return html`
      <div class="line"> <span class="text-layer name-col">${nameStr}</span> <tui-macro-bar .value=${tnl}></tui-macro-bar> </div>
      <div class="line"> <span class="text-layer name-col">${padding}</span>
        <tui-counter style="--tui-monotonic: increase;" .count=${valRank}></tui-counter>
        <tui-percentage style="--tui-monotonic: increase;" .value=${tnl} style=}></tui-percentage>        
        <tui-micro-bar style="--tui-monotonic: increase;" .value=${microPct}></tui-micro-bar>
      </div>
    `;
  }

  render() {
    return html`${this.renderContent(this.skill)}`;
  }
}
