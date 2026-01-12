# # test_broadsword_textgen.py
# """
# Pytest suite for validating the broadsword injury textgen data.

# What it checks:
# 1) Structure & reachability
#    - No missing template keys
#    - Each root scalar category exists in choices
#    - No unused choice keys (unreachable from any root category)
#    - No duplicate strings inside any choices[key] list
# 2) Spell-check (optional; skipped if libs unavailable)
#    - Uses 'wordfreq' if present; otherwise skipped with explanation
#    - Allows a configurable custom whitelist for domain words
# 3) Sample generation + grammar-check (optional; skipped if libs unavailable)
#    - Randomly resolves examples from each category, checks basic grammar
# 4) Combinatorics
#    - Performant permutation counts via recursive analysis + memoization
#    - Asserts scale (>= 30_000_000 per category)
#    - Asserts branches (sentences) within an order of magnitude
# 5) Max resolved length per category (worst-case, computed symbolically)
#    - Verifies severity-length budgets (80, 140, 200, 260, 320 chars)

# To run:
#     pytest -q

# Environment notes:
# - If your data file isn't valid JSON (e.g., trailing commas, missing quotes),
#   prefer putting it in a Python module 'data.py' as a Python dict named DATA.
# - Grammar check uses language_tool_python if installed; else test is skipped.
# - Spell check uses wordfreq if installed; else test is skipped.
# """

# import random
# import re
# from functools import lru_cache
# from typing import Dict, List, Tuple, Any
# import logging
# from spellchecker import SpellChecker

# from ninjamagic.data import DATA

# assert "broadsword" in DATA and isinstance(DATA["broadsword"], dict), (
#     "Expected top-level key 'broadsword' with a dict."
# )


# PLACEHOLDER_RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
# logger = logging.getLogger(__name__)


# def extract_placeholders(text: str) -> List[str]:
#     """Return a list of placeholder keys (e.g., 'blood', 'their(o)') in a template string."""
#     return PLACEHOLDER_RE.findall(text)


# def normalize_whitespace(s: str) -> str:
#     return re.sub(r"\s+", " ", s).strip()


# def _choices_for_part(part_data: Dict[str, Any]) -> Dict[str, List[str]]:
#     choices = part_data.get("choices", {})
#     assert isinstance(choices, dict), "choices must be a dict"
#     for k, v in choices.items():
#         assert isinstance(k, str), f"choices key {k!r} must be string"
#         assert isinstance(v, list), f"choices[{k!r}] must be a list of strings"
#         for i, item in enumerate(v):
#             assert isinstance(item, str), f"choices[{k!r}][{i}] must be a string"
#     return choices


# def _scalars_for_part(part_data: Dict[str, Any]) -> Dict[str, List[str]]:
#     scalars = part_data.get("scalars", {})
#     assert isinstance(scalars, dict), "scalars must be a dict"
#     for sk, sv in scalars.items():
#         assert isinstance(sk, str), "scalar names must be str"
#         assert isinstance(sv, list), (
#             f"scalars[{sk!r}] must be a list of root category keys (str)"
#         )
#         for i, item in enumerate(sv):
#             assert isinstance(item, str), f"scalars[{sk!r}][{i}] must be str"
#     return scalars


# def reachable_choice_keys_from_roots(
#     choices: Dict[str, List[str]], root_keys: List[str]
# ) -> Tuple[set, Dict[str, List[str]]]:
#     """
#     BFS/DFS from root category keys, following placeholders inside the choices strings
#     to find all reachable choice lists needed to resolve templates.
#     Returns (reachable_keys_set, missing_keys_by_ref)
#     """
#     missing_refs: Dict[str, List[str]] = {}
#     visited = set()
#     stack = list(root_keys)

#     while stack:
#         key = stack.pop()
#         if key in visited:
#             continue
#         visited.add(key)

#         if key not in choices:
#             # This is a missing category key
#             missing_refs.setdefault(key, []).append(f"Missing category '{key}'")
#             continue

