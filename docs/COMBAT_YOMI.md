# Combat & Yomi System

## Core Loop

Two verbs: `attack` and `block`. Simple surface, recursive depth.

## Timing Windows

```
attack windup:     3.0 seconds (visible to all)
block active:      1.2 seconds (instant activation)
block recovery:    2.5 seconds (if you whiff)
stun (block proc): 5.0 seconds
```

## The Mechanics

### Attack
```python
# commands.py:140-176
attack <target>
```
- Visible windup: `"{0} draws back their fist..."`
- 3-second delay before resolution
- **Can be cancelled** (`requires_not_busy = False`)
- Cancelling emits `bus.Interrupt`, removes pending action

### Block
```python
# commands.py:196-221
block
```
- **Instant activation** - adds `Defending` component immediately
- Lasts 1.2 seconds, then auto-removes
- **Also emits Interrupt** - cancels your own pending attack
- If nothing hits you: "You block the air!" + 2.5s recovery lag

### Resolution (combat.py:107-147)

**If target is Defending:**
- Attack is blocked
- Attacker gains 1-2 stress
- 10% chance (PPM-adjusted): defender procs → **stuns attacker for 5s**

**If target is not Defending:**
- Damage = `skill_mult * pain_mult * 10.0`
- DoubleDamage component doubles this
- Target gains 3-4 stress + aggravated stress
- 10% chance: attacker procs → **DoubleDamage on next hit**

## Yomi Layers

### Layer 0: No Read
I attack. You stand there. I hit.

### Layer 1: Basic Read
I attack. You see the windup. You block. I miss.

### Layer 2: Counter-Read
I attack. You start to block. I see you blocking, cancel my attack into my own block. We both whiff.

Or: I attack. You block. I cancel, then immediately attack again while your block expires. I hit during your recovery window.

### Layer 3: Meta-Read
I attack. You know I like to cancel. You don't block, you wait. I commit. You block late. I miss.

Or: I attack expecting you to wait. You block early expecting me to commit. Whoever reads right wins.

### Layer 4+: Conditioning
Over multiple exchanges, I establish patterns. "This player always blocks on the third attack." Then I exploit the pattern. Then you exploit my exploitation.

## Tempo

Tempo is who has initiative.

**Winning tempo:**
- Landing a hit (they're in pain)
- Block proc (they're stunned 5s)
- Making them whiff (they're in 2.5s recovery)

**Losing tempo:**
- Getting hit
- Getting stunned
- Blocking air

The fight is a series of tempo exchanges. The player with tempo can press; the player without must find a way to reset or steal it back.

## Skill Differential (util.py:296-347)

The `contest()` function creates asymmetric risk:

```python
skill_mult = contest(attack.rank, defend.rank)
damage = skill_mult * pain_mult * 10.0
```

Higher martial arts rank = more damage per hit.
Higher evasion rank = reduced incoming damage (via contest inversion).

This means:
- Skilled fighters can take more risks (each hit matters more)
- Unskilled fighters need better reads to compete
- Upsets are possible but costly

## Proc System (util.py:176-198)

Procs use PPM (procs per minute) math, not flat chance:

```python
λ = odds / interval
return RNG.random() < 1 - math.exp(-λ * δ)
```

This means: the longer since your last proc, the higher your chance. Rewards sustained fighting, not hit-and-run.

## What Creates Depth

1. **Visible windups** - information asymmetry without hidden inputs
2. **Cancellable commits** - the read isn't just "will they attack" but "will they commit"
3. **Asymmetric recovery** - block whiff costs more than attack cancel
4. **Procs as momentum** - DoubleDamage rewards aggression, stun punishes predictability
5. **Skill as modifier** - reads matter more than stats, but stats amplify reads

## Expansion Vectors

### More Verbs
- **Feint**: Fake windup, baits block, faster recovery than real attack
- **Grab**: Beats block (you can't block a grab), loses to attack (you get hit while grabbing)
- **Kick**: Longer windup, more damage, different timing to read
- **Dodge**: Different timing than block, maybe repositions you

This creates RPS-style interactions layered on timing reads.

### Weapons
Different weapons = different timing windows:
- Knife: 1.5s windup, low damage
- Club: 4.0s windup, high damage
- Spear: 2.5s windup, medium damage, range advantage?

Now reads include "what weapon are they using" and "can I close distance before their swing".

### Stance as Yomi
Current stance system (standing/sitting/kneeling/prone) could feed combat:
- Can't attack while sitting
- Kneeling = defensive bonus?
- Prone = vulnerable but hard to hit?

Standing up takes time. Lying down is commitment.

### Fight Profiles
Track per-player:
- Block frequency after taking damage
- Cancel frequency during windup
- Aggression when ahead/behind in health
- Proc exploitation rate

Surface this data? Maybe:
- Vague ("This fighter is patient")
- After N fights ("You've seen them block 60% of attacks")
- Never (let players build mental models)

### Typing as Execution
The prompt system could gate combat:
- Attack requires typing the attack verb quickly
- Faster typing = shorter effective windup
- Block timing becomes literal reaction time

This adds execution skill on top of strategic reads. Optional for casuals (tab to take default timing).

## The Design Goal

From CLAUDE.md: "Optimal play should be fun play."

The yomi system should reward:
1. **Reading your opponent** - not memorizing combos
2. **Adaptation** - changing strategy mid-fight
3. **Risk management** - knowing when to press, when to reset
4. **Presence** - paying attention to what's happening now

It should not reward:
1. **Grinding stats** - skill differential matters but doesn't override reads
2. **Scripted play** - predictable patterns get exploited
3. **Execution barriers** - no frame-perfect inputs required (unless opted into)
4. **Information hiding** - windups are visible, health is visible, the game is honest

The reconstruction: violence is real, but it's a conversation. You learn from it. The best fighters are the ones who pay attention.
