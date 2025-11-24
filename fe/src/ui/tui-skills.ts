import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import type { SkillState } from "../state";
import { sharedStyles } from "./tui-styles";
import { useGameStore } from "../state";
import "./tui-skill";

@customElement("tui-skills")
export class TuiSkills extends LitElement {
  @state()
  private _skills: SkillState[] = [];

  private _unsubscribe: () => void = () => {};

  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        width: 100%;
        box-sizing: border-box;
      }

      .container {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(27ch, 1fr));
        gap: ch 0ch;
        align-items: start;
        justify-content: start;
      }
    `,
  ];

  connectedCallback() {
    super.connectedCallback();
    this._skills = useGameStore.getState().skills;
    this._unsubscribe = useGameStore.subscribe((state) => {
      this._skills = state.skills;
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._unsubscribe();
  }

  render() {
    return html`
      <div class="container">
        ${this._skills.map(
          (skill) => html`<tui-skill .skill=${skill}></tui-skill>`
        )}
      </div>
    `;
  }
}