#         for s in choices[key]:
#             for ref in extract_placeholders(s):
#                 # placeholders like their(o) are still keys in choices (per your data)
#                 if ref not in choices and "(" not in ref:
#                     missing_refs.setdefault(ref, []).append(
#                         f"Missing referenced key '{ref}' (referred from '{key}')"
#                     )
#                 # We still push it to crawl further; we'll catch missing in the if above
#                 stack.append(ref)

#     return visited, missing_refs


# @lru_cache(None)
# def _count_permutations_for_text(
#     text: str, choices_kv: Tuple[Tuple[str, Tuple[str, ...]], ...]
# ) -> int:
#     """
#     Count permutations for a text that may include nested placeholders.
#     choices_kv is a hashable frozen mapping: tuple of (key, tuple(options...))
#     Counting rule:
#       For text without placeholders: 1
#       For each placeholder {{k}}: sum over options (permutation count of that option text)
#       For a sentence with multiple placeholders: multiply their counts (independent choices)
#     """
#     # Rebuild dict from the hashable tuple
#     choices: Dict[str, Tuple[str, ...]] = dict(choices_kv)  # immutable for caching

#     parts = PLACEHOLDER_RE.split(text)
#     # split -> [plain0, key1, plain1, key2, plain2, ...]
#     # We'll iterate pairs: plain, key, plain, key...
#     # Approach: multiply counts over placeholders; plains contribute 1.

#     # We need to process placeholder occurrences in order.
#     # For each placeholder, total variations = sum(count(option))
#     # If a placeholder repeats, it's independent (can pick different options).
#     total = 1
#     # indices of placeholders are the odd positions
#     for i in range(1, len(parts), 2):
#         key = parts[i].strip()
#         if key not in choices:
#             # Missing keys are handled elsewhere; treat as zero paths
#             return 0
#         options = choices[key]
#         subtotal = 0
#         for opt in options:
#             subtotal += _count_permutations_for_text(opt, choices_kv)
#         total *= max(subtotal, 1)
#     return total or 1


# @lru_cache(None)
# def _max_length_for_text(
#     text: str, choices_kv: Tuple[Tuple[str, Tuple[str, ...]], ...]
# ) -> int:
#     """
#     Compute the maximum fully-resolved character length for a text with nested placeholders.
#     This is exact under independent choice assumption: for each placeholder, take the option
#     that yields the longest resolved text; sum across the sentence parts.
#     """
#     choices: Dict[str, Tuple[str, ...]] = dict(choices_kv)
#     # Split into literals and placeholder keys
#     cursor = 0
#     max_len = 0
#     for m in PLACEHOLDER_RE.finditer(text):
#         literal = text[cursor : m.start()]
#         max_len += len(literal)
#         key = m.group(1).strip()
#         if key in choices:
#             # Max among options
#             best = 0
#             for opt in choices[key]:
#                 best = max(best, _max_length_for_text(opt, choices_kv))
#             max_len += best
#         else:
#             # Unresolved placeholder — treat its textual marker length to avoid undercount.
#             max_len += len(m.group(0))
#         cursor = m.end()
#     max_len += len(text[cursor:])
#     return max_len


# def _freeze_choices(
#     choices: Dict[str, List[str]],
# ) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
#     """Convert dict -> hashable tuple-of-tuples for caching."""
#     return tuple(sorted((k, tuple(v)) for k, v in choices.items()))


# # -------------------------- Resolution (sampling) --------------------------- #


# def resolve_once(text: str, choices: Dict[str, List[str]], rng: random.Random) -> str:
#     """Randomly resolve a template text into a single output string (recursive)."""

#     def repl(m):
#         key = m.group(1).strip()
#         vals = choices.get(key)
#         if not vals:
#             return m.group(
#                 0
#             )  # leave unresolved; the structure tests will catch missing
#         chosen = rng.choice(vals)
#         return resolve_once(chosen, choices, rng)

#     return normalize_whitespace(PLACEHOLDER_RE.sub(repl, text))


# # ------------------------------ Test Helpers --------------------------------#

