import { LitElement, html, css } from "lit";
import { customElement, state, property } from "lit/decorators.js";
import { sharedStyles } from "./tui-styles";
import { useGameStore, type EntityPosition } from "../state";

import "./tui-clock";
import "./tui-entity-title";
import "./tui-health-bar";
import "./tui-label-line";

const PLAYER_ID = 0;
const BAR_WIDTH = 22;

type NearbyHsva = {
  h: number;
  s: number;
  v: number;
  a: number;
};

type EntityMetaFromStore = {
  glyph?: string;
  noun?: string;
  stance?: string;
  healthPct?: number;
  stressPct?: number;
  hsva?: NearbyHsva;
};

type NearbyEntity = EntityPosition & EntityMetaFromStore;

function directionLabel(player: NearbyEntity, ent: NearbyEntity): string {
  const dx = ent.x - player.x;
  const dy = ent.y - player.y;

  if (dx === 0 && dy === 0) return "(here)";

  const vert = dy < 0 ? "north" : dy > 0 ? "south" : "";
  const horiz = dx < 0 ? "west" : dx > 0 ? "east" : "";

  if (vert && horiz) return `(${vert}${horiz})`;
  if (vert) return `(${vert})`;
  if (horiz) return `(${horiz})`;
  return "";
}

@customElement("tui-nearby")
export class TuiNearby extends LitElement {
  @property({ type: Number }) playerId = PLAYER_ID;

  @state() private _entities: NearbyEntity[] = [];

  private _unsubscribe?: () => void;

  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        width: ${BAR_WIDTH}ch;
        font: 300 19px "IBM Plex Mono", monospace;
      }

      .entity-block {
        margin-bottom: 0.1em;
      }

      .entity-block:last-child {
        margin-bottom: 0;
      }

      /* extra vertical space between distinct locations */
      .entity-gap {
        height: 19px;
      }
    `,
  ];

  connectedCallback() {
    super.connectedCallback();
    this._updateFromStore();
    this._unsubscribe = useGameStore.subscribe(() => {
      this._updateFromStore();
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._unsubscribe) {
      this._unsubscribe();
      this._unsubscribe = undefined;
    }
  }

  private _updateFromStore() {
    const { entities, entityMeta } = useGameStore.getState();

    const merged: NearbyEntity[] = [];
    for (const pos of Object.values(entities) as EntityPosition[]) {
      const meta = (entityMeta[pos.id] ?? {}) as EntityMetaFromStore;
      merged.push({
        ...pos,
        glyph: meta.glyph,
        noun: meta.noun,
        stance: meta.stance,
        healthPct: meta.healthPct,
        stressPct: meta.stressPct,
        hsva: meta.hsva,
      });
    }

    this._entities = merged;
  }

  private _orderedOnSameMap(): NearbyEntity[] {
    const player = this._entities.find((e) => e.id === this.playerId);
    if (!player) return [];

    const sameMap = this._entities.filter((e) => e.map_id === player.map_id);
    const playerList = sameMap.filter((e) => e.id === this.playerId);
    const others = sameMap.filter((e) => e.id !== this.playerId);

    others.sort((a, b) => {
      const da =
        (a.x - player.x) * (a.x - player.x) +
        (a.y - player.y) * (a.y - player.y);
      const db =
        (b.x - player.x) * (b.x - player.x) +
        (b.y - player.y) * (b.y - player.y);
      return da - db;
    });

    return [...playerList, ...others];
  }

  private _renderEntityBlock(ent: NearbyEntity, player: NearbyEntity) {
    const isPlayer = ent.id === this.playerId;
    const dir = isPlayer ? "(here)" : directionLabel(player, ent);
    const hsva = ent.hsva ?? { h: 0, s: 0, v: 1, a: 1 };

    const health = ent.healthPct;
    const stress = ent.stressPct;
    const lines = [
      html`<tui-entity-title
        glyph=${ent.glyph ?? "@"}
        name=${ent.noun ?? "unknown"}
        direction=${dir}
        .isPlayer=${isPlayer}
        .h=${hsva.h}
        .s=${hsva.s}
        .v=${hsva.v}
        .a=${hsva.a}
      ></tui-entity-title>`,
    ];

    if (health !== undefined) {
      lines.push(html`<tui-health-bar .value=${health}></tui-health-bar>`);
    }

    if (stress !== undefined) {
      lines.push(html`<tui-stress-bar .value=${stress}></tui-stress-bar>`);
    }

    if (ent.stance) {
      lines.push(html`<tui-label-line text=${ent.stance}></tui-label-line>`);
    }

    // prettier-ignore
    return html`<div class="entity-block">${lines}</div>`;
  }

  render() {
    const player = this._entities.find((e) => e.id === this.playerId);
    if (!player) return html``;

    const ordered = this._orderedOnSameMap();
    if (ordered.length === 0) return html`<tui-clock></tui-clock>`;

    const blocks: unknown[] = [];
    let lastLoc: string | null = null;

    for (const ent of ordered) {
      const locKey = `${ent.x},${ent.y}`;
      if (lastLoc !== null && locKey !== lastLoc) {
        blocks.push(html`<div class="entity-gap"></div>`);
      }
      blocks.push(this._renderEntityBlock(ent, player));
      lastLoc = locKey;
    }

    return html`<tui-clock></tui-clock>${blocks}`;
  }
}
