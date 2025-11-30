// src/ui/tui-nearby.ts
import { LitElement, html, css } from "lit";
import { customElement, state, property } from "lit/decorators.js";
import { sharedStyles } from "./tui-styles";
import { useGameStore, type EntityPosition, type EntityMeta } from "../state";
import { cardinalFromDelta } from "../util/util";
import { getTile, type EntityLookupFn, type TileSample } from "./map";
import "./tui-clock";
import "./tui-entity-title";
import "./tui-health-bar";
import "./tui-label-line";

const PLAYER_ID = 0;
const BAR_WIDTH = 22;

type EntityMetaFromStore = EntityMeta & {
  healthPct?: number;
  stressPct?: number;
};

type NearbyEntity = EntityPosition & EntityMetaFromStore;

function directionLabel(player: NearbyEntity, ent: NearbyEntity): string {
  return cardinalFromDelta(ent.x - player.x, ent.y - player.y);
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
        ...meta,
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

  private _renderEntityBlock(
    ent: NearbyEntity,
    player: NearbyEntity,
    tileSample?: TileSample
  ) {
    const isPlayer = ent.id === this.playerId;
    const dir = directionLabel(player, ent);

    // Glyph: prefer what the map would draw at this tile
    const glyph = tileSample?.glyph ?? ent.glyph ?? "@";

    // Color:
    // - Prefer tileSample.color from getTile (same as map)
    // - Fall back to per-entity h/s/v from store
    const color = tileSample?.color;
    const hNorm = color?.h ?? (typeof ent.h === "number" ? ent.h : 0); // normalized [0,1]
    const s = color?.s ?? (typeof ent.s === "number" ? ent.s : 0);
    const v = color?.v ?? (typeof ent.v === "number" ? ent.v : 1);

    // Convert normalized hue in [0,1] to degrees for hsvaToRgba
    const hDeg = hNorm * 360;
    const a = 1;

    const health = ent.healthPct;
    const stress = ent.stressPct;

    const lines = [
      html`<tui-entity-title
        glyph=${glyph}
        name=${ent.noun ?? "unknown"}
        direction=${dir}
        .isPlayer=${isPlayer}
        .h=${hDeg}
        .s=${s}
        .v=${v}
        .a=${a}
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

    // Get tile lookup (same as map.ts uses)
    const state = useGameStore.getState();
    const lookupFactory = (state as any).entityLookup as
      | (() => EntityLookupFn)
      | undefined;
    const lookupFn: EntityLookupFn | undefined = lookupFactory
      ? lookupFactory()
      : undefined;

    const blocks: unknown[] = [];
    let lastLoc: string | null = null;

    for (const ent of ordered) {
      const locKey = `${ent.x},${ent.y}`;

      let tileSample: TileSample | undefined;

      if (lookupFn) {
        try {
          // Ask who "wins" this tile, per the map renderer.
          const winner = lookupFn(ent.map_id, ent.x, ent.y);

          if (winner && winner.position.id === ent.id) {
            // This entity is the winner → use the same glyph/color as the map
            tileSample = getTile(ent.map_id, ent.x, ent.y, lookupFn);
          } else {
            // Not the winner → leave tileSample undefined so we fall back
            // to the entity's own glyph/color.
            tileSample = undefined;
          }
        } catch (err) {
          // Don't kill HUD if anything misbehaves
          console.error(
            "tui-nearby: lookup/getTile failed for entity",
            ent.id,
            err
          );
        }
      }

      if (lastLoc !== null && locKey !== lastLoc) {
        blocks.push(html`<div class="entity-gap"></div>`);
      }
      blocks.push(this._renderEntityBlock(ent, player, tileSample));
      lastLoc = locKey;
    }

    return html`<tui-clock></tui-clock>${blocks}`;
  }
}