# SEVERITY_BUDGETS = {
#     0: 80,  # least severe
#     1: 140,
#     2: 200,
#     3: 260,
#     4: 320,  # most severe
# }


# def iter_parts():
#     for part_name, part_data in DATA["broadsword"].items():
#         if not isinstance(part_data, dict):
#             continue
#         yield part_name, part_data


# # ================================ TESTS ===================================== #


# def test_structure_and_references():
#     problems = []

#     for part_name, part_data in iter_parts():
#         choices = _choices_for_part(part_data)
#         scalars = _scalars_for_part(part_data)

#         # duplicates
#         for k, lst in choices.items():
#             seen, dups = set(), set()
#             for s in lst:
#                 if s in seen:
#                     dups.add(s)
#                 seen.add(s)
#             if dups:
#                 problems.append(
#                     f"[{part_name}] choices[{k}] has duplicate options: {sorted(dups)}"
#                 )

#         # scalar roots exist
#         for scalar_name, roots in scalars.items():
#             for root in roots:
#                 if root not in choices:
#                     problems.append(
#                         f"[{part_name}] scalar '{scalar_name}' root '{root}' missing in choices"
#                     )

#             # reachability
#             reachable, missing = reachable_choice_keys_from_roots(choices, roots)
#             for ref, msgs in missing.items():
#                 for msg in msgs:
#                     problems.append(f"[{part_name}::{scalar_name}] {msg}")

#             # unused (per scalar)
#             unused = sorted(set(choices.keys()) - reachable)
#             if unused:
#                 problems.append(
#                     f"[{part_name}::{scalar_name}] Unused choice keys: {unused[:25]}{'...' if len(unused) > 25 else ''}"
#                 )

#     assert not problems, "Structure/reference issues:\n" + "\n".join(problems)


# def test_preview_some_resolutions(capsys):
#     rng = random.Random(1234)
#     for part_name, part_data in iter_parts():
#         choices = _choices_for_part(part_data)
#         scalars = _scalars_for_part(part_data)
#         for scalar_name, roots in scalars.items():
#             logger.info(f"\n== {part_name}:{scalar_name} ==")
#             for root in roots:
#                 for i, sent in enumerate(choices[root][:3]):  # first 3 sentences
#                     out = resolve_once(sent, choices, rng)
#                     logger.info(f"  [{root} #{i}] {out}")


# def test_spell_check_values():
#     """
#     Spell-check all literal tokens in all choice strings.

#     Heuristics:
#       - Strip template placeholders {{...}} before checking
#       - Split on non-word chars (underscores & parentheses are allowed and skipped)
#       - Accept tokens <=2 chars
#       - Accept tokens with digits or parentheses/underscores (domain placeholders)
#       - Maintain a domain whitelist for fantasy/anatomy/etc. and add to the spellchecker
#     """

#     spell = SpellChecker(distance=1)  # conservative Levenshtein radius

#     DOMAIN_WHITELIST = {
#         # Domain / fantasy / anatomy / onomatopoeia:
#         "broadsword",
#         "gullet",
#         "ichor",
#         "fulming",
#         "sundered",
#         "sunders",
#         "hew",
#         "hewn",
#         "sinew",
#         "malar",
#         "cranium",
#         "mandible",
#         "rictus",
#         "orb",
#         "halved",
#         "unzips",
#         "unzipped",
#         "unzipping",
#         "vitae",
#         "welling",
#         "scarlet",
#         "claret",
#         "humerus",
#         "ulna",
#         "radius",
#         "patella",
#         "femoris",
#         "greave",
#         "cleaves",
#         "sunder",
#         "unmakes",
#         "veil",
#         "plume",
#         "geyser",
#         "tibia",
#         "femur",
#         "viscera",
#         "fulmin",
#         "fulmining",
#         "fulminant",
#         "fulminate",
#         "unsure",
#         "their(o)",
#         "they(o)",
#         "their(p)",
#         "Their(o)",
#         "They(o)",
#         "Their(p)",
#     }

