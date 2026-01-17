# Player-Facing Feature Interaction Matrix

## Feature List
1) Movement
2) Look/Perception (map + nearby)
3) Forage
4) Cook
5) Eat/Meals
6) Rest/Camp
7) Take Cover (nightstorm)
8) Stance Changes (stand/sit/lie/kneel)
9) Combat: Attack
10) Combat: Block
11) Combat: Conditions (stun/shock/prone)
12) Health/Death/Respawn
13) Skills/XP Gain/Consolidation
14) Inventory/Items/Equipment
15) Loot/Drops
16) Talk/Say/Emote
17) Prompts/Opts/Hints
18) Wyrd/Kneel Ritual
19) Night/Day/Nightstorm Cycle
20) Visibility/Line of Sight
21) Heat/Light/Bonfire Proximity
22) Hostility/Danger Zones
23) Tokens (e.g., DoubleDamage)

## Interaction Matrix (notes per pair)

### 1) Movement
- Look/Perception: moving updates nearby/map context and line of sight.
- Forage: movement changes what tiles are forageable.
- Cook: movement to a prop/fire may be required to cook.
- Eat/Meals: moving can change safety/heat/light affecting meal quality.
- Rest/Camp: movement required to find safe rest spot.
- Take Cover: movement may be restricted during storm; cover location matters.
- Stance: movement requires standing (current rule).
- Combat: attack/block often gated by range/reach; movement changes range.
- Conditions: stun/prone can prevent movement.
- Health/Death: moving while low health changes risk; death resets location.
- Skills/XP: movement may influence exploration XP or survival checks.
- Inventory: encumbrance may slow or limit movement.
- Loot: movement to loot location enables pickup.
- Talk: proximity enables talk/emote to others.
- Prompts/Opts/Hints: movement often triggers hints or prompts.
- Wyrd: reaching a ritual spot requires movement.
- Night/Day: visibility and danger change how movement feels.
- Visibility: movement changes what you can see.
- Heat/Light: moving away from heat/light changes safety.
- Hostility: movement into hostile tiles affects risk.
- Tokens: movement may affect token positioning or duration contexts.

### 2) Look/Perception
- Forage: seeing forageable items/tiles indicates availability.
- Cook/Eat: seeing props/food sources informs choices.
- Rest/Camp: seeing shelter/anchor affects rest decisions.
- Take Cover: seeing cover options affects survival.
- Stance: some stances may reduce visibility (prone).
- Combat: perception of threats governs timing.
- Conditions: shock/stun may alter perception text.
- Health/Death: low health may change perception cues.
- Skills/XP: perception can be a source of skill-based reveals.
- Inventory/Loot: spotting items enables pickup.
- Talk/Emote: seeing entities enables social actions.
- Prompts/Opts/Hints: prompts often align with visible cues.
- Wyrd: seeing a ritual point suggests kneel.
- Night/Day: darkness reduces perception; storms obscure.
- Visibility/LoS: same system; look is front-end of LoS.
- Heat/Light: light increases visibility range.
- Hostility: seeing hostile zones warns player.
- Tokens: token cues may need to be visible.

### 3) Forage
- Cook: foraged items become ingredients.
- Eat: foraged items can be eaten raw or cooked.
- Rest/Camp: forage before rest affects meal quality.
- Take Cover: storms may reduce forage opportunities.
- Stance: foraging may require standing or kneeling.
- Combat: foraging may be interrupted by combat.
- Conditions: shock/stun blocks foraging.
- Health: forage affects survival and recovery indirectly via food.
- Skills/XP: survival XP from forage or risk checks.
- Inventory: forage adds items; limited slots.
- Loot: forage is a form of loot generation.
- Prompts/Opts/Hints: forage taught via hints.
- Night/Day: forage tables or success change with time.
- Visibility: must see/know tile to forage.
- Heat/Light: foraging near fire safer.
- Hostility: hostile tiles reduce safe forage.
- Tokens: tokens could boost forage success.

### 4) Cook
- Eat: cooked food improves meal quality.
- Rest: cooking before rest affects recovery.
- Stance: cooking likely requires kneel/sit near fire.
- Combat: cooking can be interrupted by combat.
- Conditions: shock/stun blocks cooking.
- Health: cooked food improves survival/regen.
- Skills/XP: cooking grants skill XP.
- Inventory: consumes ingredients, creates items.
- Loot: cooked items are loot outputs.
- Prompts/Opts/Hints: hints can teach cooking.
- Night/Day: night encourages cooking near fire.
- Heat/Light: fire required for cooking.
- Hostility: hostile areas reduce safe cooking.
- Tokens: tokens may alter cook outcomes.

### 5) Eat/Meals
- Rest: meal quality affects rest outcomes.
- Take Cover: eating in unsafe conditions reduces benefits.
- Stance: eating while resting changes quality.
- Combat: eating during combat risky or impossible.
- Conditions: shock/stun blocks eating.
- Health: meals restore health/stress.
- Skills/XP: survival XP or buffs from meals.
- Inventory: consumes food items.
- Prompts/Opts/Hints: eating taught via hints.
- Night/Day: eating at night affects safety checks.
- Heat/Light: warmth/light affect meal pips.
- Hostility: hostile area reduces meal safety.
- Tokens: tokens may buff meal effects.

