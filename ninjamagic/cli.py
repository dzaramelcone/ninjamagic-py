#!/usr/bin/env python3
"""
sample_cli.py — quick-and-dirty sampler for broadsword textgen data.

Usage examples:
  # 10 samples from every damage root in every part, one batch; then prompt
  python sample_cli.py -b 10

  # Keep printing batches of 5 for just torso damage (press Enter for next)
  python sample_cli.py -p torso -b 5

  # Specific root key, e.g. 'a_single_blow_parts_the_head_from_trunk'
  python sample_cli.py -p neck -r a_single_blow_parts_the_head_from_trunk -b 8

  # Non-interactive: run 3 batches then exit
  python sample_cli.py -b 5 --batches 3

  # Deterministic output
  python sample_cli.py -s 1337 -b 5
"""

import argparse
import random
import re
import sys

from ninjamagic.story import STORIES as DATA

PLACEHOLDER_RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def resolve_once(text: str, choices: dict[str, list[str]], rng: random.Random) -> str:
    """Randomly resolve a template string recursively."""

    def repl(m):
        key = m.group(1).strip()
        vals = choices.get(key)
        if not vals:
            # leave unresolved so you can spot missing keys visually
            return m.group(0)
        chosen = rng.choice(vals)
        return resolve_once(chosen, choices, rng)

    return normalize_whitespace(PLACEHOLDER_RE.sub(repl, text))


def iter_parts():
    for part_name, part_data in DATA.get("broadsword", {}).items():
        if isinstance(part_data, dict):
            yield part_name, part_data


def list_parts() -> list[str]:
    return [p for p, _ in iter_parts()]


def get_choices(part: str) -> dict[str, list[str]]:
    part_data = DATA["broadsword"][part]
    choices = part_data.get("choices", {})
    if not isinstance(choices, dict):
        raise ValueError(f"{part}.choices must be a dict")
    return choices


def get_roots(part: str, scalar: str) -> list[str]:
    part_data = DATA["broadsword"][part]
    scalars = part_data.get("scalars", {})
    roots = scalars.get(scalar, [])
    if not isinstance(roots, list):
        raise ValueError(f"{part}.scalars[{scalar}] must be a list")
    return roots


def print_header(
    part: str, scalar: str, root: str | None, batch_idx: int, batch_size: int
):
    title = f"[{part}::{scalar}]"
    if root:
        title += f" -> {root}"
    print("=" * len(title))
    print(title)
    print(f"batch {batch_idx} (size={batch_size})")
    print("=" * len(title))


def run_batches(
    parts: list[str],
    scalar: str,
    root: str | None,
    batch_size: int,
    num_batches: int | None,
    seed: int | None,
    interactive: bool,
):
    rng = random.Random(seed)
    batch_idx = 1
    # precompute per-part roots
    per_part_roots = {p: get_roots(p, scalar) for p in parts}
    for p in parts:
        if not per_part_roots[p]:
            print(f"(warn) {p} has no roots for scalar '{scalar}'", file=sys.stderr)

    def one_batch():
        for part in parts:
            roots = per_part_roots[part]
            choices = get_choices(part)
            if root:
                if root not in choices:
                    print(
                        f"(warn) root '{root}' not in choices for {part}",
                        file=sys.stderr,
                    )
                    continue
                roots_to_use = [root]
            else:
                roots_to_use = roots

            for r in roots_to_use:
                opts = choices.get(r, [])
                if not opts:
                    print(f"(warn) empty list for {part}::{r}", file=sys.stderr)
                    continue
                print_header(part, scalar, r if root else None, batch_idx, batch_size)
                for i in range(batch_size):
                    sent = rng.choice(opts)
                    out = resolve_once(sent, choices, rng)
                    print(f"{i + 1:>3}. {out}")
                print()

    while True:
        one_batch()
        if num_batches is not None:
            if batch_idx >= num_batches:
                break
        batch_idx += 1
        if interactive:
            try:
                inp = input("[Enter] next batch • (q) quit: ").strip().lower()
            except EOFError:
                break
            if inp.startswith("q"):
                break


def main():
    ap = argparse.ArgumentParser(
        description="Sample broadsword textgen outputs in batches."
    )
    ap.add_argument(
        "-p",
        "--part",
        choices=list_parts() + ["all"],
        default="all",
        help="Body part to sample (default: all)",
    )
    ap.add_argument(
        "-scl",
        "--scalar",
        default="damage",
        help="Scalar name to use (default: damage)",
    )
    ap.add_argument(
        "-r",
        "--root",
        default=None,
        help="Specific root key to sample (overrides scalar roots)",
    )
    ap.add_argument(
        "-b",
        "--batch-size",
        type=int,
        default=10,
        help="How many lines per root per batch (default: 10)",
    )
    ap.add_argument(
        "--batches",
        type=int,
        default=None,
        help="Number of batches to run; omit for infinite/interactive",
    )
    ap.add_argument(
        "-s", "--seed", type=int, default=None, help="RNG seed for reproducibility"
    )
    ap.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt between batches (useful for CI/logs)",
    )
    ap.add_argument(
        "--list",
        action="store_true",
        help="List available parts and root keys, then exit",
    )

    args = ap.parse_args()

    if args.list:
        print("Parts:", ", ".join(list_parts()))
        for p in list_parts():
            roots = get_roots(p, args.scalar)
            print(
                f"- {p}::{args.scalar} roots: {', '.join(roots) if roots else '(none)'}"
            )
        # Also list top-level choice keys as potential roots
        if args.part != "all":
            choices = get_choices(args.part)
            print(f"- {args.part} choice keys ({len(choices)}):")
            print("  " + ", ".join(sorted(choices.keys())))
        return

    parts = list_parts() if args.part == "all" else [args.part]
    run_batches(
        parts=parts,
        scalar=args.scalar,
        root=args.root,
        batch_size=max(1, args.batch_size),
        num_batches=args.batches,
        seed=args.seed,
        interactive=not args.non_interactive and args.batches in (None, 0),
    )


if __name__ == "__main__":
    main()