#     # Teach pyspellchecker our domain words (lower-cased)
#     for w in DOMAIN_WHITELIST:
#         spell.word_frequency.add(w.lower())

#     def acceptable_token(token: str) -> bool:
#         if not token:
#             return True
#         if token.isdigit():
#             return True
#         # Skip placeholders / domain-like tokens that include underscores or parentheses
#         if "_" in token or "(" in token or ")" in token:
#             return True
#         # Keep simple short words
#         if len(token) <= 2:
#             return True
#         # If token contains any digits, treat as domain-y and accept
#         if any(ch.isdigit() for ch in token):
#             return True
#         # Domain whitelist (case-insensitive)
#         if token.lower() in {w.lower() for w in DOMAIN_WHITELIST}:
#             return True
#         return False

#     problems = []
#     for part_name, part_data in iter_parts():
#         choices = _choices_for_part(part_data)
#         for key, options in choices.items():
#             for idx, s in enumerate(options):
#                 # Remove templates first so we only check literal surface text
#                 literal = PLACEHOLDER_RE.sub(" ", s)
#                 # Split on non-word characters but keep apostrophes inside words
#                 raw_tokens = re.split(r"[^\w']+", literal)
#                 # Filter + normalize tokens to check
#                 tokens_to_check = []
#                 for tok in raw_tokens:
#                     tok = tok.strip()
#                     if not tok:
#                         continue
#                     if acceptable_token(tok):
#                         continue
#                     tokens_to_check.append(tok.lower())

#                 # Ask pyspellchecker for unknown words
#                 unknown = spell.unknown(tokens_to_check)
#                 if unknown:
#                     for bad in sorted(unknown):
#                         problems.append((part_name, key, idx, bad, s))

#     assert not problems, (
#         "Potential spelling issues found (using pyspellchecker). "
#         "Review tokens below and either fix typos or add to DOMAIN_WHITELIST.\n"
#         + "\n".join(
#             f"[{p}::{k} #{i}] token={t!r} in: {s}" for p, k, i, t, s in problems[:100]
#         )
#     )


# def test_grammar_on_samples():
#     """
#     Randomly resolve a sample from each sentence of each category and check grammar with LanguageTool.
#     We allow some minor stylistic flags but assert no obvious errors (e.g., agreement, casing, leftover '{{').
#     """
#     import language_tool_python  # type: ignore

#     tool = language_tool_python.LanguageTool("en-US")

#     rng = random.Random(1337)
#     MAX_PER_SENTENCE = 3  # keep runtime manageable

#     violations = []

#     for part_name, part_data in iter_parts():
#         choices = _choices_for_part(part_data)
#         scalars = _scalars_for_part(part_data)

#         for _, roots in scalars.items():
#             for root in roots:
#                 assert root in choices, f"Missing category {root} for grammar test."
#                 for sent in choices[root]:
#                     for _ in range(MAX_PER_SENTENCE):
#                         text = resolve_once(sent, choices, rng)
#                         # sanity checks
#                         assert (
#                             ("{{" not in text and "}}" not in text)
#                             or "(" in text
#                             and ")" in text
#                         ), f"Unresolved template in '{text}'"
#                         assert "  " not in text, f"Double-space in '{text}'"
#                         assert text[0].isalpha() or text[0] in "\"'(", (
#                             f"Odd sentence start: {text!r}"
#                         )
#                         assert text[-1] in ".;:!?" or text[-1].isalpha(), (
#                             f"Suspicious ending: {text!r}"
#                         )
#                         matches = tool.check(text)
#                         # Allow a few stylistic warnings; flag if too many or severe categories appear
#                         hard = [
#                             m
#                             for m in matches
#                             if m.ruleId
#                             not in {"ENGLISH_WORD_REPEAT_RULE", "WHITESPACE_RULE"}
#                         ]
#                         if len(hard) >= 2:
#                             violations.append((part_name, root, text, hard[:3]))

#     assert not violations, "Grammar issues found in samples:\n" + "\n".join(
#         f"[{p}::{root}] {txt}\n  -> {', '.join(m.ruleId for m in ms)}"
#         for p, root, txt, ms in violations[:50]
#     )


