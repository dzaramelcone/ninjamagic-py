from string import Formatter

from ninjamagic import bus, reach
from ninjamagic.component import YOU, EntityId, client, noun
from ninjamagic.util import RNG, auto_cap

FMT = Formatter()


def render(data: dict, start: str, *args, seed: int | None = None) -> str:
    RNG.seed(seed)

    def dfs(key: str, choices: dict) -> str:
        val = RNG.choice(data[key])
        for _, next_key, _, _ in FMT.parse(val):
            if next_key and next_key in data:
                choices[next_key] = dfs(next_key, choices)
        return FMT.vformat(val, args, choices)

    return auto_cap(dfs(start, {}))


def vrender(
    story: str, args: tuple[EntityId, ...], kwargs=None, first_person: EntityId = 0
) -> str:
    return auto_cap(
        FMT.vformat(
            story,
            [YOU if v == first_person else noun(v) for v in args],
            kwargs or {},
        )
    )


def echo(
    story: str,
    *args: EntityId,
    range: reach.Selector = reach.adjacent,
    send_to_target: bool = True,
    **kwargs,
):
    has_source = len(args) > 0 and client(args[0])
    if has_source:
        bus.pulse(
            bus.Outbound(
                to=args[0], text=vrender(story, args, kwargs, first_person=args[0])
            )
        )

    target = None
    target_text = ""
    if send_to_target and len(args) > 1 and client(args[1]):
        target = args[1]
        target_text = vrender(story, args, kwargs, first_person=target)
    # note if source and target are not adjacent, target may need to emit also.
    # "SharedEmit" signal that returns true if c in range of a or b
    bus.pulse(
        bus.Emit(
            source=args[0],
            range=range,
            text=vrender(story, args, kwargs),
            target=target,
            target_text=target_text,
        ),
    )