### 6) Rest/Camp
- Take Cover: alternative to camping during nightstorm.
- Stance: resting requires sit/lie; kneel may block.
- Combat: cannot rest in combat.
- Conditions: shock/stun may force rest outcomes.
- Health: rest is primary recovery.
- Skills/XP: consolidation often during rest.
- Inventory: rest may interact with items (bedroll).
- Prompts/Opts/Hints: rest taught via hints.
- Night/Day: rest tied to night cycle.
- Heat/Light: rest near fire safer/better.
- Hostility: hostility reduces rest success.
- Tokens: tokens may buff rest gains.

### 7) Take Cover
- Stance: cover implies prone/lying stance.
- Combat: cover can be used mid-combat.
- Conditions: cover can inflict stunned or reduce damage.
- Health: reduces nightstorm damage.
- Skills/XP: survival XP for cover checks.
- Prompts/Opts/Hints: cover prompt occurs at night.
- Night/Day: tied to nightstorm timing.
- Heat/Light: cover may reduce light/heat.
- Hostility: hostile areas reduce cover efficacy.

### 8) Stance Changes
- Combat: stance affects block/attack availability.
- Conditions: stun/prone overrides stance.
- Rest: rest requires specific stances.
- Eat: eating while sitting/lying changes quality.
- Cook: kneel/sit may be required.
- Move: must stand to move.
- Wyrd: kneel triggers ritual.
- Prompts/Opts/Hints: hints teach stance usage.

### 9) Combat: Attack
- Block: attack/block timing interplay.
- Conditions: attacks cause stun/shock/prone.
- Health: attacks deal damage leading to death.
- Skills/XP: combat grants XP and tokens.
- Inventory/Items: weapons affect attack.
- Loot: attacks enable loot drops.
- Tokens: tokens may buff attack.
- Hostility: hostile zones spawn combat.

### 10) Combat: Block
- Conditions: successful block may reduce stun or prevent.
- Health: block mitigates damage.
- Skills/XP: block may train defensive skills.
- Tokens: tokens may buff block.

### 11) Combat: Conditions
- Health: conditions can cause death or incapacitation.
- Movement: conditions can stop movement.
- Stance: conditions force prone/lying.
- Rest: conditions may require rest to recover.

### 12) Health/Death/Respawn
- Skills/XP: death may affect XP or consolidation.
- Inventory: death may drop items.
- Loot: death creates loot.
- Rest: health recovery tied to rest.
- Prompts/Opts/Hints: death could trigger prompts.

### 13) Skills/XP Gain/Consolidation
- Forage/Cook/Eat/Rest/Combat: all grant XP.
- Tokens: tokens earned through play loops.
- Wyrd: ritual could award or lock XP.
- Night/Day: consolidation during rest/night.

### 14) Inventory/Items/Equipment
- Combat: weapons/armor affect outcomes.
- Forage/Cook/Eat: item flow through inventory.
- Rest: items can improve rest.
- Loot: inventory receives drops.

### 15) Loot/Drops
- Combat: enemy death triggers loot.
- Forage: foraging creates loot.
- Inventory: loot stored or dropped.

### 16) Talk/Say/Emote
- Combat: taunts or communication mid-fight.
- Rest: social interaction during rest.
- Prompts/Opts/Hints: social prompts or choices.

### 17) Prompts/Opts/Hints
- Movement/Combat/Rest: hints teach commands.
- Wyrd: opt or prompt for rituals.
- Night/Day: prompts at nightstorm.

### 18) Wyrd/Kneel Ritual
- Stance: kneel required.
- Tokens: rituals may grant tokens.
- Skills/XP: ritual may grant XP or buffs.
- Prompts/Opts/Hints: hint teaches kneel.

### 19) Night/Day/Nightstorm Cycle
- Take Cover: prompts at nightstorm.
- Rest: night cycle drives rest.
- Visibility: darkness reduces sight.
- Heat/Light: fire more important at night.
- Hostility: night increases danger.

### 20) Visibility/Line of Sight
- Movement: position alters LoS.
- Combat: visibility gates targeting.
- Forage: visibility gates discovery.
- Talk: visibility affects who you can speak to.

### 21) Heat/Light/Bonfire Proximity
- Rest/Eat/Cook: improves outcomes.
- Visibility: increases sight.
- Hostility: reduces danger near fire.
- Wyrd: ritual tied to bonfire.

### 22) Hostility/Danger Zones
- Movement: hostile tiles affect risk.
- Forage/Rest: hostile areas reduce success.
- Combat: spawns threats.

### 23) Tokens
- Combat: tokens buff attack/defense.
- Skills/XP: tokens earned through play loops.
- Rest/Wyrd: potential sources or multipliers.
- Forage/Cook/Eat: possible tokens to enhance outcomes.