# def test_permutation_scale_and_balance():
#     failures = []
#     for part_name, part_data in iter_parts():
#         choices = _choices_for_part(part_data)
#         scalars = _scalars_for_part(part_data)
#         frozen = _freeze_choices(choices)

#         for _, roots in scalars.items():
#             for root in roots:
#                 per_sentence = [
#                     _count_permutations_for_text(s, frozen) for s in choices[root]
#                 ]
#                 total = sum(per_sentence)
#                 if total < 30_000_000:
#                     failures.append(
#                         f"[{part_name}::{root}] variety={total:,} < 30,000,000 (per-branch={per_sentence})"
#                     )
#                 nz = [x for x in per_sentence if x > 0]
#                 if nz and max(nz) / max(1, min(nz)) > 10:
#                     failures.append(
#                         f"[{part_name}::{root}] imbalance max/min={max(nz) / min(nz):.2f} (per-branch={per_sentence})"
#                     )
#     assert not failures, "Permutation failures:\n" + "\n".join(failures)


# def test_permutation_totals_report(capsys):
#     """
#     Aggregate report of permutation variety across all parts/categories.
#     - Asserts the grand total meets a baseline:
#         baseline = 30_000_000 * (sum over all scalar roots)
#       (i.e., at least the per-root minimum already required elsewhere)
#     """
#     grand_total = 0
#     baseline = 0
#     lines = []

#     for part_name, part_data in iter_parts():
#         choices = _choices_for_part(part_data)
#         scalars = _scalars_for_part(part_data)
#         frozen = _freeze_choices(choices)

#         part_total = 0
#         part_baseline = 0

#         for _, roots in scalars.items():
#             # each root must meet >= 30,000,000 per your scale test
#             part_baseline += 30_000_000 * len(roots)

#             for root in roots:
#                 assert root in choices, f"Missing category {root} for totals report."
#                 per_sentence = [
#                     _count_permutations_for_text(s, frozen) for s in choices[root]
#                 ]
#                 root_total = sum(per_sentence)
#                 part_total += root_total

#                 lines.append(
#                     f"{part_name}::{root} variety={root_total:,} "
#                     f"(branches={per_sentence})"
#                 )

#         lines.append(f"-- {part_name} total: {part_total:,}")
#         grand_total += part_total
#         baseline += part_baseline

#     lines.append(f"\nGRAND TOTAL variety: {grand_total:,}")
#     lines.append(f"Baseline (roots * 30,000,000): {baseline:,}")

#     # Emit the report to stdout
#     logger.info("\n".join(lines))

#     # Sanity assertion: at least as large as sum of the per-root baselines
#     assert grand_total >= baseline, (
#         f"Grand total variety {grand_total:,} fell below baseline {baseline:,}"
#     )


# def test_max_length_budgets_by_severity():
#     issues = []
#     for part_name, part_data in iter_parts():
#         choices = _choices_for_part(part_data)
#         scalars = _scalars_for_part(part_data)
#         frozen = _freeze_choices(choices)

#         assert "damage" in scalars and len(scalars["damage"]) == 5, (
#             f"[{part_name}] Expected exactly 5 severity levels in scalars['damage']."
#         )

#         for rank, root in enumerate(scalars["damage"]):
#             budget = SEVERITY_BUDGETS.get(rank, 320)
#             offenders = []
#             for idx, s in enumerate(choices[root]):
#                 mlen = _max_length_for_text(s, frozen)
#                 if mlen > budget:
#                     offenders.append((idx, mlen, s))
#             if offenders:
#                 offenders.sort(key=lambda x: x[1], reverse=True)
#                 preview = "\n".join(
#                     f"  - sentence#{i}: len={L} > {budget} :: {s!r}"
#                     for i, L, s in offenders[:10]
#                 )
#                 issues.append(
#                     f"[{part_name}::{root}] {len(offenders)} over budget.\n{preview}"
#                 )
#     assert not issues, "Length budget issues:\n" + "\n".join(issues)