STORIES: dict[str, tuple[str]] = {
    "whisper": [
        "whisper",
        "slit",
        "sliver",
        "nick",
        "tip",
        "trace",
        "scratch",
        "line",
    ],
    "promise": ["promise", "threat", "omen"],
    "throat": [
        "throat",
        "gullet",
        "neck",
        "collar",
        "skin",
        "flesh",
        "windpipe",
    ],
    "bead": ["bead", "line", "streak", "pearl", "drop", "rivulet", "gem"],
    "brushes": [
        "brushes",
        "glances",
        "catches",
        "snags",
        "nicks",
        "grazes",
        "scratches",
        "scrapes",
    ],
    "silver": [
        "silver",
        "cold",
        "keen",
        "narrow",
        "bright",
        "hissing",
        "singing",
        "hungry",
        "polished",
        "cruel",
        "gleam-bright",
        "waiting",
    ],
    "blood": [
        "blood",
        "crimson",
        "scarlet",
    ],
    "fountain": [
        "fountain",
        "plume",
        "spray",
        "fan",
        "jet",
        "pulse",
        "current",
        "geyser",
        "torrent",
        "cascade",
        "eruption",
    ],
    "bursts_open": [
        "blasts open",
        "bursts open",
        "flares open",
        "explodes",
    ],
    "air": [
        "air",
        "night",
        "dust",
        "dark",
    ],
    "collar": [
        "collar",
        "garland",
        "band",
        "necklace",
        "ribbon",
    ],
    "parts": [
        "parts",
        "severs",
        "cleaves",
        "cuts",
        "shears",
        "sunders",
        "hews",
        "divides",
        "unmakes",
    ],
    "grazes": [
        "grazes",
        "skims",
        "kisses",
        "touches",
        "nicks",
        "traces",
        "slices",
    ],
    "gathers": [
        "gathers",
        "beads",
        "forms",
        "pearls",
        "wells",
        "collects",
        "emerges",
    ],
    "appears": [
        "appears",
        "peeks",
        "answers",
        "surfaces",
    ],
    "breath": [
        "breath",
        "whisper",
        "kiss",
        "touch",
        "hiss",
        "song",
        "edge",
    ],
    "shallow": [
        "shallow",
        "shoal",
        "fine",
        "delicate",
    ],
    "blooms": [
        "blooms",
        "blossoms",
        "flowers",
        "spreads",
        "unfurls",
    ],
    "slice": [
        "slice",
        "cut",
        "stroke",
    ],
    "opens": [
        "opens",
        "etches",
        "scores",
        "marks",
        "inscribes",
    ],
    "wound": [
        "wound",
        "band",
        "frown",
        "crevice",
    ],
    "buries": [
        "buries",
        "sinks",
        "plunges",
        "thrusts",
        "drives",
        "sheathes",
        "vanishes",
    ],
    "surges": [
        "surges",
        "pours",
        "floods",
        "jets",
        "erupts",
        "rushes",
        "torrents",
    ],
    "jets": [
        "jets",
        "spouts",
        "sprays",
        "spurts",
    ],
    "carves": [
        "carves",
        "hews",
        "cleaves",
        "rakes",
        "gouges",
        "digs",
        "trenches",
    ],
    "severed": [
        "severed",
        "sawn",
        "hewn",
        "parted",
        "sundered",
        "rent",
        "divided",
    ],
    "pours": [
        "pours",
        "spills",
        "streams",
        "runs",
        "cascades",
        "gushes",
        "floods",
    ],
    "sags": [
        "sags",
        "droops",
        "slumps",
        "wilts",
        "falters",
        "gives way",
        "sinks",
    ],
    "by_a_thread": [
        "by a thread",
        "by a strip",
        "by sinew",
        "by a ribbon of flesh",
        "by ragged cords",
        "by a final strand",
    ],
    "runs": [
        "runs",
        "courses",
        "streams",
        "leaks",
        "flows",
        "spills",
        "pumps",
    ],
    "leaks": [
        "leaks",
        "seeps",
        "dribbles",
        "trickles",
        "weeps",
        "oozes",
    ],
    "stoops": [
        "stoops",
        "bows",
        "hunches",
        "buckles",
        "folds",
        "slumps",
        "doubles over",
        "crumples",
    ],
    "laid_open": [
        "laid open",
        "ripped wide",
        "split bare",
        "opened raw",
        "torn asunder",
        "gaping",
        "exposed",
    ],
    "ripped_wide": [
        "laid open",
        "ripped wide",
        "split bare",
        "opened raw",
        "torn asunder",
        "gaping",
        "exposed",
    ],
    "streams": [
        "streams",
        "pours",
        "courses",
        "rivers",
        "floods",
        "cascades",
    ],
    "shears": [
        "shears",
        "sunders",
        "severs",
        "parts",
        "divides",
        "bisects",
        "unmakes",
    ],
    "fans": [
        "fans",
        "sprays",
        "veils",
        "sheets",
        "mists",
        "curtains",
        "clouds",
    ],
    "drops": [
        "drops",
        "falls",
        "folds",
        "collapses",
        "tumbles",
        "plummets",
        "crashes",
    ],
    "leaves": [
        "leaves",
        "quits",
        "flees",
        "departs",
        "escapes",
    ],
    "scarlet": ["scarlet", "crimson", "red", "vermilion", "ruby", "vivid"],
    "spray": ["spray", "veil", "sheet", "mist", "cloud", "burst", "plume"],
    "collapses": [
        "collapses",
        "crumples",
        "buckles",
        "folds",
        "gives way",
        "falls inward",
        "implodes",
    ],
    "flying": [
        "flying",
        "spinning",
        "spiraling",
        "tumbling",
        "soaring",
    ],
    "vivid": ["vivid", "stark", "bright", "raw", "wet", "shocking"],
    "hot": ["hot", "steaming", "warm", "sudden", "scalding", "feverish"],
    "ruined": [
        "ruined",
        "shattered",
        "broken",
        "mangled",
        "destroyed",
        "unmade",
    ],
    "gushing": [
        "gushing",
        "spraying",
        "arcing",
        "pulsing",
        "violent",
        "unleashed",
    ],
    "silent": [
        "silent",
        "foreboding",
        "quiet",
        "tacit",
    ],
    "sudden": ["sudden", "shocking", "abrupt", "startling", "violent"],
    "gruesome": ["gruesome", "brutal", "ghastly", "hideous", "grisly"],
    "wet": ["wet", "slick", "sodden", "glistening"],
    "fragile": ["fragile", "delicate", "tenuous", "brittle", "thin"],
    "suddenly": [
        "suddenly",
        "abruptly",
        "instantly",
        "swiftly",
        "without warning",
    ],
    "spreading": [
        "spreading",
        "widening",
        "creeping",
        "growing",
        "seeping",
    ],
    "ruin": ["ruin", "wreck", "mess"],
    "violent": ["violent", "brutal", "savage", "vicious"],
    "bloody": ["bloody", "bloodied", "crimson", "scarlet", "red"],
    "skin": ["skin", "flesh", "hide", "meat"],
    "line": [
        "line",
        "trace",
        "cut",
        "mark",
        "scratch",
        "crease",
        "parting",
    ],
    "tip": ["tip", "point", "end", "needle", "prow", "prick", "fang"],
    "neck": ["neck", "throat", "nape"],
    "answers": [
        "answers",
        "appears",
        "wells",
        "surfaces",
        "shows",
        "emerges",
    ],
    "limb": ["limb", "arm", "appendage"],
    "wells": ["wells", "beads", "gathers", "appears", "rises", "pearls"],
    "dust": ["dust", "air", "gloom", "space", "void", "dirt"],
    "cleaves": [
        "cleaves",
        "splits",
        "parts",
        "sunders",
        "divides",
        "opens",
    ],
    "buckles": [
        "buckles",
        "folds",
        "collapses",
        "gives way",
        "fails",
        "crumbles",
    ],
    "tumbles": ["tumbles", "falls", "lands", "thuds", "drops"],
    "sinks": [
        "sinks",
        "plunges",
        "drives",
        "buries",
        "vanishes",
        "sheathes",
        "disappears",
    ],
    "pulse": ["pulse", "jet", "plume", "burst", "surge"],
    "plume": ["plume", "jet", "fountain", "fan"],
    "hangs": ["hangs", "dangles", "droops", "lolls", "flops", "swings"],
    "hewn": ["hewn", "hacked", "cloven", "split", "mangled", "shorn"],
    "buckle": ["buckle", "fold", "crumple", "give way", "collapse", "fail"],
    "bites": ("bites", "cleaves", "cuts", "rips", "slashes"),
    "bitten": ("bitten", "cleaved", "cut", "ripped", "slashed"),
    "deeply": ("deeply", "viciously", "hard"),
    "swing": ("swing", "arc", "stroke", "cut"),
    "goblin": ("goblin", "green runt", "beast", "creature"),
    "thigh": ("thigh", "upper leg"),
    "foot_top": ("foot-top", "instep"),
    "stagger": ("staggers", "reels", "buckles"),
    "clean": ("clean", "keen"),
    "edge": ("biting edge", "keen edge", "bright edge"),
    "bite": ("slash", "slice", "gash", "cut"),
    "muscle": ("muscle", "meat", "flesh"),
    "bone": ("bone", "white bone"),
    "warning": [
        "{0:their} warning",
        "a {blood} {bead}",
        "{0:their} {silent} {promise}",
    ],
    "a_gruesome_adornment": [
        "a {gruesome} wound",
        "a {violent} sight",
        "a necklace of {ruin}",
    ],
    "the_end_begins": [
        "a {wet} beginning to the {bloody} end",
        "a mortal, {gushing} truth",
        "life's last frantic signal",
    ],
    "the_body_fails": [
        "the {fragile} strings of a puppet {suddenly} cut",
        "a {ruin} of meat and bone",
        "a sack of failing flesh",
        "the architecture of life undone",
        "{1:s} body's {sudden} surrender",
        "{1:s} final, graceless bow",
    ],
    "a_final_stillness": [
        "leaving only a final, {spreading} stillness",
        "a {sudden} silence",
        "a {gruesome} mess upon the ground",
        "the final punctuation in a life's sentence",
        "an answer to a question never asked",
        "a stillness where movement used to be",
    ],
    "a_silver_whisper_brushes_the_throat": [
        "A {silver} {whisper} on the {throat}; {warning}.",
        "The edge {grazes}. A {vivid} drop of {blood} {gathers}.",
        "Steel's {breath} on the {skin}; a {bead} of {blood} {appears}.",
        "A {shallow}, {blood} {line} appears; {warning}.",
        "The blade's {tip} {opens} a {whisper} of flesh; {warning}.",
        "{silver} steel {grazes} the {neck}; a drop of {blood} {answers}.",
    ],
    "a_shallow_cut_blooms_a_blood_collar_marks_the_strike": [
        "A {shallow} cut; a {vivid} {blood} {collar} {blooms}.",
        "{1:their} {throat} wears a {blood} {collar}, {0:their} {shallow} {slice}'s prize.",
        "A {vivid} {blood} {collar} wreathes {1:their} {neck}!",
        "The blade {carves} a raw {wound} across {1:their} {throat}; {blood} {leaks} down.",
        "Flesh {blooms} in a {shallow} slice as {vivid} {blood} {pours} forth.",
        "{blood} {wells} from a {shallow} {slice}, staining {1:their} collar.",
    ],
    "steel_drives_deep_a_fountain_of_blood_leaps_through_air": [
        "Steel {buries} to the hilt! {blood} {surges} in a {hot} {spray}!",
        "A deep thrust {opens} flesh! {blood} {jets} into the {dust}; {a_gruesome_adornment}!",
        "Steel {carves} low and deep; a {gushing} {spray} of {blood} leaps through the {dust}!",
        "A {wet} sound as {silver} steel {sinks}; a {hot} {pulse} of {blood} soaks the {air}!",
        "{1:their} carotid artery {bursts_open}! a {plume} of {blood} {fans} across the ground, {a_gruesome_adornment}!",
        "{1:their} {throat} is {laid_open}! a {fountain} of {blood} {surges} from the {vivid} {wound}!",
    ],
    "half_severed_the_neck_pours_shoulders_sink_beneath_the_loss": [
        "Half-{severed}, {1:their} {ruined} {throat} {pours}! {1:their} frame {sags}, {the_body_fails}.",
        "{1:their} head hangs {by_a_thread}! {hot}, {vivid} {blood} {runs} unchecked, pooling at {1:s} feet!",
        "{1:their} neck is shred to the spine! {1:s} {ruined} {throat} {leaks} while {1:their} frame {stoops} in final defeat!",
        "Bone grinds as the {neck} {buckles}! {1:s} head {hangs} on a {ruin} of flesh, {the_body_fails}.",
        "{1:their} spine is {hewn}! {1:s} head {sags} on its {ruined} stalk as {1:their} knees {buckle}!",
        "{1:their} {throat} is {ripped_wide}! {1:s} chin rests on {1:their} collarbone as {hot} life {streams} onto the dust, {the_body_fails}.",
    ],
    "a_single_blow_parts_the_head_from_trunk": [
        "A single blow {parts} head from trunk! {gushing} arterial {spray}s stain the {dust} as the corpse {drops}, {a_final_stillness}.",
        "{0:s} {0.weapon} {cleaves} clean through {1:s} neck! A {spray} of {hot} {blood} {bursts_open} from the stump as life {leaves} the frame!",
        "{0:s} {0.weapon:hyp} {parts} {1:s} head and body! A {blood} {spray} {blooms} before {1:their} empty husk {buckles}!",
        "{1:s} head {tumbles} free! A thick {fountain} of {blood} marks the spot as the body {drops}!",
        "Head falls one way, body another! a {spray} of {blood} {fans} the space between them! {the_body_fails}.",
        "{0.weapon} cleaves clean through bone! {1:s} head is sent {flying}! {1:their} corpse {drops}.",
    ],
    "the_weapon": (
        "{0.weapon}",
        "{0.weapon} in {0:s} hand",
        "{0:their} {swing}",
    ),
    "thigh_bite": (
        "{the_weapon} {bites} {deeply} into {1:s} {thigh}.",
        "{1:s} {thigh} is {bitten} open by {the_weapon}.",
        "with a {clean} {swing}, {0:their} {0.weapon} {bites} into {1:s} {thigh}, spilling {blood}.",
        "{the_weapon} lands {0.weapon:their} {edge}. the {bite} opens {muscle}.",
        "{bone} rattles as {the_weapon} {bites} {1:s} {thigh}.",
        "the {bite} runs long; {blood} leaps from {1:s} {thigh}.",
    ),
    "foot_slash": (
        "the {0.weapon} skates along the {poss_target} {foot_top}, and {blood} {leap}.",
        "{0.weapon} {0.weapon:kisses} the {poss_target} {foot_top}; the {target_goblin} {stagger}.",
        "a mean {swing} rakes the {poss_target} {foot_top}.",
    ),
}


