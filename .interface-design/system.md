# Interface Design System

## Direction

CRT terminal aesthetic. Dark void, high contrast text that emits light. Linear.app-inspired minimalism. Text floating in space, not contained in cards.

## Feel

- Quiet, focused, ritualistic
- Text writes itself into existence
- Keyboard-first, mouse secondary
- Minimal chrome, maximum content

## Colors

Using existing tokens from `main.css`:

```css
--bg: #1B1E26;              /* the void */
--surface: #1C1F27;         /* subtle elevation */
--on-surface: #ECE6F0;      /* terminal white, primary text */
--primary: #7DD3FC;         /* cyan glow, selection, emphasis */
--danger: #F38BA8;          /* destructive actions */

/* Derived for interfaces */
--dim: #6B7280;             /* muted, unselected, secondary */
--glow: var(--primary);     /* selection highlight */
--pip-empty: #2A2E37;       /* unfilled indicators */
--pip-filled: var(--primary);
```

## Typography

- **Font**: IBM Plex Mono throughout
- **Body/content**: 19px, weight 300
- **Labels**: 14px, weight 400, uppercase, wide tracking
- **Line-height**: tight for density

## Spacing

- Base unit: 8px
- Generous vertical padding to float content
- Consistent gaps using multiples of base

## Depth Strategy

**Borders-only.** No shadows, no cards with visible edges. Surfaces barely differentiate. Separation through spacing and typography hierarchy, not visual containers.

## Selection & Focus

- Background: `rgba(125, 211, 252, 0.15)` — subtle cyan wash
- Border-radius: 4px
- Box-shadow: `0 0 8px rgba(125, 211, 252, 0.3)` — CRT glow effect
- Transition: 150ms ease

## Animation

- Micro-interactions: 150ms
- Type-in effects: 25-35ms per character (randomized for organic feel)
- State changes: 200ms
- Fade out: 300ms opacity, then collapse
- Easing: ease or ease-out, no bounce/spring

## States

Every interactive element needs:
- Default (dim until relevant)
- Focused (cyan glow)
- Active/Selected (brighter, persistent)
- Disabled (further dimmed, no pointer)

## Patterns

### Pip indicators
```
◀  ● ● ○  ▶
```
- Filled: `var(--primary)`
- Empty: `var(--pip-empty)`
- Arrows dim until focused

### Text with selectable spans
- Normal text with inline highlights
- Rounded rect background on selection
- Glow on focus
- Hierarchy expansion (word → clause → sentence)