DAMAGE = [
    # neck
    "a_silver_whisper_brushes_the_throat",
    "a_shallow_cut_blooms_a_blood_collar_marks_the_strike",
    "steel_drives_deep_a_fountain_of_blood_leaps_through_air",
    "half_severed_the_neck_pours_shoulders_sink_beneath_the_loss",
    "a_single_blow_parts_the_head_from_trunk",
    # head
    "a_skimming_cut_marks_the_scalp",
    "bone_kissed_the_brow_splits_blood_blinds_one_eye",
    "steel_bites_through_skull_teeth_clack_a_red_mist",
    "the_face_halved_jaw_hangs_brain_shows_in_the_cut",
    "the_head_takes_wing_from_shoulders",
    # torso
    "a_line_of_red_on_pale_skin",
    "a_deep_gash_opens_the_chest_spilling_blood",
    "steel_sinks_deep_a_killing_thrust_steals_the_breath",
    "the_belly_is_torn_open_guts_spill_like_rope",
    "a_single_blow_cleaves_the_body_in_two_a_ruin_of_flesh_and_bone",
    # arm
    "a_silver_line_on_the_flesh",
    "steel_bites_a_red_wound_blooms_wide",
    "the_blade_drives_deep_parting_muscle_and_the_arm_goes_dead",
    "a_heavy_blow_shatters_bone_the_limb_hangs_by_shreds",
    "a_single_arc_of_steel_the_arm_falls_away_leaving_a_gushing_stump",
    # leg
    "steel_scores_leather_a_red_line_answers",
    "the_blade_bites_deep_a_raw_gash_weeps_crimson",
    "a_heavy_blow_cripples_the_thigh_the_knee_buckles_under_dead_weight",
    "the_leg_is_hewn_to_the_bone_it_hangs_by_a_ribbon_of_shredded_flesh",
    "one_clean_stroke_severs_the_limb_it_tumbles_to_the_ground_in_a_spray_of_gore",
]
